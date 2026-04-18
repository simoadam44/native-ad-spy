import re
from urllib.parse import urlparse

def classify_ad(url: str, title: str) -> dict:
    """
    Classifies an ad as 'Affiliate', 'Arbitrage', or 'Unknown' 
    using pattern matching on URL and Title signals.
    """
    url = url.lower()
    title = title.lower()
    signals = []
    
    # --- A) URL-based Affiliate Signals ---
    affiliate_params = [
        "affid", "affiliate_id", "offid", "offer_id", "clickid",
        "aff_sub", "subid", "s1=", "s2=", "s3=", "cid=", "pid=", "click_id"
    ]
    if any(param in url for param in affiliate_params):
        signals.append("affiliate_params_in_url")
        
    affiliate_domains = [
        "hop.clickbank.net", "trk.", "clk.", "go.", "redir.", "track.",
        "voluum.com", "binom.org", "rdtk.io", "bemob.com", "keitaro.io", 
        "thrivetracker.com", "redtrack.io"
    ]
    if any(domain in url for domain in affiliate_domains):
        signals.append("affiliate_domain_pattern")

    # --- B) URL-based Arbitrage Signals ---
    # 1. Pagination Patterns (Mechanical Check)
    pagination_pattern = r"(/(\d+)/?$|page/\d+|next-page|/p\d+/?$)"
    if re.search(pagination_pattern, url):
        signals.append("arbitrage_pagination_detected")

    # 2. Domain-level Keywords
    arbitrage_keywords = ["trending", "lifestyle", "news", "best-offer", "story", "viral", "article"]
    domain = urlparse(url).netloc.lower()
    if any(keyword in domain for keyword in arbitrage_keywords):
        signals.append("arbitrage_domain_keyword_detected")

    # 3. Parameter Patterns
    arbitrage_params = ["utm_medium=native", "page=2", "p=2", "article", "story"]
    if any(param in url for param in arbitrage_params):
        signals.append("arbitrage_params_in_url")
        
    # --- C) Title Affiliate Patterns (Regex) ---
    aff_title_patterns = [
        r"\d+%\s*off", r"buy now", r"order now", r"get .+ for \$",
        r"limited offer", r"only \d+ left", r"claim your",
        r"lose \d+ lbs?", r"skin tag", r"blood sugar", r"keto"
    ]
    for pattern in aff_title_patterns:
        if re.search(pattern, title):
            signals.append(f"aff_title_pattern: {pattern}")
            
    # --- D) Title Arbitrage Patterns ---
    arb_title_patterns = [
        r"\d+ things", r"doctors hate", r"before you",
        r"the truth about", r"why .+ is", r"you won't believe"
    ]
    for pattern in arb_title_patterns:
        if re.search(pattern, title):
            signals.append(f"arb_title_pattern: {pattern}")

    # --- Classification Logic ---
    aff_signals = [s for s in signals if "aff" in s]
    arb_signals = [s for s in signals if "arb" in s]
    
    ad_type = "Unknown"
    confidence = "low"
    method = "none"
    
    if aff_signals and not arb_signals:
        ad_type = "Affiliate"
        confidence = "high" if len(aff_signals) > 1 else "medium"
        method = "both" if any("url" in s for s in aff_signals) and any("title" in s for s in aff_signals) else "url" if any("url" in s for s in aff_signals) else "title"
    elif arb_signals and not aff_signals:
        ad_type = "Arbitrage"
        confidence = "high" if len(arb_signals) > 1 else "medium"
        method = "both" if any("url" in s for s in arb_signals) and any("title" in s for s in arb_signals) else "url" if any("url" in s for s in arb_signals) else "title"
    elif aff_signals and arb_signals:
        # Mixed signals - usually an affiliate using arbitrage-style headlines
        ad_type = "Affiliate"
        confidence = "medium"
        method = "both"
        
    return {
        "ad_type": ad_type,
        "confidence": confidence,
        "signals": signals,
        "method": method
    }

if __name__ == "__main__":
    # Tests
    test_cases = [
        ("https://hop.clickbank.net/123", "Order Keto Gummies Now"),
        ("https://news.com/article?utm_medium=native", "10 Things Doctors Hate"),
        ("https://product.com/get?affid=99", "Buy This Product Today")
    ]
    for u, t in test_cases:
        print(f"URL: {u} | Title: {t}\nResult: {classify_ad(u, t)}\n")
