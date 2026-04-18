import asyncio
import os
import random
import json
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from supabase import create_client
from langdetect import detect

from utils.ad_classifier import calculate_ad_score
from utils.url_resolver import resolve_real_url
from utils.offer_extractor import extract_offer_intelligence
from utils.lp_analyzer import analyze_landing_page_with_page, click_cta_and_capture
from utils.screenshot_manager import take_and_store_screenshot

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
    """
    async with semaphore:
        print(f"Starting Deep Analysis for Ad: {ad_id}...")
        
        # 1. Resolve Tracker Redirects Before Browser
        actual_url = resolve_real_url(landing_url)

        # 2. Launch Browser
        async with async_playwright() as p:
            browser = None
            try:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                
                context = await browser.new_context(viewport={"width": 1280, "height": 800})
                page = await context.new_page()
                await Stealth().apply_stealth_async(page)

                # 3. Initial LP Analysis (Passive)
                lp_result = await analyze_landing_page_with_page(page, actual_url)
                
                # 4. Screenshot of Landing Page
                lp_screenshot_url = await take_and_store_screenshot(page, ad_id, "landing_page")
                
                # 5. Core Classification (Neutral Scoring)
                text_content = lp_result.get("text_content", "")
                scoring = calculate_ad_score(
                    url=landing_url, 
                    title=title, 
                    final_url=page.url, 
                    page_content=text_content
                )
                
                final_ad_type = scoring["ad_type"]
                
                # 6. Intelligence Extraction Flow (Affiliate Only)
                intelligence = {}
                click_result = {}
                offer_screenshot_url = None
                
                if final_ad_type == "Affiliate":
                    print(f"Ad {ad_id} is Affiliate. Clicking CTA to extract offer intelligence...")
                    click_result = await click_cta_and_capture(page, "Affiliate")
                    
                    if click_result.get("cta_found"):
                        # Screenshot of the Final Offer Page
                        offer_screenshot_url = await take_and_store_screenshot(page, ad_id, "offer_page")
                        
                        # Extract IDs, Trackers, Networks
                        intelligence = extract_offer_intelligence(
                            final_url=click_result["final_offer_url"],
                            redirect_chain=click_result["redirect_chain"]
                        )
                        print(f"✅ Extracted: {intelligence['affiliate_network']} via {intelligence['tracker_tool']}")

                # 7. Language Detection
                detected_lang = "en"
                try:
                    if text_content:
                        detected_lang = detect(text_content[:500])
                except: pass

                # 8. Persistence
                full_updates = {
                    "ad_type": final_ad_type,
                    "classification_score": scoring.get("score", 0),
                    "classification_confidence": scoring.get("confidence"),
                    "page_subtype": lp_result.get("page_subtype"),
                    
                    # Intelligence Fields
                    "final_offer_url": intelligence.get("final_offer_url") or page.url,
                    "offer_domain": intelligence.get("offer_domain"),
                    "offer_vertical": intelligence.get("offer_vertical"),
                    "affiliate_network": intelligence.get("affiliate_network"),
                    "tracker_tool": intelligence.get("tracker_tool"),
                    "offer_id": intelligence.get("offer_id"),
                    "affiliate_id": intelligence.get("affiliate_id"),
                    "sub_id": intelligence.get("sub_id1"),
                    
                    # CTA interaction
                    "cta_found": click_result.get("cta_found", False),
                    "cta_text": click_result.get("cta_text"),
                    
                    # Evidence data
                    "redirect_chain_json": json.dumps(click_result.get("redirect_chain", [])),
                    "all_params_json": json.dumps(intelligence.get("all_params", {})),
                    
                    # Assets & Metadata
                    "lp_screenshot_url": lp_screenshot_url,
                    "offer_screenshot_url": offer_screenshot_url,
                    "has_countdown": lp_result.get("has_countdown"),
                    "has_video": lp_result.get("has_video"),
                    "cloaking_type": lp_result.get("cloaking", {}).get("cloaking_type"),
                    "language": detected_lang,
                    "analysis_params": scoring.get("signals"),
                    "deep_analyzed_at": "now()"
                }
                
                supabase.table("ads").update(full_updates).eq("id", ad_id).execute()
                print(f"Ad {ad_id} Analysis Complete. Vertical: {intelligence.get('offer_vertical', 'N/A')}")
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
    # Test block
    asyncio.run(deep_analyze_ad("test-id", "https://healthierlivingtips.org/int_di_spl_fbpp/?c=test", "Test Ad"))
