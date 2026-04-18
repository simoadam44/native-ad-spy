from urllib.parse import urlparse, parse_qs

def extract_affiliate_params(url: str) -> dict:
    """
    Parses a URL to extract common affiliate tracking parameters 
    and identify the tracking network.
    """
    if not url:
        return {}

    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    
    result = {
        "affiliate_id": None,
        "offer_id": None,
        "sub_id1": None,
        "click_id": None,
        "detected_network": "Direct / Unknown"
    }

    # --- 1. Map Common Parameters ---
    # Affiliate ID
    result["affiliate_id"] = (
        params.get("hop", [None])[0] or 
        params.get("affid", [None])[0] or 
        params.get("affiliate_id", [None])[0] or 
        params.get("uid", [None])[0] or
        params.get("shaff", [None])[0] or
        params.get("pid", [None])[0] or 
        params.get("pubid", [None])[0] or
        params.get("source", [None])[0]
    )

    # Offer ID
    result["offer_id"] = (
        params.get("offid", [None])[0] or 
        params.get("offer_id", [None])[0] or 
        params.get("oid", [None])[0] or
        params.get("page", [None])[0] or
        params.get("lptoken", [None])[0]
    )

    # Sub ID
    result["sub_id1"] = (
        params.get("aff_sub", [None])[0] or 
        params.get("subid", [None])[0] or 
        params.get("s1", [None])[0]
    )

    # Click ID
    result["click_id"] = (
        params.get("clickid", [None])[0] or 
        params.get("transaction_id", [None])[0] or 
        params.get("click_id", [None])[0] or
        params.get("rc_uuid", [None])[0]
    )

    # --- 2. Detect Network based on URL or Params ---
    domain = parsed.netloc.lower()
    
    if "clickbank" in domain or "hop" in params or "hopId" in params or "v" in params and "bvsl" in params["v"]:
        result["detected_network"] = "ClickBank"
    elif "everflow" in domain or "vndr" in params and "evf" in params["vndr"] or "ef_id" in params:
        result["detected_network"] = "Everflow"
    elif "buygoods" in domain or "bg_id" in params or "screen_id" in params or "account_id" in params:
        result["detected_network"] = "BuyGoods"
    elif "shaff" in params or "derila" in url.lower():
        result["detected_network"] = "GiddyUp"
    elif domain.startswith("offer.") and ("lptoken" in params or "offer_id" in params):
        result["detected_network"] = "Fanyil / Native Ecom"
    elif "rc_uuid" in params:
        result["detected_network"] = "Revcontent Tracker"
    elif "cake" in url or "aff_id" in params:
        result["detected_network"] = "Cake"
    elif "hasoffers" in url or "aff_c" in url or "go2cloud.org" in domain:
        result["detected_network"] = "HasOffers (TUNE)"
    elif "voluum" in domain:
        result["detected_network"] = "Voluum"
    elif "binom" in domain or "clickid" in params:
        # Simplistic binom heuristic backup
        if result["detected_network"] == "Direct / Unknown":
            result["detected_network"] = "Binom (Probable)"
    elif "maxbounty" in domain or "mb103" in domain:
        result["detected_network"] = "MaxBounty"
    elif "advidi" in domain:
        result["detected_network"] = "Advidi"
    elif "ldbt.io" in domain or "leadbit" in domain:
        result["detected_network"] = "LeadBit"

    return result

if __name__ == "__main__":
    # Tests
    test_urls = [
        "https://track.com/aff_c?aff_id=123&offer_id=456&aff_sub=789",
        "https://go2cloud.org/aff_c?offer_id=99&aff_id=10",
        "https://maxbounty.com/landing?affid=555&oid=11"
    ]
    for u in test_urls:
        print(f"URL: {u}\nExtracted: {extract_affiliate_params(u)}\n")
