import asyncio
import os
import random
import json
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from supabase import create_client
from langdetect import detect

from urllib.parse import urlparse
from utils.ad_classifier import calculate_ad_score, is_arbitrage_site, get_ad_network_fingerprints
from utils.url_resolver import resolve_real_url
from utils.offer_extractor import extract_offer_intelligence
from utils.lp_analyzer import analyze_landing_page_with_page, click_cta_and_capture, analyze_page_structure
from utils.screenshot_manager import take_and_store_screenshot
from utils.url_blacklist import is_meaningful_url

# Supabase Setup
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://avxoumymzbioeabxfcca.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

MAX_CONCURRENT = 3
semaphore = asyncio.Semaphore(MAX_CONCURRENT)

async def check_knowledge_base(landing_url: str) -> dict:
    """Checks if we have a manual override for this domain."""
    try:
        domain = urlparse(landing_url).netloc.lower()
        res = supabase.table("forensic_feedback").select("*").eq("domain", domain).execute()
        if res.data and len(res.data) > 0:
            kb = res.data[0]
            print(f"🧠 Knowledge Base Match: {domain} is {kb['forced_type']}")
            return {
                "ad_type": kb["forced_type"],
                "confidence": "high",
                "reason": "knowledge_base_override"
            }
    except Exception as e:
        print(f"KB Check Error: {e}")
    return None

async def log_error(ad_id, step, message):
    try:
        supabase.table("analysis_logs").insert({
            "ad_id": ad_id, "step": step, "error_message": message
        }).execute()
    except: pass

async def save_classification(ad_id: int, classification: dict):
    """Persists classification results to Supabase."""
    try:
        # Resolve ad_id to int if it's a string from test blocks
        aid = int(ad_id) if isinstance(ad_id, (int, str)) and str(ad_id).isdigit() else ad_id
        
        supabase.table("ads").update({
            "ad_type": classification["ad_type"],
            "classification_confidence": classification.get("confidence", "low"),
            "classification_reason": classification.get("reason", "unknown"),
            "deep_analyzed_at": "now()",
            "detected_ad_networks": classification.get("detected_ad_networks", []),
            "needs_review": classification.get("needs_review", False)
        }).eq("id", aid).execute()
    except Exception as e:
        print(f"Error saving classification for {ad_id}: {e}")

async def classify_with_full_context(
    landing_url: str,
    title: str,
    page_content: str,
    clean_redirect_chain: list,
    page_structure: dict
) -> dict:
    """
    6-stage classification decision tree.
    First match wins — no redundant processing.
    """
    # Stage 0: Knowledge Base
    kb_match = await check_knowledge_base(landing_url)
    if kb_match: return kb_match

    url_lower = landing_url.lower()
    
    # Stage 1: Instant Affiliate Detection
    STRONG_AFFILIATE_PARAMS = [
        "hop=", "hopId=", "affid=", "aff_id=", "affiliate_id=", 
        "cep=", "clickid=", "click_id=", "lptoken=", "offid=", "offer_id="
    ]
    
    for param in STRONG_AFFILIATE_PARAMS:
        if param in url_lower:
            return {
                "ad_type": "Affiliate",
                "confidence": "high",
                "stage": 1,
                "reason": f"affiliate_param_in_url: {param}",
                "skip_deep_analysis": False
            }
    
    # Stage 2: Instant Arbitrage Detection
    fingerprint = get_ad_network_fingerprints(page_content)
    
    if fingerprint["found"] and fingerprint["confidence"] == "high":
        return {
            "ad_type": "Arbitrage",
            "confidence": "high",
            "stage": 2,
            "reason": f"ad_network_fingerprint: {fingerprint['network']}",
            "detected_ad_networks": fingerprint["all_networks"],
            "skip_deep_analysis": True
        }
    
    medium_fingerprint = fingerprint if fingerprint["found"] else None
    
    # Stage 3: Page Structure Analysis
    is_paginated = page_structure.get("is_paginated", False)
    page_number = page_structure.get("page_number", 1)
    high_ad_density = page_structure.get("high_ad_density", False)
    ad_count = page_structure.get("ad_count", 0)
    
    if is_paginated and page_number >= 2:
        return {
            "ad_type": "Arbitrage",
            "confidence": "high",
            "stage": 3,
            "reason": f"slideshow_pagination: page {page_number}",
            "detected_ad_networks": fingerprint.get("all_networks", []),
            "skip_deep_analysis": True
        }
    
    if high_ad_density and ad_count >= 3:
        return {
            "ad_type": "Arbitrage",
            "confidence": "high",
            "stage": 3,
            "reason": f"high_ad_density: {ad_count} ad containers",
            "skip_deep_analysis": True
        }
    
    # Stage 4: Clean Redirect Chain Analysis
    if len(clean_redirect_chain) > 0:
        intelligence = extract_offer_intelligence(
            final_url=clean_redirect_chain[-1],
            redirect_chain=clean_redirect_chain
        )
        
        if intelligence.get("affiliate_id") or intelligence.get("offer_id"):
            return {
                "ad_type": "Affiliate",
                "confidence": "high",
                "stage": 4,
                "reason": "affiliate_params_in_clean_redirect_chain",
                "intelligence": intelligence,
                "skip_deep_analysis": False
            }
        
        if intelligence.get("affiliate_network") not in [None, "Unknown", "Direct/In-house", "No Network Detected"]:
            return {
                "ad_type": "Affiliate",
                "confidence": "high",
                "stage": 4,
                "reason": f"known_network_in_chain: {intelligence['affiliate_network']}",
                "intelligence": intelligence,
                "skip_deep_analysis": False
            }
    
    # Stage 5: Content Scoring System
    arb_check = is_arbitrage_site(
        url=landing_url,
        page_content=page_content,
        clean_chain=clean_redirect_chain
    )
    
    if arb_check["is_arbitrage"]:
        return {
            "ad_type": "Arbitrage",
            "confidence": arb_check["confidence"],
            "stage": 5,
            "reason": f"content_scoring: score={arb_check['score']}",
            "signals": arb_check["signals"],
            "skip_deep_analysis": True
        }
    
    # Stage 6: Inconclusive
    return {
        "ad_type": "Manual Review Required",
        "confidence": "low",
        "stage": 6,
        "reason": "inconclusive_signals",
        "needs_review": True,
        "medium_fingerprint": medium_fingerprint,
        "arb_score": arb_check.get("score", 0),
        "skip_deep_analysis": False
    }

async def deep_analyze_ad(ad_id, landing_url, title):
    """
    Optimized deep analysis with early exit for confirmed arbitrage sites.
    """
    async with semaphore:
        actual_url = resolve_real_url(landing_url)
        async with async_playwright() as p:
            browser = None
            try:
                browser = await p.chromium.launch(headless=True, args=["--no-sandbox", "--disable-dev-shm-usage"])
                context = await browser.new_context(viewport={"width": 1280, "height": 800})
                page = await context.new_page()
                await Stealth().apply_stealth_async(page)

                # Capture redirects manually to avoid heavy overhead
                clean_chain = []
                page.on("response", lambda res: clean_chain.append(res.url) if res.status in [301, 302, 307, 308] else None)

                # Navigation with resource blocking
                await page.route("**/*.{woff,woff2,ttf,mp4,webm}", lambda r: r.abort())
                await page.goto(actual_url, wait_until="domcontentloaded", timeout=45000)
                await asyncio.sleep(2.0)

                # Feature detection
                page_content = await page.content()
                structure = await analyze_page_structure(page)

                # 1. Classification (Decision Tree)
                classification = await classify_with_full_context(
                    landing_url=landing_url,
                    title=title,
                    page_content=page_content,
                    clean_redirect_chain=clean_chain,
                    page_structure=structure
                )

                # 2. Early Exit for Arbitrage
                if classification.get("skip_deep_analysis"):
                    await save_classification(ad_id, classification)
                    print(f"⚡ Fast-classified [{classification['stage']}]: {ad_id} -> {classification['ad_type']} ({classification['reason']})")
                    return classification

                # 3. Deep analysis for Affiliate candidates
                final_ad_type = classification["ad_type"]
                intelligence = classification.get("intelligence", {})
                click_result = {}
                offer_screenshot_url = None
                
                lp_screenshot_url = await take_and_store_screenshot(page, ad_id, "landing_page")

                if final_ad_type == "Affiliate" or final_ad_type == "Manual Review Required":
                    print(f"Ad {ad_id}: Doing deep analysis (Stage {classification['stage']})...")
                    click_result = await click_cta_and_capture(page, "Affiliate")
                    
                    if click_result.get("cta_found"):
                        offer_screenshot_url = await take_and_store_screenshot(page, ad_id, "offer_page")
                        deep_intel = extract_offer_intelligence(
                            final_url=click_result["final_offer_url"],
                            redirect_chain=click_result["redirect_chain"],
                            landing_url=landing_url
                        )
                        intelligence.update(deep_intel)
                        print(f"✅ Deep Intel Extracted: {intelligence.get('affiliate_network')}")

                # Final Persistence
                detected_lang = "en"
                try: detected_lang = detect(page_content[:500])
                except: pass

                full_updates = {
                    "ad_type": final_ad_type,
                    "classification_confidence": classification.get("confidence"),
                    "classification_reason": classification.get("reason"),
                    "final_offer_url": intelligence.get("final_offer_url") or click_result.get("final_offer_url") or page.url,
                    "offer_domain": intelligence.get("offer_domain"),
                    "affiliate_network": intelligence.get("affiliate_network"),
                    "tracker_tool": intelligence.get("tracker_tool"),
                    "offer_id": intelligence.get("offer_id"),
                    "affiliate_id": intelligence.get("affiliate_id"),
                    "cta_found": click_result.get("cta_found", False),
                    "redirect_chain_json": json.dumps(click_result.get("redirect_chain", [])),
                    "needs_review": classification.get("needs_review", False),
                    "lp_screenshot_url": lp_screenshot_url,
                    "offer_screenshot_url": offer_screenshot_url,
                    "language": detected_lang,
                    "deep_analyzed_at": "now()",
                    "detected_ad_networks": classification.get("detected_ad_networks", [])
                }
                
                supabase.table("ads").update(full_updates).eq("id", ad_id).execute()
                print(f"Ad {ad_id} Complete: {final_ad_type}")
                return classification

            except Exception as e:
                print(f"Error for {ad_id}: {e}")
                await log_error(ad_id, "master_script", str(e))
                return {"error": str(e)}
            finally:
                if browser: await browser.close()

if __name__ == "__main__":
    asyncio.run(deep_analyze_ad("test", "https://example.com", "Test"))
