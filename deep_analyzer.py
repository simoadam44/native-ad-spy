import asyncio
import os
import random
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from supabase import create_client
from langdetect import detect

from utils.ad_classifier import classify_ad
from utils.lp_analyzer import analyze_landing_page_with_page
from utils.screenshot_manager import take_and_store_screenshot
from utils.param_extractor import extract_affiliate_params

# Supabase Setup
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://avxoumymzbioeabxfcca.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX")
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
    Uses a semaphore to limit concurrent browser instances.
    """
    async with semaphore:
        print(f"Starting Deep Analysis for Ad: {ad_id}...")
        
        # Step 1: Quick Classification
        classification = classify_ad(landing_url, title)
        
        # Step 2: Skip browser if high confidence Arbitrage (optimization)
        if classification["ad_type"] == "Arbitrage" and classification["confidence"] == "high":
            print(f"Ad {ad_id} classified as Arbitrage. Skipping browser.")
            await supabase.table("ads").update({
                "ad_type": "Arbitrage",
                "deep_analyzed_at": "now()"
            }).eq("id", ad_id).execute()
            return {"ad_type": "Arbitrage", "skipped": True}

        # Step 3: Launch Browser for Deep Analysis
        async with async_playwright() as p:
            browser = None
            try:
                browser = await p.chromium.launch(
                    headless=True,
                    args=["--no-sandbox", "--disable-dev-shm-usage"]
                )
                
                # Random UA
                user_agents = [
                    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
                ]
                
                context = await browser.new_context(
                    user_agent=random.choice(user_agents),
                    viewport={"width": 1280, "height": 800}
                )
                page = await context.new_page()
                await Stealth().apply_stealth_async(page)

                # Block heavy assets to save memory
                async def block_assets(route):
                    if route.request.resource_type in ["font", "media"]:
                        await route.abort()
                    elif "analytics" in route.request.url or "facebook" in route.request.url:
                        await route.abort()
                    else:
                        await route.continue_()
                await page.route("**/*", block_assets)

                # Step 4: Perform LP Analysis
                lp_result = await analyze_landing_page_with_page(page, landing_url)
                
                # Step 5: Take LP Screenshot
                lp_screenshot_url = await take_and_store_screenshot(page, ad_id, "landing_page")
                
                # Step 6: Offer Screenshot (if navigated)
                offer_screenshot_url = None
                if lp_result.get("final_offer_url") and lp_result["final_offer_url"] != landing_url:
                    offer_screenshot_url = await take_and_store_screenshot(page, ad_id, "offer_page")

                # Step 7: Final Parameter Extraction & Cloaking override
                final_offer_url = lp_result.get("final_offer_url")
                params = extract_affiliate_params(final_offer_url) if final_offer_url else {}
                
                final_ad_type = classification["ad_type"]
                if lp_result.get("cloaking", {}).get("force_affiliate"):
                    final_ad_type = "Affiliate"
                
                # Step 8: Language Detection
                detected_lang = "en"
                try:
                    detected_lang = detect(text_content[:500])
                except:
                    pass

                # Step 9: Persistence
                full_updates = {
                    "ad_type": final_ad_type,
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
                    "price_found": lp_result.get("price_found"),
                    "lp_screenshot_url": lp_screenshot_url,
                    "offer_screenshot_url": offer_screenshot_url,
                    "cloaking_type": lp_result.get("cloaking", {}).get("cloaking_type"),
                    "language": lp_result.get("language") or detected_lang,
                    "deep_analyzed_at": "now()"
                }
                
                supabase.table("ads").update(full_updates).eq("id", ad_id).execute()
                print(f"Ad {ad_id} Analysis Complete. Type: {final_ad_type}")
                return full_updates

            except Exception as e:
                print(f"Master Analyzer Error for {ad_id}: {e}")
                await log_error(ad_id, "master_script", str(e))
                # Fallback persistence so queue consumer doesn't freeze
                supabase.table("ads").update({
                    "ad_type": "Manual Review Required",
                    "deep_analyzed_at": "now()"
                }).eq("id", ad_id).execute()
                
                return {"error": str(e)}
            finally:
                if browser:
                    await browser.close()

if __name__ == "__main__":
    # Test single
    asyncio.run(deep_analyze_ad("test-id", "https://example.com", "Buy Now 50% Off"))
