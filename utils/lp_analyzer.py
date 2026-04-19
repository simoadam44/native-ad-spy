import asyncio
import random
import re
from urllib.parse import urlparse
from utils.popup_handler import dismiss_popups
from utils.cloak_detector import detect_cloaking
from utils.url_blacklist import is_meaningful_url
import tldextract

async def click_cta_and_capture(page, ad_type: str = "Affiliate") -> dict:
    """
    Clicks the CTA button and captures the full redirect chain.
    Enhanced with pre-emptive interception and route monitoring.
    """
    all_requests = []
    all_responses = []
    
    def on_request(request):
        all_requests.append({
            "url": request.url,
            "method": request.method
        })
    
    def on_response(response):
        try:
            url = response.url
            status = response.status
            all_responses.append({
                "url": url,
                "status": status,
                "headers": dict(response.headers)
            })
        except: pass

    # 1. Register ALL listeners BEFORE any action (Fix for Case 2)
    page.on("request", on_request)
    page.on("response", on_response)
    
    # Set up route interception for deep visibility
    async def handle_route(route):
        await route.continue_()
    await page.route("**/*", handle_route)

    # 2. Find CTA
    cta_element = None
    cta_text = "Unknown"
    
    social_domains = ["facebook.com", "twitter.com", "instagram.com", "linkedin.com", "pinterest.com"]
    keywords = ["order", "get", "buy", "claim", "shop", "discount", "check", "haz clic", "obtener", "طلب"]
    selectors = ["a", "button", "[role='button']", "input[type='button']", "input[type='submit']"]
    
    for stage in range(4):
        if stage == 1:
            await asyncio.sleep(1.0)
            try: await page.wait_for_load_state("networkidle", timeout=5000)
            except: pass
        
        for f in page.frames:
            try:
                elements = await f.query_selector_all(", ".join(selectors)) if stage < 2 else \
                           await f.query_selector_all('[class*="btn"], [class*="button"], [class*="cta"]')
                
                for el in elements:
                    txt = (await el.inner_text() or "").strip()
                    href = (await el.get_attribute("href") or "").lower()
                    if any(s in href for s in social_domains): continue
                    
                    if stage < 2 and any(k in txt.lower() for k in keywords):
                        cta_element = el
                        cta_text = txt
                        break
                    elif stage >= 2 and len(txt) >= 3:
                        cta_element = el
                        cta_text = txt
                        break
                if cta_element: break
            except: continue
        if cta_element: break

    if not cta_element:
        # Cleanup
        await page.unroute("**/*")
        page.remove_listener("request", on_request)
        page.remove_listener("response", on_response)
        return {"cta_found": False, "final_offer_url": page.url, "redirect_chain": []}

    # 3. Perform Click with Interception
    try:
        await cta_element.scroll_into_view_if_needed()
        await asyncio.sleep(random.uniform(0.5, 1.0))
        
        # Click
        await cta_element.click()
        
        # Wait logic: prioritize navigation but also wait for network quiet
        try:
            await page.wait_for_load_state("networkidle", timeout=8000)
        except: pass
        
        # 4. Filter and Build Redirect Chain
        SKIP_PATTERNS = [
            "google-analytics", "googletagmanager", "facebook.net",
            "clarity.ms", "bing.com/bat", "doubleclick",
            "cdn.", "fonts.", "static.", "assets.",
            ".css", ".js", ".png", ".jpg", ".gif", ".woff", ".svg"
        ]
        
        meaningful_urls = []
        for r in all_responses:
            url = r["url"]
            # Keep redirects (3xx) OR destination pages with parameters (200)
            if (300 <= r["status"] < 400 or (r["status"] == 200 and "?" in url)):
                if not any(skip in url.lower() for skip in SKIP_PATTERNS):
                    if url not in meaningful_urls:
                        meaningful_urls.append(url)
        
        # Build the final chain
        redirect_chain = meaningful_urls
        
        return {
            "cta_found": True,
            "cta_text": cta_text,
            "final_offer_url": page.url,
            "redirect_chain": redirect_chain,
            "final_page_title": await page.title()
        }

    except Exception as e:
        print(f"CTA Interception Error: {e}")
    finally:
        try:
            await page.unroute("**/*")
            page.remove_listener("request", on_request)
            page.remove_listener("response", on_response)
        except: pass

    return {"cta_found": False, "final_offer_url": page.url, "redirect_chain": []}

async def analyze_page_structure(page) -> dict:
    """
    Detects Arbitrage page elements: pagination, ad density, content format.
    """
    content = await page.content()
    url = page.url.lower()
    
    # 1. Pagination detector
    is_paginated = bool(re.search(r'/\d+/?$', url))
    
    # 2. Ad density
    ad_selectors = [
        "[class*='taboola']", "[id*='taboola']",
        "[class*='outbrain']", "[class*='revcontent']",
        ".adsbygoogle", "[class*='dfp']",
        "[class*='ad-slot']", "[class*='ad-unit']"
    ]
    ad_count = 0
    for sel in ad_selectors:
        try:
            nodes = await page.query_selector_all(sel)
            ad_count += len(nodes)
        except: pass
        
    # 3. Content type signals
    is_wordpress = "/wp-content/" in content or "wp-json" in content
    has_comments = "disqus" in content or "fb-comments" in content
    
    # Calculate guess
    page_type_guess = "unknown"
    if is_paginated:
        page_type_guess = "slideshow_arbitrage"
    elif ad_count >= 3:
        page_type_guess = "article_arbitrage"
    
    return {
        "is_paginated": is_paginated,
        "high_ad_density": ad_count >= 3,
        "ad_count": ad_count,
        "is_wordpress": is_wordpress,
        "is_clickbait": any(k in url for k in ["trending", "believe", "defying", "celebrities"]),
        "has_comments": has_comments,
        "page_type_guess": page_type_guess
    }

async def analyze_landing_page_with_page(page, url: str) -> dict:
    """
    Analyzes a landing page using an existing Playwright page object.
    """
    result = {
        "final_offer_url": None,
        "page_subtype": "Unknown",
        "has_countdown": False,
        "has_video": False,
        "price_found": None,
        "cta_text": None,
        "cloaking": {},
        "popups": {},
        "text_content": ""
    }

    try:
        # 1. Navigation & Redirect Tracking
        print(f"Navigating to: {url[:60]}...")
        
        # Build clean redirect chain
        clean_redirect_chain = []
        original_reg_domain = tldextract.extract(url).registered_domain
        
        def handle_response(response):
            try:
                r_url = response.url
                status = response.status
                if not is_meaningful_url(r_url):
                    return
                if status < 200 or status >= 400:
                    return
                
                # Skip same domain
                url_domain = tldextract.extract(r_url).registered_domain
                if url_domain == original_reg_domain:
                    return
                    
                if r_url not in clean_redirect_chain:
                    clean_redirect_chain.append(r_url)
            except: pass
            
        page.on("response", handle_response)

        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        
        # 2. Human Simulation
        for _ in range(2):
            await page.mouse.wheel(0, random.randint(200, 500))
            await asyncio.sleep(0.3)

        # 3. Dismiss Popups
        result["popups"] = await dismiss_popups(page)

        # 4. Content Scanning
        content = await page.content()
        text_content = await page.evaluate("document.body.innerText")
        result["text_content"] = text_content
        
        # Metadata logic
        has_video = await page.query_selector("video") or "youtube.com/embed" in content
        result["has_video"] = bool(has_video)
        result["has_countdown"] = bool(await page.query_selector("[class*='timer'], [id*='timer']"))

        # Subtype logic
        if any(k in text_content.lower() for k in ["add to cart", "buy now", "order now"]):
            result["page_subtype"] = "Direct Sales"
        elif "advertorial" in content.lower():
            result["page_subtype"] = "Advertorial"

        # 5. Cloaking & Structure Detection
        result["final_offer_url"] = page.url
        result["cloaking"] = detect_cloaking(url, result["final_offer_url"], clean_redirect_chain)
        result["page_structure"] = await analyze_page_structure(page)
        result["clean_redirect_chain"] = clean_redirect_chain

    except Exception as e:
        print(f"LP Analysis Error: {e}")

    return result
