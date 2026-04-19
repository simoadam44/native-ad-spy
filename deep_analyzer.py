import asyncio
import os
import random
import json
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from supabase import create_client
from langdetect import detect

from urllib.parse import urlparse
from utils.ad_classifier import calculate_ad_score, is_arbitrage_site
from utils.url_resolver import resolve_real_url
from utils.offer_extractor import extract_offer_intelligence
from utils.lp_analyzer import analyze_landing_page_with_page, click_cta_and_capture
from utils.screenshot_manager import take_and_store_screenshot
from utils.url_blacklist import is_meaningful_url

# Supabase Setup
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://avxoumymzbioeabxfcca.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

MAX_CONCURRENT = 3
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

async def check_knowledge_base(landing_url: str) -> dict:
    try:
        domain = urlparse(landing_url).netloc.lower()
        res = supabase.table("forensic_feedback").select("*").eq("domain", domain).execute()
        if res.data and len(res.data) > 0:
            kb = res.data[0]
            return {
                "ad_type": kb["forced_type"],
                "confidence": "high",
                "reason": "knowledge_base_override"
            }
    except: pass
    return None

async def log_error(ad_id, step, message):
    try:
        supabase.table("analysis_logs").insert({
            "ad_id": ad_id, "step": step, "error_message": message
        }).execute()
    except: pass

async def classify_with_full_context(
    landing_url: str,
    title: str,
    final_url: str,
    clean_redirect_chain: list,
    page_structure: dict,
    page_content: str,
    orig_scoring: dict
) -> dict:
    kb_match = await check_knowledge_base(landing_url)
    if kb_match: return kb_match

    url_lower = landing_url.lower()
    final_url_lower = final_url.lower()

    if "lptoken=" in url_lower or ("utm_campaign=" in url_lower and "content_id=" in url_lower):
        return {"ad_type": "Affiliate", "confidence": "high", "reason": "professional_affiliate_tracking_detected"}

    aff_params = ["affid=", "affiliate_id=", "offid=", "offer_id=", "hop=", "cbid=", "clickbank"]
    if any(p in final_url_lower for p in aff_params) or any(p in url_lower for p in aff_params):
        return {"ad_type": "Affiliate", "confidence": "high", "reason": "aff_params_detected"}

    if page_structure.get("is_paginated"):
        return {"ad_type": "Arbitrage", "confidence": "high", "reason": "paginated_slideshow_arb"}
    
    arb_scan = is_arbitrage_site(final_url, page_content)
    if arb_scan["is_arbitrage"] and arb_scan["score"] >= 6:
        return {"ad_type": "Arbitrage", "confidence": "high", "reason": "strong_arb_content_signals"}

    # Forensic Redirect Analysis
    intel = extract_offer_intelligence(final_url, clean_redirect_chain, landing_url)
    if intel.get("affiliate_network") != "No Network Detected":
        return {"ad_type": "Affiliate", "confidence": "high", "reason": "forensic_network_found", "forensic_intel": intel}
    if intel.get("tracker_tool") != "No Tracker Detected":
        return {"ad_type": "Affiliate", "confidence": "medium", "reason": "forensic_tracker_found", "forensic_intel": intel}

    if orig_scoring["score"] >= 3:
        return {"ad_type": "Affiliate", "confidence": "medium", "reason": "orig_score_fallback"}
    
    return {"ad_type": "Manual Review Required", "confidence": "low", "reason": "inconclusive_signals"}

async def deep_analyze_ad(ad_id, landing_url, title):
    async with semaphore:
        actual_url = resolve_real_url(landing_url)
        async with async_playwright() as p:
            browser = None
            try:
                browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
                context = await browser.new_context(viewport={"width": 1280, "height": 800})
                page = await context.new_page()
                await Stealth().apply_stealth_async(page)

                lp_result = await analyze_landing_page_with_page(page, actual_url)
                lp_screenshot_url = await take_and_store_screenshot(page, ad_id, "landing_page")
                
                text_content = lp_result.get("text_content", "")
                orig_scoring = calculate_ad_score(url=landing_url, title=title, final_url=page.url, page_content=text_content)
                
                classification = await classify_with_full_context(
                    landing_url=landing_url, title=title, final_url=page.url,
                    clean_redirect_chain=lp_result.get("clean_redirect_chain", []),
                    page_structure=lp_result.get("page_structure", {}),
                    page_content=text_content, orig_scoring=orig_scoring
                )
                
                final_ad_type = classification["ad_type"]
                # Start with forensic intel found during classification (if any)
                intelligence = classification.get("forensic_intel", {})
                click_result = {}
                offer_screenshot_url = None
                
                if final_ad_type == "Affiliate":
                    print(f"Ad {ad_id}: Affiliate detected. Attempting CTA click...")
                    click_result = await click_cta_and_capture(page, "Affiliate")
                    
                    if click_result.get("cta_found"):
                        offer_screenshot_url = await take_and_store_screenshot(page, ad_id, "offer_page")
                        # Overwrite with deep level intelligence from the offer page
                        deep_intel = extract_offer_intelligence(
                            final_url=click_result["final_offer_url"],
                            redirect_chain=click_result["redirect_chain"],
                            landing_url=landing_url
                        )
                        intelligence.update(deep_intel)
                        print(f"✅ Deep Intel Extracted: {intelligence.get('affiliate_network')}")

                detected_lang = "en"
                try: 
                    if text_content: detected_lang = detect(text_content[:500])
                except: pass

                full_updates = {
                    "ad_type": final_ad_type,
                    "classification_score": orig_scoring.get("score", 0),
                    "classification_confidence": classification.get("confidence"),
                    "page_subtype": lp_result.get("page_subtype") or intelligence.get("page_subtype"),
                    "final_offer_url": intelligence.get("final_offer_url") or click_result.get("final_offer_url") or page.url,
                    "offer_domain": intelligence.get("offer_domain"),
                    "affiliate_network": intelligence.get("affiliate_network"),
                    "tracker_tool": intelligence.get("tracker_tool"),
                    "offer_id": intelligence.get("offer_id"),
                    "affiliate_id": intelligence.get("affiliate_id"),
                    "sub_id": intelligence.get("sub_id1"),
                    "cta_found": click_result.get("cta_found", False),
                    "cta_text": click_result.get("cta_text"),
                    "redirect_chain_json": json.dumps(click_result.get("redirect_chain", [])),
                    "all_params_json": json.dumps(intelligence.get("all_params", {})),
                    "traffic_source": intelligence.get("traffic_source"),
                    "tracker_id": intelligence.get("tracker_id"),
                    "needs_review": intelligence.get("needs_review", False) or final_ad_type == "Manual Review Required",
                    "path_segments": json.dumps(intelligence.get("path_segments", [])),
                    "classification_reason": classification.get("reason"),
                    "lp_screenshot_url": lp_screenshot_url,
                    "offer_screenshot_url": offer_screenshot_url,
                    "has_countdown": lp_result.get("has_countdown", False),
                    "has_video": lp_result.get("has_video", False),
                    "language": detected_lang,
                    "deep_analyzed_at": "now()"
                }
                
                supabase.table("ads").update(full_updates).eq("id", ad_id).execute()
                print(f"Ad {ad_id} Complete: {final_ad_type}")
                return full_updates

            except Exception as e:
                print(f"Error for {ad_id}: {e}")
                await log_error(ad_id, "master_script", str(e))
                supabase.table("ads").update({"ad_type": "Manual Review Required", "deep_analyzed_at": "now()", "classification_reason": f"error: {str(e)}"}).eq("id", ad_id).execute()
                return {"error": str(e)}
            finally:
                if browser: await browser.close()

if __name__ == "__main__":
    asyncio.run(deep_analyze_ad("test", "https://example.com", "Test"))
