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
from utils.lp_analyzer import analyze_landing_page_with_page, click_cta_and_capture, analyze_page_structure, is_api_endpoint
from utils.url_blacklist import is_meaningful_url

# Supabase initialization
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def save_classification(ad_id: int, classification: dict):
    """Persists classification results to Supabase."""
    try:
        aid = int(ad_id) if isinstance(ad_id, (int, str)) and str(ad_id).isdigit() else ad_id
        
        updates = {
            "ad_type": classification["ad_type"],
            "classification_confidence": classification.get("confidence", "low"),
            "classification_reason": classification.get("reason", "unknown"),
            "deep_analyzed_at": "now()",
            "detected_ad_networks": classification.get("detected_ad_networks", []),
            "needs_review": classification.get("needs_review", False)
        }
        if "landing" in classification:
            updates["landing"] = classification["landing"]

        
        try:
            supabase.table("ads").update(updates).eq("id", aid).execute()
        except Exception as pge:
            if "detected_ad_networks" in str(pge):
                updates.pop("detected_ad_networks")
                supabase.table("ads").update(updates).eq("id", aid).execute()
            else: raise pge

    except Exception as e:
        print(f"Error saving classification for {ad_id}: {e}")

async def log_error(ad_id: int, stage: str, message: str):
    """Logs errors to analysis_logs table."""
    try:
        supabase.table("analysis_logs").insert({
            "ad_id": ad_id,
            "stage": stage,
            "level": "error",
            "message": message
        }).execute()
    except: pass

async def take_and_store_screenshot(page, ad_id, screenshot_type):
    """Placeholder for screenshot logic."""
    return f"https://placeholder.com/{screenshot_type}_{ad_id}.png"

async def classify_with_full_context(
    landing_url: str,
    title: str,
    final_url: str,
    clean_redirect_chain: list,
    page_structure: dict,
    page_content: str,
    ad_id: int = None
) -> dict:
    """
    MASTER CLASSIFICATION ENGINE - Reinforced Master Rule.
    """
    # 0. Knowledge Base Match
    forced_domains = {
        "buy.com": {"ad_type": "Direct Sales"},
        "amazon.com": {"ad_type": "Affiliate"}
    }
    domain = urlparse(landing_url).netloc.lower().replace("www.", "")
    kb_match = forced_domains.get(domain)
    if kb_match: return kb_match

    url_lower = landing_url.lower()
    
    # 1. STRICT MASTER RULE - INSTANT ARBITRAGE SCAN (Highest priority)
    # If it contains AdSense/Native ad code, it's Arbitrage, period.
    fingerprint = get_ad_network_fingerprints(page_content)
    
    if fingerprint["found"]:
        # Only exception: Known affiliate landing page domains (rare)
        # But for big publishers, fingerprint always wins.
        return {
            "ad_type": "Arbitrage",
            "confidence": "high",
            "stage": "Instant",
            "reason": f"EXPLICIT_NETWORK_CODE_DETECTED: {fingerprint['network']}",
            "detected_ad_networks": fingerprint["all_networks"],
            "skip_deep_analysis": True
        }

    # 2. FORCED AFFILIATE DETECTION
    # If these params exist and NO ad code was found above
    STRONG_AFFILIATE_PARAMS = [
        "hop=", "hopId=", "affid=", "aff_id=", "affiliate_id=", 
        "cep=", "clickid=", "click_id=", "lptoken=", "offid=", "offer_id=",
        "rc_uuid=", "utm_source=", "utm_medium=", "boost_id=", "widget_id=",
        "voluumdata=", "voluum",  # Voluum affiliate tracker
        "bsl=", "t=aff",          # Other common affiliate bridges
        "sub1=", "sub2=", "sub3="  # Generic sub-tracking params
    ]
    is_aff_param_found = any(p in url_lower for p in STRONG_AFFILIATE_PARAMS)
    
    if is_aff_param_found:
        return {
            "ad_type": "Affiliate",
            "confidence": "high",
            "stage": 1,
            "reason": "affiliate_param_found_no_ad_code",
            "skip_deep_analysis": False
        }

    # Page Structure signals
    is_paginated = page_structure.get("is_paginated", False)
    page_number = page_structure.get("page_number", 1)
    high_ad_density = page_structure.get("high_ad_density", False)
    ad_count = page_structure.get("ad_count", 0)

    if (is_paginated and page_number >= 2) or (high_ad_density and ad_count >= 3):
        return {
            "ad_type": "Manual Review Required",
            "confidence": "medium",
            "stage": 3,
            "reason": "suspicious_structure_no_ad_code",
            "skip_deep_analysis": False
        }

    # 4. Clean Redirect Chain Analysis
    if len(clean_redirect_chain) > 0:
        intelligence = extract_offer_intelligence(
            final_url=clean_redirect_chain[-1],
            redirect_chain=clean_redirect_chain
        )
        if intelligence.get("affiliate_id") or intelligence.get("offer_id") or \
           intelligence.get("affiliate_network") not in [None, "Unknown", "No Network Detected"]:
            return {
                "ad_type": "Affiliate",
                "confidence": "high",
                "stage": 4,
                "reason": f"known_aff_signature_in_chain: {intelligence.get('affiliate_network')}",
                "intelligence": intelligence,
                "skip_deep_analysis": False
            }

    # 5. Content Scoring
    score_check = calculate_ad_score(landing_url, title, final_url, page_content)
    if score_check["ad_type"] == "Affiliate":
        return {
            "ad_type": "Affiliate",
            "confidence": score_check["confidence"],
            "stage": 5,
            "reason": f"scoring_system: {score_check['score']}",
            "skip_deep_analysis": False
        }

    return {
        "ad_type": "Unknown",
        "confidence": "low",
        "stage": 6,
        "reason": "no_conclusive_signals",
        "skip_deep_analysis": False
    }

async def deep_analyze_ad(ad_id, landing_url, title):
    """Full analysis flow."""
    browser = None
    try:
        print(f"  [Ad {ad_id}] Launching browser...", flush=True)
        async with async_playwright() as p:
            # Add GHA-compatible flags
            browser = await p.chromium.launch(
                headless=True,
                args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
            )
            print(f"  [Ad {ad_id}] Creating context...", flush=True)
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            page = await context.new_page()
            
            # Apply stealth
            await Stealth().apply_stealth_async(page)
            
            # 1. Detailed Landing Page Analysis
            print(f"  [Ad {ad_id}] Navigating to landing page...", flush=True)
            lp_result = await analyze_landing_page_with_page(page, landing_url)
            page_content = lp_result.get("text_content", "")
            final_url = lp_result.get("final_offer_url", landing_url)
            clean_redirect_chain = lp_result.get("clean_redirect_chain", [])
            page_structure = lp_result.get("page_structure", {})

            # 2. Master Classification
            print(f"  [Ad {ad_id}] Classifying content...", flush=True)
            classification = await classify_with_full_context(
                landing_url=landing_url,
                title=title,
                final_url=final_url,
                clean_redirect_chain=clean_redirect_chain,
                page_structure=page_structure,
                page_content=lp_result.get("full_html", page_content),
                ad_id=ad_id
            )
            
            final_ad_type = classification["ad_type"]
            classification["landing"] = final_url
            
            # 3. Final Persistence & Intel Gathering
            if classification.get("skip_deep_analysis"):
                print(f"  [Ad {ad_id}] Fast-classified as {final_ad_type}", flush=True)
                await save_classification(ad_id, classification)
                return classification

            # Deep Intel for Affiliate/Review
            intelligence = classification.get("intelligence", {})
            click_result = {}
            offer_screenshot_url = None
            
            print(f"  [Ad {ad_id}] Taking screenshot...", flush=True)
            lp_screenshot_url = await take_and_store_screenshot(page, ad_id, "landing_page")

            if final_ad_type in ["Affiliate", "Manual Review Required"]:
                print(f"  [Ad {ad_id}] Attempting CTA click...", flush=True)
                click_result = await click_cta_and_capture(page, "Affiliate")
                if click_result.get("cta_found"):
                    print(f"  [Ad {ad_id}] CTA found! Analyzing offer destination...", flush=True)
                    offer_screenshot_url = await take_and_store_screenshot(page, ad_id, "offer_page")
                    deep_intel = extract_offer_intelligence(final_url=click_result["final_offer_url"], redirect_chain=click_result["redirect_chain"])
                    intelligence.update(deep_intel)
                    print(f"[Deep Intel Extracted]: {intelligence.get('affiliate_network')}")

            # Persist full results
            detected_lang = "en"
            try: detected_lang = detect(page_content[:500])
            except: pass

            # 3. Final Offer URL Selection Logic (Hardened)
            # Preference order: Network Intel -> HTML Extraction -> Click Result -> Current Page
            
            # Check background network captures first (AdPlexity style)
            bg_offers = lp_result.get("background_offers", [])
            network_final = None
            if bg_offers:
                # Use the last background offer that isn't a sync pixel
                for bg_url in reversed(bg_offers):
                    if not is_api_endpoint(bg_url) and is_meaningful_url(bg_url):
                        network_final = bg_url
                        break

            potential_final = network_final or intelligence.get("final_offer_url") or click_result.get("final_offer_url") or page.url
            
            # Check JS variables for hidden affiliate IDs
            js_vars = lp_result.get("network_intel", {}).get("js_vars", {})
            if js_vars.get("voluum_cid") and not intelligence.get("click_id"):
                intelligence["click_id"] = js_vars["voluum_cid"]
                intelligence["tracker_tool"] = "Voluum (JS)"

            # CRITICAL: If the potential final URL is an API/sync endpoint, try to recover from redirect chain
            if is_api_endpoint(potential_final) or not is_meaningful_url(potential_final):
                chain = click_result.get("redirect_chain", []) + bg_offers
                recovered = False
                for r_url in reversed(chain):
                    if not is_api_endpoint(r_url) and is_meaningful_url(r_url):
                        potential_final = r_url
                        recovered = True
                        break
                if not recovered:
                    potential_final = final_url # Fallback to the landing page if all redirects are APIs

            full_updates = {
                "ad_type": final_ad_type,
                "classification_confidence": classification.get("confidence"),
                "classification_reason": classification.get("reason"),
                "landing": final_url,  # The actual resolved landing page
                "final_offer_url": potential_final,
                "offer_domain": tldextract.extract(potential_final).registered_domain if potential_final else None,
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
            
            try:
                supabase.table("ads").update(full_updates).eq("id", ad_id).execute()
            except Exception as pge:
                if "detected_ad_networks" in str(pge):
                    full_updates.pop("detected_ad_networks")
                    supabase.table("ads").update(full_updates).eq("id", ad_id).execute()
                else: raise pge

            print(f"Ad {ad_id} Complete: {final_ad_type}")
            return classification

    except Exception as e:
        print(f"Error for {ad_id}: {e}")
        return {"error": str(e)}
    finally:
        if browser:
            try:
                # Give browser.close() a hard 10s limit
                await asyncio.wait_for(browser.close(), timeout=10.0)
            except:
                print(f"  [Ad {ad_id}] Warning: Browser close timed out.", flush=True)
