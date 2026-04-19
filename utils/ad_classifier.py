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
    aff_params = ["affid", "affiliate_id", "offid", "offer_id", "subid", "aff_sub", "clickid", "transaction_id"]
    if any(p in final_url for p in aff_params):
        score += 3
        signals.append("final_url_has_aff_params (+3)")
        
    aff_paths = ["/landers/", "/landing/", "/offer/", "/checkout/", "/order/", "/sales/", "/presell/", "/prelander/", "/p_prel/", "/bridge/", "/go/"]
    if any(p in final_url for p in aff_paths):
        score += 3
        signals.append("final_url_has_aff_path (+3)")
        
    # UUID in path (e.g. /f8ab584f-...)
    if re.search(r"/[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}", final_url):
        score += 3
        signals.append("final_url_has_uuid_path (+3)")
        
    # Domain changed to health/supplement words
    health_keywords = ["supplement", "formula", "relief", "remedy", "natural", "health", "cure", "detox", "keto", "slim"]
    if final_domain != orig_domain and any(k in final_domain for k in health_keywords):
        score += 3
        signals.append("domain_change_to_health (+3)")

    # --- 2. Medium Affiliate Signals (+2) ---
    tracker_domains = ["revcontent.com/cv/", "taboola.com/cr/", "mgid.com/ghits", "voluum.com", "bemob.com", "rdtk.io"]
    if any(t in url for t in tracker_domains):
        score += 2
        signals.append("original_url_is_tracker (+2)")
        
    if any(k in content_lower for k in ["buy now", "order now"]):
        score += 2
        signals.append("content_has_buy_intent (+2)")
        
    if re.search(r"\$\d+(\.\d{2})?", content_lower):
        score += 2
        signals.append("content_has_price_pattern (+2)")
        
    if any(t in final_domain for t in [".icu", ".biz", ".pro"]) and final_domain not in ARBITRAGE_DOMAINS:
        score += 2
        signals.append("affiliate_tld_detected (+2)")

    # --- 3. Light Affiliate Signals (+1) ---
    if any(p in url for p in aff_params):
        score += 1
        signals.append("orig_url_has_aff_params (+1)")
        
    if any(k in title for k in health_keywords):
        score += 1
        signals.append("title_has_health_keywords (+1)")

    # --- 4. Counter Signals (Arbitrage) ---
    if any(d in final_domain for d in ARBITRAGE_DOMAINS):
        score -= 3
        signals.append("final_domain_in_arbitrage_whitelist (-3)")
        
    arb_paths = ["/trending/", "/article/", "/list/", "/news/", "/blog/", "/story/", "/post/"]
    if any(p in final_url for p in arb_paths) and any(d in final_domain for d in ARBITRAGE_DOMAINS):
        score -= 3
        signals.append("arbitrage_path_on_content_site (-3)")
        
    if "utm_source=" in final_url and "utm_medium=" in final_url:
        score -= 2
        signals.append("utm_tracking_detected (-2)")
        
    if any(k in content_lower for k in ["sponsored content", "advertisement", "you may also like"]):
        score -= 2
        signals.append("arbitrage_content_keywords (-2)")

    # --- 5. Final Decision ---
    ad_type = "Unknown"
    confidence = "low"
    
    if score >= 3:
        ad_type = "Affiliate"
        confidence = "high"
    elif score >= 1:
        ad_type = "Affiliate"
        confidence = "medium"
    elif score <= -3:
        ad_type = "Arbitrage"
        confidence = "high"
    elif score <= -1:
        ad_type = "Arbitrage"
        confidence = "medium"
    else:
        # Fallback to local content scan if score is 0
        ad_type = local_content_classify(page_content, final_url)
        confidence = "medium" if ad_type != "Unknown" else "low"

    return {
        "ad_type": ad_type,
        "score": score,
        "confidence": confidence,
        "signals": signals
    }

def local_content_classify(page_content: str, final_url: str) -> str:
    """
    Local keyword-based classifier as a fallback for 0-score cases.
    """
    if not page_content:
        return "Unknown"
        
    content_lower = page_content.lower()
    
    affiliate_keywords = [
        "order now", "buy now", "add to cart",
        "limited time offer", "money back guarantee",
        "60-day guarantee", "satisfaction guaranteed",
        "click here to order", "secure checkout",
        "free shipping", "exclusive offer",
        "as seen on", "doctor approved",
        "clinical study", "proven formula"
    ]
    
    arbitrage_keywords = [
        "sponsored content", "advertisement",
        "you may also like", "recommended for you",
        "read more", "continue reading",
        "comments", "share this article",
        "related articles", "trending now"
    ]
    
    aff_score = sum(1 for kw in affiliate_keywords if kw in content_lower)
    arb_score = sum(1 for kw in arbitrage_keywords if kw in content_lower)
    
    if aff_score > arb_score and aff_score >= 2:
        return "Affiliate"
    elif arb_score > aff_score and arb_score >= 2:
        return "Arbitrage"
    else:
        return "Unknown"

def is_arbitrage_site(url: str, page_content: str) -> dict:
    """
    STRONG ARBITRAGE SIGNALS (returns Arbitrage immediately if 2+ match).
    """
    score = 0
    signals = []
    
    url_lower = url.lower()
    content_lower = (page_content or "").lower()
    
    # A) URL path patterns
    arb_path_rules = {
        "/trending/": 3, "/article/": 2, "/list/": 2, "/gallery/": 2,
        "/celebrities/": 2, "you-wont-believe": 3, "/page/2": 2
    }
    for path, points in arb_path_rules.items():
        if path in url_lower:
            score += points
            signals.append(f"arb_path_{path.strip('/')} (+{points})")
            
    # Pagination via regex (e.g. /2 or /3 at end)
    if re.search(r'/\d+/?$', url_lower):
        score += 2
        signals.append("url_ends_in_pagination (+2)")

    # B) Domain name patterns
    arb_domain_keywords = ["news", "daily", "times", "update", "report", "health", "care", "wellness", "rehab", "tips", "trending", "viral", "buzz", "today", "instant"]
    domain = urlparse(url_lower).netloc
    found_domain_kws = 0
    for kw in arb_domain_keywords:
        if kw in domain:
            score += 2
            found_domain_kws += 1
            if found_domain_kws <= 2: # Max +4 from domain keywords
                signals.append(f"domain_has_{kw} (+2)")
            if found_domain_kws >= 2: break

    # C) Page content signals
    if "disqus" in content_lower or "fb-comment" in content_lower:
        score += 3
        signals.append("has_comment_section (+3)")
    if any(k in content_lower for k in ["you might also like", "you may also like", "recommended for you"]):
        score += 2
        signals.append("has_recirculation_widget (+2)")
    if any(k in content_lower for k in ["taboola", "outbrain", "revcontent"]):
        score += 3
        signals.append("has_native_ad_widgets (+3)")
    if "share this article" in content_lower:
        score += 1
        signals.append("has_social_share (+1)")
        
    ad_type = "Unknown"
    if score >= 6:
        ad_type = "Arbitrage"
    elif score >= 3:
        ad_type = "Arbitrage" # Medium confidence

    return {
        "is_arbitrage": ad_type == "Arbitrage",
        "score": score,
        "signals": signals,
        "ad_type": ad_type
    }

# Compatibility wrapper for old calls
def classify_ad(url: str, title: str) -> dict:
    res = calculate_ad_score(url, title)
    return {
        "ad_type": res["ad_type"],
        "confidence": res["confidence"],
        "signals": res["signals"],
        "score": res["score"]
    }

if __name__ == "__main__":
    # Test cases
    test_cases = [
        ("https://product.com", "Buy Keto Now", "https://melodyeu.com/landers/p_prel/123", "Price $49.99 Buy Now"),
        ("https://revcontent.com/cv/123", "10 Celebs Who...", "https://independent.co.uk/news/123", "Trending Now related articles"),
    ]
    for u, t, fu, c in test_cases:
        print(f"URL: {u} | Final: {fu}\nResult: {calculate_ad_score(u, t, fu, c)}\n")
