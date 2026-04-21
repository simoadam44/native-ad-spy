import asyncio
import random
import re
from urllib.parse import urlparse
from utils.popup_handler import dismiss_popups
from utils.cloak_detector import detect_cloaking
from utils.url_blacklist import is_meaningful_url, is_intermediary_domain, AFFILIATE_SIGNATURES
import tldextract
from urllib.parse import urlparse, parse_qs, unquote

def extract_target_from_params(url: str) -> str:
    """Attempts to recursively find a destination URL hidden in query parameters."""
    if not url: return ""
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        # Common 'destination' parameter names for trackers
        dest_params = ["requestUrl", "dest", "url", "u", "target", "redirect", "destination"]
        for p in dest_params:
            if p in params and params[p]:
                target = unquote(params[p][0])
                if target.startswith("http"):
                    # RECURSIVE: Check if the extracted URL also has a target
                    # But avoid infinite loops - just one level deeper usually suffices
                    deeper = extract_target_from_params(target)
                    if deeper != target:
                        return deeper
                    return target
    except: pass
    return url

async def wait_for_actual_landing(page, max_wait=15000):
    """Waits for network to settle, excluding tracker redirects."""
    try:
        await page.wait_for_load_state("networkidle", timeout=max_wait)
        # Extra wait if we are still on a known tracker/intermediary - max 5s
        waited = 0
        while is_intermediary_domain(page.url) and waited < 5000:
            print(f"Waiting for redirect from intermediary: {page.url}")
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
            # Only track meaningful navigations or main documents in the chain
            # EXCLUDE media segments (.ts, .m3u8, etc.)
            media_exts = [".jpg", ".png", ".gif", ".webp", ".css", ".js", ".woff", ".ico", ".ts", ".m3u8", ".mp4", ".mp3", ".webm"]
            if not any(ext in url.lower() for ext in media_exts):
                all_responses.append({
                    "url": url,
                    "status": status,
                    "headers": dict(response.headers)
                })
        except: pass

    # 1. Register ALL listeners BEFORE any action (at Context level to catch popups)
    context = page.context
    context.on("request", on_request)
    context.on("response", on_response)
    
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
    keywords = [
        "click here", "watch", "video", "buy", "order", "get", "claim", "shop", "discount", 
        "check", "haz clic", "obtener", "طلب", "klicken", "voir", "guardar", "sehen",
        "see how it works", "watch presentation", "click here to see", "watch the video", 
        "get started", "learn more", "discovery", "hidden video", "shocking video", "presentation",
        "commandez", "acheter", "profitez", "descubre", "ver video", "clicca qui"
    ]
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
                        # Many affiliate buttons use href="#" with JS handlers, so don't penalize if keywords are strong
                        if any(k in txt_lower for k in ["watch", "click", "get", "video"]):
                            score += 5
                        else:
                            score -= 5
                        
                    # Reward high-intent keywords
                    for k in keywords:
                        if k in txt_lower:
                            score += 15
                    
                    # Extra reward for VSL specific phrases
                    if any(v in txt_lower for v in ["watch", "video", "presentation"]):
                        score += 5
                            
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
            
            # Click and wait for navigation or a new tab (popup)
            try:
                # Set up the expectation for a popup with longer timeout
                async with page.context.expect_event("popup", timeout=12000) as popup_info:
                    try:
                        # Attempt a "human-like" click if regular click might be intercepted
                        await cta_element.click(timeout=5000, force=True, delay=random.randint(50, 150))
                    except Exception as click_err:
                        print(f"Playwright click failed, using JS fallback for {page.url}")
                        await cta_element.evaluate("el => el.click()")
                
                # If a popup opened, it's the most likely intended destination
                popup_page = await popup_info.value
                print(f"Popup detected: {popup_page.url}")
                
                # Wait for the popup to resolve trackers to the final merchant page
                try:
                    await wait_for_actual_landing(popup_page, 15000)
                except: 
                    print(f"Popup resolution timeout (non-fatal) for {popup_page.url}")
                
                final_offer_url = popup_page.url
                # CAPTURE REDIRECT CHAIN FROM POPUP TOO
                # We can't easily merge but we can at least get the final result
                await popup_page.close() 
            except Exception:
                # If no popup happened, handle same-tab navigation
                print(f"No popup detected for {page.url}, checking same-tab navigation...")
                try:
                    await wait_for_actual_landing(page, 15000)
                except: pass
            # If the current page is a tracker/pixel, don't use it as the final result
            if not is_meaningful_url(final_offer_url) or is_intermediary_domain(final_offer_url):
                print(f"Landed on tracker/pixel: {final_offer_url}. Seeking fallback.")
                final_offer_url = page.url # Default back to lander so comparison logic triggers
            
            final_offer_url = extract_target_from_params(final_offer_url)

            # Normalize URLs for comparison (remove fragments, trailing slashes)
            def clean_url(u):
                if not u: return ""
                return u.split("#")[0].rstrip("/")

            cleaned_final = clean_url(final_offer_url)
            cleaned_landing = clean_url(page.url)

            # Filter clean redirect chain: Only include meaningful redirects
            redirect_chain = []
            for r in all_requests:
                r_url = r["url"]
                
                # AGGRESSIVE CLEANING: Extract target from every URL in the chain
                cleaned_r = extract_target_from_params(r_url)
                if cleaned_r != r_url:
                    r_url = cleaned_r
                
                if clean_url(r_url) == cleaned_landing:
                    continue
                media_exts = [".jpg", ".png", ".gif", ".webp", ".css", ".js", ".woff", ".ico", ".svg", ".ts", ".m3u8", ".mp4", ".mp3", ".webm"]
                if not any(ext in r_url.lower() for ext in media_exts):
                    if r_url not in redirect_chain:
                        redirect_chain.append(r_url)
            
            # CRITICAL FALLBACK: If final_offer_url is still essentially the landing page but we have a redirect chain
            if cleaned_final == cleaned_landing and len(redirect_chain) > 0:
                original_domain = tldextract.extract(cleaned_landing).registered_domain
                
                # First pass: Look for known affiliate signatures
                found_affiliate_fallback = False
                for r_url in reversed(redirect_chain):
                    # DOUBLE-PASS: Always extract the real target first
                    cleaned_r = extract_target_from_params(r_url)
                    r_domain = tldextract.extract(cleaned_r).registered_domain
                    if r_domain != original_domain:
                        # STRICT: Must be meaningful (NOT media/static) AND have an affiliate signature
                        if is_meaningful_url(cleaned_r) and any(sig in cleaned_r.lower() for sig in AFFILIATE_SIGNATURES):
                            print(f"Heuristic Fallback (Affiliate Match): Using {cleaned_r}")
                            final_offer_url = cleaned_r
                            found_affiliate_fallback = True
                            break

                
                # Second pass: If no affiliate signature found, use the last meaningful domain that is NOT the original
                # AND NOT a tracker if possible
                if not found_affiliate_fallback:
                    # Valid checkout subdomains for ClickBank/Digistore
                    valid_checkout_prefixes = ["pay.", "checkout.", "secure.", "order.", "buy."]
                    
                    # Try to find a checkout page first
                    for r_url in reversed(redirect_chain):
                        # AGGRESSIVE: Clean it again before checking
                        cleaned_r = extract_target_from_params(r_url)
                        
                        is_checkout = any(p in cleaned_r.lower() for p in valid_checkout_prefixes)
                        is_clickbank = "clickbank.net" in cleaned_r.lower()
                        is_digistore = "digistore24.com" in cleaned_r.lower()
                        
                        if (is_clickbank or is_digistore) and is_checkout:
                            # DOUBLE CHECK: Must not be a tracker path
                            if "/sellerhop" not in cleaned_r.lower() and is_meaningful_url(cleaned_r):
                                print(f"Heuristic Fallback (Checkout Detected): Using {cleaned_r}")
                                final_offer_url = cleaned_r
                                found_affiliate_fallback = True
                                break
                    
                    if not found_affiliate_fallback:
                        for r_url in reversed(redirect_chain):
                            # AGGRESSIVE: Clean it again
                            cleaned_r = extract_target_from_params(r_url)
                            r_domain = tldextract.extract(cleaned_r).registered_domain
                            
                            # Check if it's meaningful AND not a known intermediary/tracker
                            if r_domain != original_domain and is_meaningful_url(cleaned_r) and not is_intermediary_domain(cleaned_r):
                                print(f"Heuristic Fallback (Merchant Domain): Using {cleaned_r}")
                                final_offer_url = cleaned_r
                                break
                
                # FINAL ATTEMPT: If we are STILL on a problematic URL (like sellerhop), use param extraction again on fallbacks
                final_offer_url = extract_target_from_params(final_offer_url)
                print(f"Finalized Offer Resolution: {final_offer_url}")
            
            # Clean up listeners
            context.remove_listener("request", on_request)
            context.remove_listener("response", on_response)
            
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
        await page.goto(url, wait_until="domcontentloaded", timeout=30000)
        
        await wait_for_actual_landing(page, 10000)
        
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
