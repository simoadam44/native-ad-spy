import re
from urllib.parse import urlparse

# --- Whitelists ---
ARBITRAGE_DOMAINS = [
    "independent.co.uk", "dailymail.co.uk", "mirror.co.uk",
    "thesun.co.uk", "buzzfeed.com", "huffpost.com",
    "msn.com", "yahoo.com", "cnn.com", "foxnews.com",
    "breitbart.com", "thegatewaypundit.com",
    "ancestry.com", "goodrx.com", "rocketmortgage.com",
    "smartasset.com", "aarp.org", "verizon.com",
    "libertymutual.com", "ring.com", "wisebread.com",
    "herbeauty.co", "buzzday.info", "newsphere.jp",
    "health7x24.com", "travelcaribou.com",
    "gameswaka.com", "buzzfond.com", "ezzin.com",
]

def calculate_ad_score(url: str, title: str, final_url: str = None, page_content: str = "") -> dict:
    """
    Calculates a neutral score for ad classification.
    Positive = Affiliate Signal
    Negative = Arbitrage Signal
    """
    score = 0
    signals = []
    
    url = (url or "").lower()
    title = (title or "").lower()
    final_url = (final_url or url).lower()
    content_lower = (page_content or "").lower()
    
    final_domain = urlparse(final_url).netloc.lower()
    orig_domain = urlparse(url).netloc.lower()

    # --- 1. Strong Affiliate Signals (+3) ---
    aff_params = ["affid", "aff_id", "affiliate_id", "offid", "offer_id", "subid", "aff_sub", "clickid", "transaction_id", "lptoken"]
    if any(p in final_url for p in aff_params):
        score += 3
        signals.append("final_url_has_aff_params (+3)")
        
    aff_paths = ["/landers/", "/landing/", "/offer/", "/checkout/", "/order/", "/sales/", "/presell/", "/prelander/", "/p_prel/", "/bridge/", "/go/"]
    if any(p in final_url for p in aff_paths):
        score += 3
        signals.append("final_url_has_aff_path (+3)")
        
    health_keywords = ["supplement", "formula", "relief", "remedy", "natural", "health", "cure", "detox", "keto", "slim"]
    if final_domain != orig_domain and any(k in final_domain for k in health_keywords):
        score += 3
        signals.append("domain_change_to_health (+3)")

    # --- 2. Medium Affiliate Signals (+2) ---
    tracker_domains = ["revcontent.com/cv/", "taboola.com/cr/", "mgid.com/ghits", "voluum.com", "bemob.com", "rdtk.io", "trkerupper.com"]
    if any(t in url for t in tracker_domains) or any(t in final_url for t in tracker_domains):
        score += 2
        signals.append("url_is_known_tracker (+2)")
        
    if any(k in content_lower for k in ["buy now", "order now", "add to cart"]):
        score += 2
        signals.append("content_has_buy_intent (+2)")
        
    # --- 3. Arbitrage Signals (Negative) ---
    if any(d in final_domain for d in ARBITRAGE_DOMAINS):
        score -= 2
        signals.append("final_domain_in_arbitrage_whitelist (-2)")
        
    # --- 4. Final Decision ---
    ad_type = "Unknown"
    confidence = "low"
    
    if score >= 3:
        ad_type = "Affiliate"
        confidence = "high"
    elif score >= 1:
        ad_type = "Affiliate"
        confidence = "medium"
    elif score <= -3:
        # Note: Even if score is negative, deep_analyzer enforces STRICT rule.
        ad_type = "Arbitrage"
        confidence = "medium"
    else:
        ad_type = local_content_classify(page_content, final_url)
        confidence = "medium" if ad_type != "Unknown" else "low"

    return {
        "ad_type": ad_type,
        "score": score,
        "confidence": confidence,
        "signals": signals
    }

def local_content_classify(page_content: str, final_url: str) -> str:
    if not page_content:
        return "Unknown"
    content_lower = page_content.lower()
    affiliate_keywords = ["order now", "buy now", "add to cart", "exclusive offer", "as seen on"]
    arbitrage_keywords = ["sponsored content", "advertisement", "you may also like", "trending now"]
    aff_score = sum(1 for kw in affiliate_keywords if kw in content_lower)
    arb_score = sum(1 for kw in arbitrage_keywords if kw in content_lower)
    if aff_score > arb_score and aff_score >= 1: return "Affiliate"
    elif arb_score > aff_score and arb_score >= 2: return "Arbitrage"
    else: return "Unknown"

def get_ad_network_fingerprints(page_content: str) -> dict:
    """
    STRICT CHECK for Publisher IDs and Ad Containers.
    Includes DOM container patterns for AdSense, Taboola, MGID, Outbrain, Revcontent.
    """
    content = page_content.lower()
    FINGERPRINTS = {
        "Google AdSense": {
            "patterns": [
                "adsbygoogle", "googlesyndication.com/pagead", "google_ad_client",
                "pub-", "ins class=\"adsbygoogle\""
            ], 
            "confidence": "high"
        },
        "Taboola": {
            "patterns": [
                "cdn.taboola.com/libtrc", "_taboola.push", "trc.taboola.com",
                "taboola-below-article", "taboola-right-rail", "data-taboola-placeholder"
            ], 
            "confidence": "high"
        },
        "Outbrain": {
            "patterns": [
                "widgets.outbrain.com", "ob-widget", "data-ob-mark=",
                "outbrain-widget", "OUTBRAIN"
            ], 
            "confidence": "high"
        },
        "MGID": {
            "patterns": [
                "servicer.mgid.com", "mgid.com/widgets", "jsc.mgid.com",
                "mgid-widget", "data-mgid-id"
            ], 
            "confidence": "high"
        },
        "Revcontent": {
            "patterns": [
                "trends.revcontent.com", "revcontent.com/gp/", "rc_widget",
                "rev-content", "data-revcontent"
            ], 
            "confidence": "high"
        },
    }
    found_networks = []
    for name, config in FINGERPRINTS.items():
        matches = [p for p in config["patterns"] if p in content]
        if matches: found_networks.append({"network": name, "confidence": config["confidence"], "matches": matches[:3], "count": len(matches)})
    
    if not found_networks: return {"found": False, "network": None, "confidence": None, "all_networks": []}
    
    found_networks.sort(key=lambda x: (0 if x["confidence"] == "high" else 1, -x["count"]))
    primary = found_networks[0]
    return {"found": True, "network": primary["network"], "confidence": primary["confidence"], "matched_patterns": primary["matches"], "all_networks": [n["network"] for n in found_networks]}

def is_arbitrage_site(url: str, page_content: str, has_network_fingerprint: bool = False) -> dict:
    """
    STRICT ARBITRAGE MASTER RULE.
    """
    if not has_network_fingerprint:
        return {"is_arbitrage": False, "score": 0, "confidence": "high", "signals": ["NO_AD_NETWORK_DETECTED(STRICT_RULE)"]}

    score = 0
    signals_found = []
    url_lower = url.lower()
    content_lower = (page_content or "").lower()
    
    arb_rules = {"/trending/": 3, "/article/": 2, "/list/": 2, "/gallery/": 2, "/celebrities/": 3}
    for p, pts in arb_rules.items():
        if p in url_lower: score += pts; signals_found.append(f"url:{p}(+{pts})")
        
    content_signals = {"you might also like": 2, "related articles": 2, "recommended for you": 2, "next page": 3}
    for p, pts in content_signals.items():
        if p in content_lower: score += pts; signals_found.append(f"content:{p}(+{pts})")
        
    return {"is_arbitrage": True, "score": score, "confidence": "high", "signals": signals_found}

def classify_ad(url: str, title: str) -> dict:
    res = calculate_ad_score(url, title)
    return {"ad_type": res["ad_type"], "confidence": res["confidence"], "signals": res["signals"], "score": res["score"]}
