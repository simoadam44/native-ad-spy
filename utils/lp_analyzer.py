import asyncio
import random
import re
from urllib.parse import urlparse
from utils.popup_handler import dismiss_popups
from utils.cloak_detector import detect_cloaking
from utils.url_blacklist import is_meaningful_url, is_intermediary_domain
import tldextract

async def wait_for_actual_landing(page, max_wait=10000):
    """Waits for network to settle, especially if currently on a tracking domain."""
    try:
        await page.wait_for_load_state("networkidle", timeout=max_wait)
        waited = 0
        while is_intermediary_domain(page.url) and waited < 15000:
            await asyncio.sleep(1.0)
            waited += 1000
    except: pass

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

    # 1. Register ALL listeners BEFORE any action
    page.on("request", on_request)
    page.on("response", on_response)
    
    # Set up route interception
    async def handle_route(route):
        await route.continue_()
    await page.route("**/*", handle_route)

    # 2. Find CTA with Heuristic Scoring and Bottom Scrolling
    cta_element = None
    cta_text = "Unknown"
    
    # Pre-emptively scroll the page to ensure lazy-loaded CTAs (like bottom article buttons) are loaded
    try:
        for _ in range(5):
            await page.mouse.wheel(0, 1000)
            await asyncio.sleep(0.3)
    except: pass
    
    social_domains = ["facebook.com", "twitter.com", "instagram.com", "linkedin.com", "pinterest.com"]
    keywords = ["click here", "watch", "video", "buy", "order", "get", "claim", "shop", "discount", "check", "haz clic", "obtener", "طلب", "klicken", "voir", "guardar", "sehen"]
    selectors = "a, button, [role='button'], input[type='button'], input[type='submit'], [class*='btn'], [class*='button'], [class*='cta']"
    
    best_el = None
    best_score = -1
    best_text = ""

    for f in page.frames:
        try:
            elements = await f.query_selector_all(selectors)
            for el in elements:
                try:
                    txt = (await el.inner_text() or "").strip()
                    href = (await el.get_attribute("href") or "").lower()
                    class_attr = (await el.get_attribute("class") or "").lower()
                    
                    if not txt and not href and not class_attr:
                        continue
                        
                    txt_lower = txt.lower()
                    score = 0
                    
                    # Penalize social media or internal anchors
                    if any(s in href for s in social_domains):
                        score -= 50
                    if href.startswith("#") or href == "/" or "void(0)" in href:
                        score -= 5
                        
                    # Reward high-intent keywords
                    for k in keywords:
                        if k in txt_lower:
                            score += 15
                            
                    # Reward typical CTA class names 
                    if "btn" in class_attr or "button" in class_attr or "cta" in class_attr:
                        score += 5
                        
                    # Reward external or tracking-like hrefs
                    if href and not href.startswith("#") and "facebook" not in href:
                        score += 5
                        
                    # Reward descriptive but concise text
                    if 5 < len(txt) < 50:
                        score += 2
                        
                    if score > best_score and score > 0:
                        best_score = score
                        best_el = el
                        best_text = txt
                except:
                    continue
        except:
            continue
            
    if best_el:
        cta_element = best_el
        cta_text = best_text

    # 3. Perform the click
    final_offer_url = page.url
    redirect_chain = []
    cta_found = False

    if cta_element:
        try:
            cta_found = True
            # Scroll into view with timeout
            try:
                await cta_element.scroll_into_view_if_needed(timeout=5000)
            except Exception as se:
                print(f"Non-fatal scroll error: {se}")
            
            # Click and wait for navigation or network
            try:
                await cta_element.click(timeout=5000, force=True)
            except Exception as click_err:
                # Fallback to JavaScript click directly if Playwright's click fails (e.g., hidden by overlay)
                await cta_element.evaluate("el => el.click()")
            
            try:
                await wait_for_actual_landing(page, 10000)
            except: pass
            
            final_offer_url = page.url
            # Filter clean redirect chain from all_requests
            redirect_chain = [r["url"] for r in all_requests if r["url"] != final_offer_url]
            
        except Exception as e:
            print(f"CTA Interception Error for {page.url}: {e}")

    return {
        "cta_found": cta_found,
        "cta_text": cta_text,
        "final_offer_url": final_offer_url,
        "redirect_chain": redirect_chain
    }

async def analyze_page_structure(page) -> dict:
    """Detects pagination, galleries, and high ad density."""
    try:
        content = await page.content()
        url = page.url.lower()
        
        # Pagination indicators
        pagination_selectors = [".pagination", ".next-page", ".slideshow-nav", "[class*='pagination']", "[class*='next']"]
        is_paginated = False
        for sel in pagination_selectors:
            try:
                if await page.query_selector(sel):
                    is_paginated = True
                    break
            except: pass
            
        # Ad container signatures
        ad_selectors = [
            "[id*='google_ads']", ".adsbygoogle", "[id*='taboola']", "[id*='outbrain']",
            "[class*='taboola']", "[class*='outbrain']", "[class*='revcontent']",
            ".adsbygoogle", "[class*='dfp']"
        ]
        ad_count = 0
        for sel in ad_selectors:
            try:
                nodes = await page.query_selector_all(sel)
                ad_count += len(nodes)
            except: pass
            
        is_wordpress = "/wp-content/" in content or "wp-json" in content
        has_comments = "disqus" in content or "fb-comments" in content
        
        page_type_guess = "unknown"
        if is_paginated: page_type_guess = "slideshow_arbitrage"
        elif ad_count >= 3: page_type_guess = "article_arbitrage"
        
        return {
            "is_paginated": is_paginated,
            "high_ad_density": ad_count >= 3,
            "ad_count": ad_count,
            "is_wordpress": is_wordpress,
            "is_clickbait": any(k in url for k in ["trending", "believe", "defying", "celebrities"]),
            "has_comments": has_comments,
            "page_type_guess": page_type_guess
        }
    except: return {}

async def analyze_landing_page_with_page(page, url: str) -> dict:
    """Analyzes a landing page using an existing Playwright page object."""
    result = {
        "final_offer_url": None,
        "page_subtype": "Unknown",
        "has_countdown": False,
        "has_video": False,
        "price_found": None,
        "cta_text": None,
        "cloaking": {},
        "popups": {},
        "text_content": "",
        "full_html": ""
    }

    try:
        clean_redirect_chain = []
        original_reg_domain = tldextract.extract(url).registered_domain
        
        def handle_response(response):
            try:
                r_url = response.url
                status = response.status
                if not is_meaningful_url(r_url): return
                if status < 200 or status >= 400: return
                url_domain = tldextract.extract(r_url).registered_domain
                if url_domain == original_reg_domain: return
                if r_url not in clean_redirect_chain: clean_redirect_chain.append(r_url)
            except: pass
            
        page.on("response", handle_response)
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        
        await wait_for_actual_landing(page, 15000)
        
        await page.mouse.wheel(0, 500)
        await asyncio.sleep(1.0)

        result["popups"] = await dismiss_popups(page)
        content = await page.content()
        try: text_content = await page.evaluate("document.body.innerText")
        except: text_content = ""
        result["text_content"] = text_content
        result["full_html"] = content
        
        result["has_video"] = bool(await page.query_selector("video") or "youtube.com/embed" in content)
        result["has_countdown"] = bool(await page.query_selector("[class*='timer'], [id*='timer']"))

        if any(k in text_content.lower() for k in ["add to cart", "buy now", "order now"]):
            result["page_subtype"] = "Direct Sales"
        elif "advertorial" in content.lower():
            result["page_subtype"] = "Advertorial"

        result["final_offer_url"] = page.url
        result["cloaking"] = detect_cloaking(url, result["final_offer_url"], clean_redirect_chain)
        result["page_structure"] = await analyze_page_structure(page)
        result["clean_redirect_chain"] = clean_redirect_chain

    except Exception as e:
        print(f"LP Analysis Error for {url}: {e}")

    return result
