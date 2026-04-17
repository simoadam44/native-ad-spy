import tldextract

def detect_cloaking(original_url: str, final_url: str, redirect_chain: list = None) -> dict:
    """
    Detects cloaking by comparing the original domain vs the final landing domain.
    Analyzes domain types (News vs Sales) and redirect chain length.
    """
    try:
        # Prevent DNS resolution errors by not fetching live updates
        extractor = tldextract.TLDExtract(fetch=False)
        orig_ext = extractor(original_url)
        final_ext = extractor(final_url)
        
        original_domain = orig_ext.registered_domain
        final_domain = final_ext.registered_domain
        
        domain_changed = original_domain != final_domain
        cloaking_detected = False
        cloaking_type = "none"
        force_affiliate = False
        
        if domain_changed:
            cloaking_detected = True
            
            # --- Type A: News to Sales (Strong Signal) ---
            news_keywords = [
                "news", "daily", "times", "post", "report", "health", "wellness",
                "wire", "today", "journal", "tribune", "herald", "blog", "info", "tips"
            ]
            sales_keywords = [
                "supplement", "formula", "official", "shop", "store", "order",
                "get", "try", "buy", "checkout"
            ]
            
            is_news = any(k in original_domain for k in news_keywords)
            is_sales = any(k in final_domain for k in sales_keywords) or final_url.endswith(".shop")
            
            if is_news and is_sales:
                cloaking_type = "news_to_sales"
                force_affiliate = True
            
            # --- Type B: Tracker to Offer ---
            tracker_keywords = ["voluum", "binom", "rdtk", "click", "track", "redir"]
            if any(k in original_domain for k in tracker_keywords):
                cloaking_type = "tracker_to_offer"
                force_affiliate = True
            else:
                cloaking_type = "domain_change"
        
        # --- Check Redirect Chain ---
        redirect_count = len(redirect_chain) if redirect_chain else 0
        suspicious_redirect = False
        if redirect_count > 3:
            suspicious_redirect = True
            
        return {
            "cloaking_detected": cloaking_detected,
            "cloaking_type": cloaking_type,
            "original_domain": original_domain,
            "final_domain": final_domain,
            "domain_changed": domain_changed,
            "force_affiliate": force_affiliate,
            "redirect_count": redirect_count,
            "suspicious_redirect": suspicious_redirect
        }
    except Exception as e:
        return {"error": str(e), "cloaking_detected": False}

if __name__ == "__main__":
    # Tests
    print(detect_cloaking("https://wellnesswire.com/story", "https://naturalformula.shop/order"))
    print(detect_cloaking("https://track.com/123", "https://final.com/abc", ["r1", "r2", "r3", "r4"]))
