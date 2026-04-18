import asyncio
import random
import re
from utils.popup_handler import dismiss_popups
from utils.cloak_detector import detect_cloaking
from utils.groq_analyzer import invoke_groq_intelligence

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

        # Setup Network Traffic Monitor
        active_trackers = 0
        def on_request(r):
            nonlocal active_trackers
            if any(k in r.url.lower() for k in ['pixel', 'track', 'click', 'vsl']):
                active_trackers += 1

        def on_request_done(r):
            nonlocal active_trackers
            if any(k in r.url.lower() for k in ['pixel', 'track', 'click', 'vsl']):
                active_trackers = max(0, active_trackers - 1)

        page.on("request", on_request)
        page.on("requestfinished", on_request_done)
        page.on("requestfailed", on_request_done)

        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        
        current_url_lower = page.url.lower()
        if any(token in current_url_lower for token in ['lptoken=', 'cep=', 'hop=', 'affid=']):
            result["final_offer_url"] = page.url
            result["page_subtype"] = "Direct Affiliate Hybrid"
            return result

        # Active Network Wait (up to 8 seconds)
        for _ in range(16):
            if active_trackers <= 0:
                await asyncio.sleep(2)
                break
            await asyncio.sleep(0.5)

        # 2. Human Simulation with Extended Mouse Jitter
        for _ in range(3):
            await page.mouse.wheel(0, random.randint(200, 700))
            await page.mouse.move(random.randint(100, 700), random.randint(100, 700))
            await asyncio.sleep(0.5)

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

        # 5. Universal CTA Detection & Link Hunting (The Golden Rule)
        try:
            link_hunted = await page.evaluate(f'''() => {{
                const links = Array.from(document.querySelectorAll('a[href], button'));
                for(let el of links) {{
                    const href = (el.href || '').toLowerCase();
                    const text = el.innerText.toLowerCase();
                    
                    // Check if it's an outgoing offer link or explicit intent
                    if (href.includes('hop=') || href.includes('clickid=') || href.includes('vndr=') ||
                        href.includes('aff_id=') || href.includes('/out/') || text.includes('click')) {{
                        
                        try {{
                            const myDomain = new URL(window.location.href).hostname;
                            const targetDomain = new URL(href).hostname;
                            if (myDomain !== targetDomain || href.includes('/out/')) {{
                                el.scrollIntoView();
                                el.click();
                                return text;
                            }}
                        }} catch(e) {{}}
                    }}
                }}
                return null;
            }}''')
            
            if link_hunted:
                result["cta_text"] = link_hunted.strip()
                await asyncio.sleep(4) # Wait for redirect cascade
                result["final_offer_url"] = page.url
                cta_clicked = True
            else:
                cta_clicked = False
                
        except Exception as e:
            cta_clicked = False

        if not cta_clicked:
            # Fallback to Text Intent & Buttons across all frames (Bypassing IFrames)
            intent_regex = re.compile(r'\b(get|order|watch|claim|shop|discount|check|70%|off|availability)\b', re.IGNORECASE)
            
            for f in page.frames:
                if cta_clicked: break
                try:
                    elements = await f.query_selector_all("a, button, .cta-button, [role='button']")
                    for el in elements:
                        text = await el.inner_text()
                        if text and intent_regex.search(text):
                            await el.scroll_into_view_if_needed()
                            result["cta_text"] = text.strip()
                            
                            try:
                                async with page.expect_navigation(timeout=8000):
                                    await el.click()
                                cta_clicked = True
                                result["final_offer_url"] = page.url
                                break
                            except:
                                await el.click()
                                await asyncio.sleep(4)
                                cta_clicked = True
                                result["final_offer_url"] = page.url
                                break
                except:
                    continue

        if not result["final_offer_url"] or result["final_offer_url"] == url:
            result["final_offer_url"] = page.url
            
        # 6. Cloaking Detection
        result["cloaking"] = detect_cloaking(url, result["final_offer_url"], redirect_chain)

        # 7. Fallback to Groq AI if high confidence target not secured, or cloaked
        # Extracted links array just in case Groq needs it
        if result["final_offer_url"] == url or result["cloaking"].get("cloaking_detected"):
            print("Invoking Groq AI Intelligence Fallback...")
            try:
                extracted_links = await page.evaluate(
                    "Array.from(document.querySelectorAll('a[href]')).map(a => a.href).filter(h => h.startsWith('http'))"
                )
                groq_data = invoke_groq_intelligence(
                    title="Unknown Title (AI Probe)",
                    landing_url=result["final_offer_url"],
                    text_snippet=text_content,
                    extracted_links=extracted_links
                )
                if groq_data and "decision" in groq_data:
                    dec = groq_data["decision"]
                    # Override if AI has higher confidence
                    if dec.get("target_url") and dec.get("target_url") != "null":
                        result["final_offer_url"] = dec["target_url"]
                    if dec.get("funnel_type"):
                        result["page_subtype"] = dec["funnel_type"]
                    if dec.get("cloaking_detected"):
                        result["cloaking"]["cloaking_detected"] = True
                        result["cloaking"]["cloaking_type"] = "ai_detected"
                    if dec.get("detected_tracker"):
                        result["detected_tracker"] = dec["detected_tracker"]
                    if dec.get("detected_network"):
                        result["detected_network"] = dec["detected_network"]
                    if dec.get("language"):
                        result["language"] = dec["language"]
            except Exception as e:
                print(f"Groq API skipped/failed: {e}")

    except Exception as e:
        print(f"Analysis Error: {e}")

    return result
