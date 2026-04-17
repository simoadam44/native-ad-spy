import asyncio
import random
import re
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
        "popups": {}
    }

    try:
        # 1. Navigation
        print(f"Navigating to: {url[:60]}...")
        # Listen for redirects to capture chain
        redirect_chain = []
        def handle_response(response):
            if 300 <= response.status < 400:
                redirect_chain.append(response.url)
        page.on("response", handle_response)

        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        await asyncio.sleep(2)

        # 2. Human Simulation
        for _ in range(2):
            await page.mouse.wheel(0, random.randint(300, 600))
            await asyncio.sleep(0.5)
        await page.mouse.move(random.randint(100, 500), random.randint(100, 500))

        # 3. Dismiss Popups
        result["popups"] = await dismiss_popups(page)

        # 4. Detect Subtype & Content
        content = await page.content()
        text_content = await page.evaluate("document.body.innerText")
        
        # VSL check
        has_video = await page.query_selector("video") or "youtube.com/embed" in content or "vimeo.com" in content
        result["has_video"] = bool(has_video)
        
        has_timer = await page.query_selector("[class*='timer'], [id*='timer'], [class*='countdown']") or "minutes" in content.lower() and ":" in content
        result["has_countdown"] = bool(has_timer)

        if has_video and has_timer:
            result["page_subtype"] = "VSL"
        elif "by:" in text_content[:500].lower() or "advertorial" in content.lower():
            result["page_subtype"] = "Advertorial"
        elif any(k in text_content.lower() for k in ["add to cart", "buy now", "check out"]):
            result["page_subtype"] = "Direct Sales"
        elif await page.query_selector("input[type='radio']") or "question" in text_content.lower():
            result["page_subtype"] = "Quiz"

        # Price detection
        price_match = re.search(r"\$\d+(\.\d{2})?", text_content)
        if price_match:
            result["price_found"] = price_match.group(0)

        # 5. Find and Click CTA
        cta_selectors = [
            "a:has-text('Order Now')", "a:has-text('Buy Now')", 
            "a:has-text('Get Started')", "a:has-text('Claim Offer')",
            "button:has-text('Order Now')", ".cta-button", "#cta"
        ]
        
        cta_clicked = False
        for selector in cta_selectors:
            try:
                cta_btn = await page.wait_for_selector(selector, timeout=2000)
                if cta_btn and await cta_btn.is_visible():
                    result["cta_text"] = await cta_btn.inner_text()
                    # Scroll into view and click
                    await cta_btn.scroll_into_view_if_needed()
                    
                    # Click with expectation of navigation
                    try:
                        async with page.expect_navigation(timeout=10000):
                            await cta_btn.click()
                        cta_clicked = True
                        break
                    except:
                        # Fallback click if navigation doesn't trigger traditionally
                        await cta_btn.click()
                        await asyncio.sleep(3)
                        cta_clicked = True
                        break
            except:
                continue
        
        result["final_offer_url"] = page.url
        
        # 6. Cloaking Detection
        result["cloaking"] = detect_cloaking(url, result["final_offer_url"], redirect_chain)

    except Exception as e:
        print(f"Analysis Error: {e}")

    return result
