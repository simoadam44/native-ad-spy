import asyncio
import random
import re
from urllib.parse import urlparse
from utils.popup_handler import dismiss_popups
from utils.cloak_detector import detect_cloaking

async def analyze_landing_page_with_page(page, url: str) -> dict:
    """
    Analyzes a landing page using an existing Playwright page object.
    Performs human simulation, dismisses popups, and clicks CTA.
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
        "detected_network": "Direct / Unknown",
        "detected_tracker": "Unknown",
        "params": {}
    }

    try:
        # 1. Navigation
        print(f"Navigating to: {url[:60]}...")
        redirect_chain = []
        def handle_response(response):
            if 300 <= response.status < 400:
                redirect_chain.append(response.url)
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
        
        # Metadata logic
        has_video = await page.query_selector("video") or "youtube.com/embed" in content
        result["has_video"] = bool(has_video)
        result["has_countdown"] = bool(await page.query_selector("[class*='timer'], [id*='timer']"))

        # Subtype logic
        if any(k in text_content.lower() for k in ["add to cart", "buy now", "order now"]):
            result["page_subtype"] = "Direct Sales"
        elif "advertorial" in content.lower():
            result["page_subtype"] = "Advertorial"

        # 5. Robust 4-Stage CTA Detection
        cta_clicked = False
        
        async def find_and_click_cta():
            # Exclude social media noise
            social_domains = ["facebook.com", "twitter.com", "instagram.com", "linkedin.com", "pinterest.com"]
            
            # ATTEMPT 1-3: Intent-based search
            keywords = ["order", "get", "buy", "claim", "shop", "discount", "check", "haz clic", "obtener", "طلب"]
            selectors = ["a", "button", "[role='button']", "input[type='button']", "input[type='submit']"]
            
            for stage in range(4):
                if stage == 1:
                    print("CTA Stage 2: Waiting for JS/Network Idle...")
                    await asyncio.sleep(3.0)
                    try: await page.wait_for_load_state("networkidle", timeout=5000)
                    except: pass
                elif stage == 2:
                    print("CTA Stage 3: Scrolling to bottom...")
                    await page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
                    await asyncio.sleep(1.5)
                elif stage == 3:
                    print("CTA Stage 4: Broad CSS Selector search...")
                
                # Scan all frames
                for f in page.frames:
                    try:
                        if stage < 3:
                            # Search by intent keywords
                            elements = await f.query_selector_all(", ".join(selectors))
                            for el in elements:
                                txt = (await el.inner_text() or "").lower()
                                href = (await el.get_attribute("href") or "").lower()
                                
                                # Skip social links
                                if any(s in href for s in social_domains): continue
                                
                                if any(k in txt for k in keywords):
                                    await el.scroll_into_view_if_needed()
                                    await el.click(delay=random.randint(50, 200))
                                    return txt, True
                        else:
                            # Broad search: [class*="btn"], [class*="cta"], etc.
                            broad_selectors = ['[class*="btn"]', '[class*="button"]', '[class*="cta"]', '[class*="order"]']
                            elements = await f.query_selector_all(", ".join(broad_selectors))
                            for el in elements:
                                txt = (await el.inner_text() or "").strip()
                                if len(txt) >= 3:
                                    # Skip social links
                                    href = (await el.get_attribute("href") or "").lower()
                                    if any(s in href for s in social_domains): continue
                                    
                                    await el.scroll_into_view_if_needed()
                                    await el.click(delay=random.randint(50, 200))
                                    return txt, True
                    except: continue
            return None, False

        cta_txt, cta_clicked = await find_and_click_cta()
        if cta_clicked:
            result["cta_text"] = cta_txt
            await asyncio.sleep(5) # Wait for redirect
            result["final_offer_url"] = page.url
        else:
            result["final_offer_url"] = page.url

        # 6. Cloaking Detection
        result["cloaking"] = detect_cloaking(url, result["final_offer_url"], redirect_chain)

    except Exception as e:
        print(f"LP Analysis Error: {e}")

    return result
