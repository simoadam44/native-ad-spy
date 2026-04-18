import asyncio
import os
import random
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from supabase import create_client
from langdetect import detect

from utils.ad_classifier import calculate_ad_score
from utils.lp_analyzer import analyze_landing_page_with_page
from utils.screenshot_manager import take_and_store_screenshot
from utils.param_extractor import extract_affiliate_params
from utils.url_resolver import resolve_real_url

# Supabase Setup
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://avxoumymzbioeabxfcca.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

MAX_CONCURRENT = 3
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

async def log_error(ad_id, step, message):
    try:
        supabase.table("analysis_logs").insert({
            "ad_id": ad_id,
            "step": step,
            "error_message": message
        }).execute()
    except:
        pass

async def deep_analyze_ad(ad_id, landing_url, title):
    """
    Ties together all utilities to perform a deep analysis of a single ad.
    Uses a neutral scoring system and tracker resolution.
    """
    async with semaphore:
        print(f"Starting Deep Analysis for Ad: {ad_id}...")
        
        # FIX 2: Follow Tracker Redirect URLs First
        actual_url = resolve_real_url(landing_url)
        if actual_url != landing_url:
            print(f"Resolved Tracker: {landing_url[:40]} -> {actual_url[:60]}...")

        # Step 3: Launch Browser for Deep Analysis
        async with async_playwright() as p:
            browser = None
            try:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                
                context = await browser.new_context(
                    viewport={"width": 1280, "height": 800}
                )
                page = await context.new_page()
                await Stealth().apply_stealth_async(page)

                # Step 4: Perform LP Analysis
                lp_result = await analyze_landing_page_with_page(page, actual_url)
                
                # Step 5: Screenshots
                lp_screenshot_url = await take_and_store_screenshot(page, ad_id, "landing_page")
                offer_screenshot_url = None
                if lp_result.get("final_offer_url") and lp_result["final_offer_url"] != actual_url:
                    offer_screenshot_url = await take_and_store_screenshot(page, ad_id, "offer_page")

                # Step 6: Parameter Extraction
                final_offer_url = lp_result.get("final_offer_url") or actual_url
                params = extract_affiliate_params(final_offer_url)
                
                # Step 7: Neutral Scoring System (Fix 4)
                text_content = lp_result.get("text_content", "")
                scoring = calculate_ad_score(
                    url=landing_url, 
                    title=title, 
                    final_url=final_offer_url, 
                    page_content=text_content
                )
                
                final_ad_type = scoring["ad_type"]
                
                # Step 8: Language Detection
                detected_lang = "en"
                try:
                    if text_content:
                        detected_lang = detect(text_content[:500])
                except: pass

                # Step 9: Persistence (Fix 1)
                full_updates = {
                    "ad_type": final_ad_type,
                    "classification_score": scoring.get("score", 0),
                    "classification_confidence": scoring.get("confidence"),
                    "page_subtype": lp_result.get("page_subtype"),
                    "affiliate_id": params.get("affiliate_id"),
                    "offer_id": params.get("offer_id"),
                    "sub_id": params.get("sub_id1"),
                    "final_offer_url": final_offer_url,
                    "detected_network": lp_result.get("detected_network") or params.get("detected_network"),
                    "detected_tracker": lp_result.get("detected_tracker"),
                    "cta_text": lp_result.get("cta_text"),
                    "has_countdown": lp_result.get("has_countdown"),
                    "has_video": lp_result.get("has_video"),
                    "lp_screenshot_url": lp_screenshot_url,
                    "offer_screenshot_url": offer_screenshot_url,
                    "cloaking_type": lp_result.get("cloaking", {}).get("cloaking_type"),
                    "language": detected_lang,
                    "analysis_params": scoring.get("signals"), # Storing tokens for transparency
                    "deep_analyzed_at": "now()"
                }
                
                # IMPORTANT: No wrong fallback logic here. 
                # Ad type remains what the scoring system decided.
                
                supabase.table("ads").update(full_updates).eq("id", ad_id).execute()
                print(f"Ad {ad_id} Analysis Complete. Type: {final_ad_type} (Score: {scoring.get('score')})")
                return full_updates

            except Exception as e:
                print(f"Master Analyzer Error for {ad_id}: {e}")
                await log_error(ad_id, "master_script", str(e))
                supabase.table("ads").update({
                    "ad_type": "Manual Review Required",
                    "deep_analyzed_at": "now()"
                }).eq("id", ad_id).execute()
                return {"error": str(e)}
            finally:
                if browser: await browser.close()

if __name__ == "__main__":
    asyncio.run(deep_analyze_ad("test-id", "https://example.com", "Buy Now 50% Off"))
