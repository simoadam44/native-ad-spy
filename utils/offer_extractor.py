import json
import re
import tldextract
from urllib.parse import urlparse, parse_qs

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 1. PRE-PROCESSING: Chain Cleaning & Ranking
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def clean_and_rank_chain(raw_chain: list, landing_url: str) -> list:
    """Filters out technical noise and ranks URLs by potential intelligence value."""
    cleaned = []
    landing_domain = tldextract.extract(landing_url).registered_domain
    
    # 1. Noise Filtering
    NOISE_EXTS = {".ts", ".m3u8", ".mp4", ".mp3", ".webm", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".css", ".js", ".woff", ".woff2", ".ico"}
    NOISE_PATTERNS = [
        "google-analytics", "gtm.js", "clarity.ms", "facebook.com/tr", "bing.com/bat", "doubleclick.net",
        "deepintent", "stackadapt", "smartadserver", "sync.taboola.com", "id5-sync.com", "adsrvr.org", "adnxs.com",
        "rubiconproject", "prebid", "3lift.com", "onetag-sys.com", "brainlyads.com", "fastlane.json",
        "cdn.taboola.com", "images.taboola.com", "cloudfront.net"
    ]
    
    for url in raw_chain:
        if not url or not isinstance(url, str): continue
        u_lower = url.lower()
        
        # Skip static assets
        if any(u_lower.endswith(ext) for ext in NOISE_EXTS): continue
        # Skip known ad-tech noise
        if any(p in u_lower for p in NOISE_PATTERNS): continue
        
        # 2. Scoring
        score = 0
        parsed = urlparse(u_lower)
        domain_info = tldextract.extract(u_lower)
        reg_domain = domain_info.registered_domain
        params = parse_qs(parsed.query)
        
        # Affiliate Network Domain
        NET_DOMAINS = ["clickbank.net", "everflow.io", "eflow.io", "go2cloud.org", "go2jump.org", "impact.com", "sjv.io", "awin1.com", "rakuten", "linksynergy"]
        if any(nd in reg_domain for nd in NET_DOMAINS): score += 3
        
        # Affiliate Params
        AFF_PARAMS = ["affid", "aff_id", "hop", "offid", "offer_id", "clickid", "click_id"]
        if any(p in params for p in AFF_PARAMS): score += 3
        
        # Tracker Signatures
        if any(tk in u_lower for tk in ["voluum", "binom", "redtrack", "rdtk.io", "keitaro"]): score += 2
        
        # Domain Change
        if reg_domain and reg_domain != landing_domain: score += 2
        
        # Path Signals
        if any(path_sig in parsed.path for path_sig in ["/vsl/", "/offer/", "/lander/", "/checkout/"]): score += 1
        
        # Same domain as landing (often just an internal redirect)
        if reg_domain == landing_domain: score -= 2
        
        cleaned.append({"url": url, "score": score, "domain": reg_domain})
        
    # Sort by score descending and return top URLs
    cleaned.sort(key=lambda x: x["score"], reverse=True)
    return [item["url"] for item in cleaned[:10]]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 2. DEAD-END DETECTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def is_dead_end_url(url: str) -> tuple:
    """Returns (is_dead_end, reason). Checks if URL is an API or postback."""
    if not url: return False, None
    u_lower = url.lower()
    
    # 1. Video APIs
    DEAD_END_DOMAINS = ["api.vturb.com.br", "vturb.com", "player.vturb.com", "fast.wistia.net/embed", "vimeo.com/api", "youtube.com/api"]
    if any(d in u_lower for d in DEAD_END_DOMAINS):
        return True, "video_api_endpoint"
        
    # 2. Conversion Postbacks
    POSTBACK_PATTERNS = ["/sdk/conversion", "/postback?", "/s2s/", "/server-to-server", "/conversion?effp=", "/track/conversion", "/pixel/fire"]
    if any(p in u_lower for p in POSTBACK_PATTERNS):
        return True, "conversion_postback"
        
    # 3. Checkout (Special case: is the offer, but is a tracking dead end)
    CHECKOUT_DOMAINS = ["checkout.stripe.com", "paypal.com/checkout", "pay.google.com", "secure.2checkout.com"]
    if any(d in u_lower for d in CHECKOUT_DOMAINS):
        return False, "direct_checkout" # It's not a "dead end" for the user, but for the tracker
        
    return False, None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 3. NETWORK DETECTION ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NETWORK_SIGNATURES = {
    "ClickBank": {
        "confidence": "high",
        "detect_fn": lambda url, params: (
            "hop.clickbank.net" in url or "hop=" in url or "hopId=" in url or 
            "/cb/vsl/" in url or ("/cb/" in url and "affiliate=" in url) or
            "pay.clickbank.net" in url
        )
    },
    "Everflow": {
        "confidence": "high",
        "detect_fn": lambda url, params: (
            "effp=" in url or "ef_click_id=" in url or "vndr=evf" in url or 
            "djpcraze.com" in url or "everflow.io" in url or "eflow.io" in url
        )
    },
    "Tune/HasOffers": {
        "confidence": "high",
        "detect_fn": lambda url, params: (
            "hasoffers.com" in url or "tune.com" in url or "go2cloud.org" in url or
            ("offer_id" in params and "aff_id" in params)
        )
    },
    "Impact": {
        "confidence": "high",
        "detect_fn": lambda url, params: any(d in url for d in ["impact.com", "impactradius.com", "sjv.io", "prf.hn"])
    },
    "ShareASale": {
        "confidence": "high",
        "detect_fn": lambda url, params: "shareasale.com" in url
    },
    "CJ (Commission Junction)": {
        "confidence": "high",
        "detect_fn": lambda url, params: any(d in url for d in ["anrdoezrs.net", "dpbolvw.net", "tkqlhce.com", "jdoqocy.com", "qksrv.net", "cj.com"])
    },
    "Awin": {
        "confidence": "high",
        "detect_fn": lambda url, params: "awin1.com" in url or "awin.com" in url or "awc=" in url
    },
    "Rakuten": {
        "confidence": "high",
        "detect_fn": lambda url, params: "linksynergy.com" in url or "rakutenmarketing.com" in url
    },
    "MaxBounty": {
        "confidence": "high",
        "detect_fn": lambda url, params: "maxbounty.com" in url or "mb103.com" in url
    },
    "Digistore24": {
        "confidence": "high",
        "detect_fn": lambda url, params: "digistore24.com" in url or "ds24" in url or "aff=" in url
    },
    "Admitad": {
        "confidence": "high",
        "detect_fn": lambda url, params: "admitad.com" in url or "alitems.com" in url
    }
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 4. TRACKER DETECTION ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TRACKER_SIGNATURES = {
    "Voluum": {
        "url_sig": ["voluum", "cid="],
        "html_sig": ["cdn.voluum.com", "voluumtrk.com/track", "window.__vl_cid"],
        "confidence": "high"
    },
    "Binom": {
        "url_sig": ["binom.org"],
        "html_sig": ["binom.org/click", "binom_click_id"],
        "confidence": "high"
    },
    "Keitaro": {
        "url_sig": ["keitaro.io", "k_click_id="],
        "html_sig": ["keitaro.io/click", "keitaroClickId"],
        "confidence": "high"
    },
    "Everflow": {
        "url_sig": ["everflow", "effp=", "ef_click_id"],
        "html_sig": ["everflow.io/scripts", "window.EF", "EverflowClient"],
        "confidence": "high"
    },
    "RedTrack": {
        "url_sig": ["rdtk.io", "redtrack.io"],
        "html_sig": ["redtrack"],
        "confidence": "high"
    },
    "Custom/In-house": {
        "url_sig": ["lptoken=", "lp_token="],
        "html_sig": [],
        "confidence": "medium"
    }
}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 5. PARAMETER EXTRACTION ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def extract_all_params(urls: list) -> dict:
    """Parses and merges params from all URLs in the chain."""
    results = {"raw_all": {}}
    
    ID_MAPS = {
        "affiliate_id": ["affid", "aff_id", "affiliate_id", "affiliate", "aid", "pub_id", "pid", "partner", "ref", "refid", "promo", "hop", "cbaffiliate", "aff", "awinaffid", "irpid"],
        "offer_id": ["offer_id", "offid", "oid", "prod", "product_id", "campaign_id", "cid", "bid", "item", "f", "cbid", "pay", "awinmid", "id", "campaignid"],
        "click_id": ["clickid", "click_id", "tid", "transaction_id", "uuid", "hopId", "ef_click_id", "effp", "k_click_id", "rtid", "rc_uuid", "tblci", "ob_click_id"]
    }
    
    SUB_ID_PARAMS = ["subid", "subid1", "subid2", "subid3", "sub1", "sub2", "sub3", "s1", "s2", "s3", "aff_sub"]
    
    for url in urls:
        if not url: continue
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        
        # Store raw for debug
        for k, v in params.items():
            results["raw_all"][k] = v[0]
            
        # Map IDs
        for target, aliases in ID_MAPS.items():
            for alias in aliases:
                if alias in params:
                    results[target] = params[alias][0]
                    
        # Sub IDs
        for s_alias in SUB_ID_PARAMS:
            if s_alias in params:
                key = f"sub_id{s_alias[-1]}" if s_alias[-1].isdigit() else "sub_id1"
                results[key] = params[s_alias][0]
                
        # Special Param: event_source_url
        if "event_source_url" in params:
            results["real_offer_domain"] = params["event_source_url"][0]
            
        # Revcontent specific
        for rc_p in ["widget_id", "boost_id", "content_id", "sitename"]:
            if rc_p in params:
                results[rc_p] = params[rc_p][0]

    return results

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 6. FINAL OFFER RESOLUTION
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def resolve_offer_url(cleaned_chain: list, raw_final_url: str, extracted_params: dict) -> dict:
    """Decides the most accurate final offer URL."""
    is_dead, reason = is_dead_end_url(raw_final_url)
    
    # 1. Not a dead end? Use it.
    if not is_dead and raw_final_url:
        return {"url": raw_final_url, "method": "direct_navigation"}
        
    # 2. Dead end? Try recovery
    # a. event_source_url param
    if extracted_params.get("real_offer_domain"):
        domain = extracted_params["real_offer_domain"]
        if not domain.startswith("http"): domain = f"https://{domain}"
        return {"url": domain, "method": "event_source_param"}
        
    # b. Last non-dead URL in chain
    for url in reversed(cleaned_chain):
        if not is_dead_end_url(url)[0]:
            return {"url": url, "method": "chain_last_valid"}
            
    # c. Unresolved
    return {"url": None, "method": "unresolved", "needs_manual_review": True}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 7. DOMAIN & VERTICAL ANALYSIS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def analyze_offer_domain(url: str) -> dict:
    """Identifies vertical and page type from the offer URL."""
    if not url: return {"domain": None, "page_type": None, "vertical": None}
    
    u_lower = url.lower()
    domain = tldextract.extract(u_lower).registered_domain
    
    VERTICAL_KEYWORDS = {
        "Health/Supplements": ["supplement", "health", "natural", "remedy", "formula", "keto", "detox", "slim", "blood", "joint", "pain", "sugar", "memory", "brain", "weight", "loss", "fat", "cholesterol", "derila", "ergo", "retinaclear"],
        "Finance": ["invest", "trading", "forex", "crypto", "insurance", "loan", "credit", "mortgage"],
        "Beauty/Skincare": ["skin", "beauty", "cream", "serum", "collagen", "hair", "anti-aging"],
        "Software/App": ["software", "app", "download", "tool", "platform", "saas"]
    }
    
    vertical = "Unknown"
    for v, keywords in VERTICAL_KEYWORDS.items():
        if any(k in u_lower for k in keywords):
            vertical = v
            break
            
    PAGE_TYPES = {
        "/vsl/": "VSL (Video Sales Letter)",
        "/video/": "Video Sales Page",
        "/landers/": "Pre-lander",
        "/lp/": "Landing Page",
        "/checkout/": "Direct Checkout",
        "/order/": "Order Page",
        "/cb/vsl/": "ClickBank VSL"
    }
    
    page_type = "Landing Page"
    for path, name in PAGE_TYPES.items():
        if path in u_lower:
            page_type = name
            break
            
    return {"domain": domain, "page_type": page_type, "vertical": vertical}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN ORCHESTRATOR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def extract_offer_intelligence(landing_url: str, raw_final_url: str, all_captured_urls: list, page_html: str = "") -> dict:
    """Full extraction logic from all available signals."""
    
    # Step 0: Clean and rank
    full_chain = all_captured_urls + [raw_final_url]
    cleaned = clean_and_rank_chain(full_chain, landing_url)
    
    # Step 1: Pre-detect dead ends
    final_is_dead, dead_end_reason = is_dead_end_url(raw_final_url)
    
    # Step 2: Extract params
    all_params = extract_all_params(cleaned + [landing_url])
    
    # Step 3: Network Detection
    network_name = "Unknown"
    net_confidence = "none"
    # Analyze EVERYTHING for network signals
    for url in (cleaned + [raw_final_url, landing_url]):
        parsed_url = urlparse(url)
        url_params = parse_qs(parsed_url.query)
        for name, sig in NETWORK_SIGNATURES.items():
            if sig["detect_fn"](url, url_params):
                network_name = name
                net_confidence = sig["confidence"]
                break
        if network_name != "Unknown": break
        
    # Step 4: Tracker Detection
    tracker_name = "Unknown"
    trk_confidence = "none"
    # Analyze EVERYTHING for tracker signals
    for url in (cleaned + [raw_final_url, landing_url]):
        for name, sig in TRACKER_SIGNATURES.items():
            if any(s in url.lower() for s in sig["url_sig"]):
                tracker_name = name
                trk_confidence = sig["confidence"]
                break
        if tracker_name != "Unknown": break
        
    # From HTML Fallback
    if tracker_name == "Unknown" and page_html:
        for name, sig in TRACKER_SIGNATURES.items():
            if any(s in page_html for s in sig["html_sig"]):
                tracker_name = name
                trk_confidence = "medium"
                break
                
    # Fallback: If we have IDs but no network, it's Direct/In-house
    if network_name == "Unknown":
        if all_params.get("affiliate_id") or all_params.get("offer_id"):
            network_name = "Direct/In-house"
            net_confidence = "low"
            
    # Step 5: Resolve final offer URL
    offer_url_result = resolve_offer_url(cleaned, raw_final_url, all_params)
    
    # Step 6: Domain Analysis
    domain_intel = analyze_offer_domain(offer_url_result["url"])
    
    # Step 7: Final Result Construction
    return {
        "affiliate_network": network_name,
        "network_confidence": net_confidence,
        "tracker_tool": tracker_name,
        "tracker_confidence": trk_confidence,
        
        "final_offer_url": offer_url_result["url"],
        "offer_url_method": offer_url_result["method"],
        "offer_domain": domain_intel["domain"],
        "offer_vertical": domain_intel["vertical"],
        "page_type": domain_intel["page_type"],
        
        "affiliate_id": all_params.get("affiliate_id"),
        "offer_id": all_params.get("offer_id"),
        "click_id": all_params.get("click_id"),
        "sub_id1": all_params.get("sub_id1"),
        "sub_id2": all_params.get("sub_id2"),
        
        "traffic_source": "Revcontent" if all_params.get("rc_uuid") else ("Taboola" if all_params.get("tblci") else "Unknown"),
        "widget_id": all_params.get("widget_id"),
        "publisher_site": all_params.get("sitename"),
        
        "needs_manual_review": offer_url_result.get("needs_manual_review", False),
        "dead_end_detected": final_is_dead,
        "dead_end_reason": dead_end_reason,
        "urls_analyzed": len(cleaned)
    }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# 8. VALIDATION TESTS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

if __name__ == "__main__":
    print("Running Validation Tests...")

    # Case 1: vturb dead-end
    res1 = extract_offer_intelligence(
        landing_url="https://en.healthheadlines.info/v209659-en-V3-Memory-Loss/?lptoken=17fa761455d13979058f&widget_id=289322&sitename=joehoft.com",
        raw_final_url="https://api.vturb.com.br/vturb/check",
        all_captured_urls=[]
    )
    print("\nCase 1 (vturb):")
    print(f"  Network: {res1['affiliate_network']} | Tracker: {res1['tracker_tool']}")
    print(f"  Final URL: {res1['final_offer_url']} | Method: {res1['offer_url_method']}")

    # Case 2: ClickBank via /cb/ path
    res2 = extract_offer_intelligence(
        landing_url="https://calmgrowthcenter.com/crstrenght/cb/vsl/v3/?hopId=3f93f391&affiliate=supaffcb&extclid=da81u",
        raw_final_url="https://calmgrowthcenter.com/crstrenght/cb/vsl/v3/?hopId=3f93f391&affiliate=supaffcb",
        all_captured_urls=[]
    )
    print("\nCase 2 (ClickBank):")
    print(f"  Network: {res2['affiliate_network']} | AffID: {res2['affiliate_id']}")

    # Case 3: Everflow postback
    res3 = extract_offer_intelligence(
        landing_url="https://smarterlivingdaily.org/lps/F1h7P22F4/",
        raw_final_url="https://www.djpcraze.com/sdk/conversion?effp=37fb5d3f&oid=7971&affid=5351&event_source_url=get-derila-ergo.com",
        all_captured_urls=[]
    )
    print("\nCase 3 (Everflow):")
    print(f"  Network: {res3['affiliate_network']} | Final URL: {res3['final_offer_url']}")

    # Case 4: getretinaclear.com with aff_id
    res4 = extract_offer_intelligence(
        landing_url="https://wellnesspeek.com/lifehacks_001/?widget_id=289325&rc_uuid=76a9ef5c",
        raw_final_url="https://getretinaclear.com/video/?aff_id=57967&subid=clf2947e55d",
        all_captured_urls=[]
    )
    print("\nCase 4 (RetinaClear):")
    print(f"  Network: {res4['affiliate_network']} | Page Type: {res4['page_type']}")
