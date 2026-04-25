import asyncio
import os
import random
import json
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from supabase import create_client
from langdetect import detect

import tldextract
from urllib.parse import urlparse
from utils.ad_classifier import calculate_ad_score, is_arbitrage_site, get_ad_network_fingerprints
from utils.url_resolver import resolve_real_url
from utils.offer_extractor import extract_offer_intelligence
from utils.lp_analyzer import analyze_landing_page_with_page, click_cta_and_capture, analyze_page_structure, is_api_endpoint
from utils.url_blacklist import is_meaningful_url
from utils.url_resolver import is_tracking_redirect, resolve_tracking_url

# Supabase initialization
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)



def strip_tracking_params(url: str) -> str:
    """
    Remove known tracking query parameters from URL.
    Keeps only params that are part of the actual offer.
    """
    from urllib.parse import urlparse, urlencode, parse_qs, urlunparse
    
    if not url or not url.startswith("http"): return url

    # Params to REMOVE (pure tracking noise)
    TRACKING_PARAMS_TO_REMOVE = {
        # Outbrain
        "marketerId", "ob_click_id", "outbrainclickid",
        # Taboola
        "tblci", "taboola_hm",
        # Google
        "gclid", "gclsrc", "gbraid", "wbraid",
        # Facebook
        "fbclid",
        # TikTok
        "ttclid",
        # Generic UTM (remove for storage, keep offer params)
        "utm_source", "utm_medium", "utm_campaign",
        "utm_content", "utm_term",
        # Other noise
        "_ga", "_gl", "msclkid",
        "zanpid", "igshid",
        "rtkck", "clickid", "psid", "sjk", "fexp", "jsid"
    }
    
    # Params to KEEP even if they look like tracking
    # (they are part of the actual affiliate offer)
    AFFILIATE_PARAMS_TO_KEEP = {
        "affid", "aff_id", "affiliate_id", "affiliate",
        "hop", "hopId", "cbid",
        "offer_id", "offid", "oid",
        "aff_sub", "subid", "sub1", "s1",
        "aff_id", "pid", "ref",
    }
    
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query, keep_blank_values=True)
        
        # Remove tracking params but keep affiliate params
        cleaned_params = {}
        for k, v in params.items():
            if k in AFFILIATE_PARAMS_TO_KEEP or k not in TRACKING_PARAMS_TO_REMOVE:
                cleaned_params[k] = v
        
        # Rebuild URL
        new_query = urlencode(cleaned_params, doseq=True)
        cleaned = urlunparse((
            parsed.scheme, parsed.netloc, parsed.path,
            parsed.params, new_query, parsed.fragment
        ))
        return cleaned
    
    except Exception:
        return url

def clean_url_for_storage(url: str) -> str:
    """
    Resolves tracking redirects and returns the clean
    human-readable URL suitable for database storage.
    """
    if not url or not url.startswith("http"):
        return url
    
    # Step 1: Check if it's a tracking redirect
    if is_tracking_redirect(url):
        result = resolve_tracking_url(url)
        if result["resolved"]:
            url = result["final"]
            print(f"  ✅ Resolved tracking URL -> {url[:80]}")
        else:
            print(f"  ⚠️ Could not resolve tracking URL: {result.get('reason')}")
    
    # Step 2: Remove tracking parameters from the resolved URL
    url = strip_tracking_params(url)
    
    return url

async def save_to_supabase(ad_id: str, data: dict):
    """Save ad intelligence to database with clean URLs and robust schema handling."""
    
    # Clean all URL fields before saving
    url_fields = [
        "landing", "final_offer_url", "lp_screenshot_url",
        "offer_screenshot_url"
    ]
    
    for field in url_fields:
        if data.get(field):
            data[field] = clean_url_for_storage(data[field])
    
    # Save to Supabase
    try:
        supabase.table("ads").update(data).eq("id", ad_id).execute()
    except Exception as e:
        err_msg = str(e)
        # ROBUST FALLBACK: If a column doesn't exist, remove it and retry
        if "Could not find the" in err_msg and "column" in err_msg:
            import re
            match = re.search(r"'([^']+)' column", err_msg)
            if match:
                missing_col = match.group(1)
                if missing_col in data:
                    print(f"  [DB] Removing unsupported column '{missing_col}' and retrying...")
                    data.pop(missing_col)
                    await save_to_supabase(ad_id, data)
                    return
        
        # Specific fallback for ad networks (older code legacy)
        if "detected_ad_networks" in err_msg:
            data.pop("detected_ad_networks", None)
            supabase.table("ads").update(data).eq("id", ad_id).execute()
        else:
            print(f"⚠️ DB save error for ad {ad_id}: {e}")

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
    
    # 1. FORCED AFFILIATE DETECTION (Highest Priority - Signal beats Content)
    # If these params or domains exist, it's an Affiliate Bridge, period.
    STRONG_AFFILIATE_MARKERS = [
        "hop=", "hopid=", "affid=", "aff_id=", "affiliate_id=", 
        "cep=", "clickid=", "click_id=", "lptoken=", "offid=", "offer_id=",
        "rc_uuid=", "voluumdata=", "voluum", "wellnessgaze", "go.php",
        "bsl=", "t=aff", "sub1=", "sub2=", "sub3=", "tid=", "extclid=",
        "smeagol.revcontent.com", "revcontent.com/cv", "rtkck", "trendingboom"
    ]
    is_aff_signal = any(p in url_lower for p in STRONG_AFFILIATE_MARKERS) or \
                    "voluumdata" in page_content or "/go.php?" in page_content
    
    if is_aff_signal:
        return {
            "ad_type": "Affiliate",
            "confidence": "high",
            "stage": "Signal",
            "reason": "STRONG_AFFILIATE_SIGNAL_DETECTED",
            "skip_deep_analysis": False
        }

    # 2. STRICT ARBITRAGE SCAN
    # If it contains AdSense/Native ad code, and NO affiliate signals were found above.
    fingerprint = get_ad_network_fingerprints(page_content)
    
    if fingerprint["found"] or "syndicatedsearch.goog" in url_lower or "google.com/afs" in url_lower:
        return {
            "ad_type": "Arbitrage",
            "confidence": "high",
            "stage": "Instant",
            "reason": f"EXPLICIT_NETWORK_CODE_DETECTED: {fingerprint.get('network', 'Google AFD')}",
            "detected_ad_networks": fingerprint.get("all_networks", ["Google Adsense"]),
            "skip_deep_analysis": True
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
            landing_url=landing_url,
            raw_final_url=clean_redirect_chain[-1],
            all_captured_urls=clean_redirect_chain
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
            print(f"  [Ad {ad_id}] Navigation complete. Processing results...", flush=True)
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
                # Map classification to DB schema
                fast_updates = {
                    "ad_type": final_ad_type,
                    "classification_confidence": classification.get("confidence"),
                    "classification_reason": classification.get("reason"),
                    "landing": final_url,
                    "deep_analyzed_at": "now()",
                    "detected_ad_networks": classification.get("detected_ad_networks", [])
                }
                await save_to_supabase(ad_id, fast_updates)
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
                    deep_intel = extract_offer_intelligence(
                        landing_url=landing_url,
                        raw_final_url=click_result["final_offer_url"],
                        all_captured_urls=click_result["redirect_chain"]
                    )
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
            
            # PEELING STEP: If the URL looks like a tracker/API but has a target parameter, peel it
            from utils.lp_analyzer import extract_target_from_params
            peeled = extract_target_from_params(potential_final)
            if peeled != potential_final:
                potential_final = peeled

            # Check JS variables for hidden affiliate IDs
            js_vars = lp_result.get("network_intel", {}).get("js_vars", {})
            if js_vars.get("voluum_cid") and not intelligence.get("click_id"):
                intelligence["click_id"] = js_vars["voluum_cid"]
                intelligence["tracker_tool"] = "Voluum (JS)"

            # CRITICAL: If the potential final URL is STILL an API/sync endpoint, try to recover from redirect chain
            if is_api_endpoint(potential_final) or not is_meaningful_url(potential_final):
                chain = click_result.get("redirect_chain", []) + bg_offers
                recovered = False
                for r_url in reversed(chain):
                    # Try to peel each URL in the chain too
                    peeled_r = extract_target_from_params(r_url)
                    target_r = peeled_r if peeled_r != r_url else r_url
                    
                    if not is_api_endpoint(target_r) and is_meaningful_url(target_r):
                        potential_final = target_r
                        recovered = True
                        break
                if not recovered:
                    # Fallback to the landing page ONLY if it's meaningful
                    if is_meaningful_url(final_url):
                        potential_final = final_url
                    else:
                        # Absolute last resort: the original ad link (at least it's an entry point)
                        potential_final = ad_landing 

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
            
            await save_to_supabase(ad_id, full_updates)

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
