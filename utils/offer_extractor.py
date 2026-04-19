import json
import re
import tldextract
from urllib.parse import urlparse, parse_qs

TRACKER_SIGNATURES = {
    "Voluum": {
        "domains": ["voluum.com", "voluumtrk.com", "trkvol.com"],
        "params": ["cid", "voluum"],
        "url_patterns": ["voluum"],
        "priority": "high"
    },
    "Binom": {
        "domains": ["binom.org", "binomtracker.com"],
        "params": ["clickid", "click_id", "binom"],
        "url_patterns": ["binom"],
        "priority": "high"
    },
    "Keitaro": {
        "domains": ["keitaro.io", "ktr.ovh"],
        "params": ["k_click_id", "subid", "keitaro"],
        "url_patterns": ["keitaro", "ktr."],
        "priority": "high"
    },
    "Custom/In-house Tracker": {
        "domains": [],
        "params": ["lptoken", "lp_token", "lpt", "tracking_id", "trk_id", "trkid", "pixel_id", "px_id"],
        "url_patterns": ["lptoken="],
        "priority": "low"
    },
    "Revcontent Tracker": {
        "domains": ["revcontent.com", "smeagol.revcontent.com"],
        "params": ["rc_uuid", "boost_id", "content_id", "widget_id"],
        "url_patterns": ["rc_uuid=", "revcontent", "smeagol.rev"],
        "priority": "high"
    },
    "Taboola Tracker": {
        "domains": ["taboola.com", "trc.taboola.com"],
        "params": ["trc_click_id", "tblci"],
        "url_patterns": ["tblci=", "taboola"],
        "priority": "high"
    },
    "Outbrain Tracker": {
        "domains": ["outbrain.com", "zemanta.com"],
        "params": ["ob_click_id", "outbrainclickid"],
        "url_patterns": ["ob_click_id="],
        "priority": "high"
    },
    "Digistore24": {
        "domains": ["digistore24.com"],
        "params": ["pay", "cid"],
        "url_patterns": ["digistore24", "aff=", "ds24"],
        "priority": "high"
    },
    "ClickBank": {
        "domains": ["hop.clickbank.net", "clickbank.com", "pay.clickbank.net"],
        "params": ["hop", "hopId", "cbid", "cbu", "tid", "vtid"],
        "url_patterns": ["hop=", "hopId=", "clickbank", "cbid=", "hop.clickbank"],
        "priority": "high"
    }
}

NETWORK_SIGNATURES = {
    "ClickBank": {
        "domains": ["hop.clickbank.net", "clickbank.com", "pay.clickbank.net"],
        "url_patterns": ["hop=", "hopId=", "clickbank", "cbid="],
        "affiliate_id_params": ["hop"],
        "offer_id_params": ["item", "cbid", "v"],
        "click_id_params": ["hopId", "tid", "vtid"]
    },
    "Digistore24": {
        "domains": ["digistore24.com"],
        "url_patterns": ["digistore24", "ds24"],
        "affiliate_id_params": ["aff"],
        "offer_id_params": ["pay", "cid"]
    },
    "MaxBounty": {"domains": ["maxbounty.com", "mb103.com"], "url_patterns": ["maxbounty"]},
    "Warrior Plus": {
        "domains": ["warriorplus.com", "jvzoo.com"],
        "url_patterns": ["warriorplus", "jvzoo"],
        "affiliate_id_params": ["affiliate"],
        "offer_id_params": ["offer_id", "oid"]
    },
    "Direct/In-house": {
        "domains": [],
        "url_patterns": [],
        "affiliate_id_params": ["affid", "aff"],
        "offer_id_params": ["prod", "product", "item"],
        "is_fallback": True
    }
}

TRAFFIC_SOURCE_SIGNALS = {
    "Revcontent": ["rc_uuid", "boost_id", "widget_id", "revcontent"],
    "Taboola":    ["tblci", "taboola", "utm_source=taboola"],
    "MGID":       ["mgid", "utm_source=mgid"],
    "Outbrain":   ["ob_click_id", "outbrain"],
    "Facebook":   ["fbclid", "utm_source=facebook"],
    "Google":     ["gclid", "utm_source=google"],
}

VERTICALS = {
    "Health/Supplements": ["supplement", "health", "wellness", "remedy", "formula", "keto", "detox", "slim", "diabetes", "blood", "joint", "pain", "sugar"],
    "Finance/Insurance": ["insurance", "loan", "credit", "mortgage", "invest", "trading", "forex", "crypto", "finance"],
    "Beauty/Skincare": ["skin", "beauty", "cream", "serum", "anti-aging", "wrinkle", "collagen", "hair"],
    "Weight Loss": ["weight", "loss", "fat", "burn", "slim", "diet", "calorie", "belly"],
    "Adult/Dating": ["dating", "match", "love", "meet", "singles"],
    "Software/SaaS": ["software", "app", "tool", "platform", "download"],
    "E-commerce": ["shop", "store", "buy", "order", "product", "cart"]
}

def extract_traffic_source(url: str) -> dict:
    """Identifies the native/social source from URL parameters."""
    parsed = urlparse(url)
    params = parse_qs(parsed.query)
    
    for source, signals in TRAFFIC_SOURCE_SIGNALS.items():
        if any(s in url.lower() for s in signals):
            return {
                "traffic_source": source,
                "widget_id": params.get("widget_id", [None])[0] or params.get("utm_source", [None])[0],
                "publisher_site": params.get("sn", [None])[0],
                "content_id": params.get("content_id", [None])[0] or params.get("utm_content", [None])[0]
            }
    return {}

def extract_from_path(url: str) -> dict:
    """Extracts intelligence from URL path and subdomains."""
    results = {}
    parsed = urlparse(url)
    netloc = parsed.netloc.lower()
    path = parsed.path.lower()
    
    # 1. ClickBank Subdomain Pattern: {affiliate}.{product}.hop.clickbank.net
    if "hop.clickbank.net" in netloc:
        parts = netloc.split(".")
        if len(parts) >= 4:
            results["affiliate_id"] = parts[0]
            results["offer_domain_hint"] = parts[1]
    
    # 2. Numeric IDs in path
    id_patterns = [
        (r'/(offer|product|item|deal|promo)/(\d+)/', "offer_id"),
        (r'/(id|vsl)/(\d+)/', "offer_id")
    ]
    for pattern, key in id_patterns:
        match = re.search(pattern, path)
        if match:
            results[key] = match.group(2)
            
    # 3. Path-based geo/variant targets
    if "/int_" in path:
        results["path_segments"] = path.strip("/").split("/")
        
    return results

def extract_offer_intelligence(final_url: str, redirect_chain: list, landing_url: str = None) -> dict:
    all_urls = []
    for item in redirect_chain:
        if isinstance(item, dict):
            all_urls.append(item.get("url") or item.get("from") or "")
        else:
            all_urls.append(str(item))
    all_urls.append(final_url)
    
    # Init storage
    extracted = {
        "final_offer_url": final_url,
        "affiliate_network": "No Network Detected",
        "tracker_tool": "No Tracker Detected",
        "traffic_source": "Direct/Unknown",
        "offer_id": None,
        "affiliate_id": None,
        "tracker_id": None,
        "click_id": None,
        "sub_id1": None,
        "all_params": {},
        "network_confidence": "low",
        "tracker_confidence": "low",
        "needs_review": False
    }
    
    # 1. Traffic Source (from landing URL)
    if landing_url:
        source_info = extract_traffic_source(landing_url)
        extracted.update(source_info)

    # 2. Main Detection Loop
    for url in all_urls:
        if not url: continue
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        params = parse_qs(parsed.query)
        
        # Merge params
        for k, v in params.items():
            extracted["all_params"][k] = v[0]
        
        # Check Trackers
        for name, sig in TRACKER_SIGNATURES.items():
            if any(d in domain for d in sig["domains"]) or \
               any(pk in params for pk in sig["params"]):
                extracted["tracker_tool"] = name
                extracted["tracker_confidence"] = "high"
                # Extract tracker_id
                for pk in sig["params"]:
                    if pk in params:
                        extracted["tracker_id"] = params[pk][0]
                break
        
        # Check Networks
        for name, sig in NETWORK_SIGNATURES.items():
            if any(d in domain for d in sig["domains"]) or \
               any(p in url.lower() for p in sig["url_patterns"]):
                extracted["affiliate_network"] = name
                extracted["network_confidence"] = "high"
                break

    # 3. Map IDs (Enhanced Aliases)
    PARAM_MAP = {
        "offer_id": ["offer_id", "offid", "oid", "prod", "product_id", "item", "cbid", "pay", "v", "campaign"],
        "affiliate_id": ["affiliate_id", "affid", "aff_id", "aid", "pub_id", "pid", "hop", "aff", "partner", "ref"],
        "click_id": ["clickid", "click_id", "tid", "transaction_id", "hopId", "c", "rc_uuid", "tblci", "ob_clickid"]
    }
    
    for key, aliases in PARAM_MAP.items():
        if extracted[key]: continue
        for alias in aliases:
            if alias in extracted["all_params"]:
                extracted[key] = extracted["all_params"][alias]
                break

    # 4. Path analysis fallback
    path_intel = extract_from_path(final_url)
    if not extracted["offer_id"] and path_intel.get("offer_id"):
        extracted["offer_id"] = path_intel["offer_id"]
    if not extracted["affiliate_id"] and path_intel.get("affiliate_id"):
        extracted["affiliate_id"] = path_intel["affiliate_id"]

    # 5. Intelligent Fallbacks
    if extracted["tracker_tool"] == "No Tracker Detected":
        if "lptoken" in extracted["all_params"]:
            extracted["tracker_tool"] = "Custom/In-house Tracker"
            extracted["tracker_id"] = extracted["all_params"]["lptoken"]
            extracted["tracker_confidence"] = "medium"
            
    if extracted["affiliate_network"] == "No Network Detected":
        if extracted["affiliate_id"] or extracted["offer_id"]:
            extracted["affiliate_network"] = "Direct/In-house"
            extracted["network_confidence"] = "low"
            extracted["needs_review"] = True

    # 6. Vertical & Domain
    ext = tldextract.extract(final_url)
    extracted["offer_domain"] = ext.registered_domain
    
    extracted["offer_vertical"] = "Unknown"
    search_str = (extracted["offer_domain"] + " " + urlparse(final_url).path).lower()
    for vert, keywords in VERTICALS.items():
        if any(k in search_str for k in keywords):
            extracted["offer_vertical"] = vert
            break
            
    return extracted

if __name__ == "__main__":
    # Case 1: Energy Revolution (Custom Tracker)
    test1_landing = "https://healthierlivingtips.org/int_pp_spl_ee/?c=w9htmg9omb4afuphjsnskcpi&r=289323_joehoft.com_2452300_MA_DESKTOP_Windows&t=66729985-64f1-4eee-a6f7-e69ac6bb45f7&lptoken=17fa761455d13979058f&widget_id=289323&content_id=13840265&boost_id=2452300&sn=joehoft.com&rc_uuid=a350284b-4273-4c4e-b256-39845b301f2d"
    test1_offer   = "https://theenergyrevolution.net/index-ers-auto-lead-39-promise-epp-lead-6-ph.html"

    print("--- Testing Case 1: Custom Tracker ---")
    res1 = extract_offer_intelligence(test1_offer, [], test1_landing)
    print(json.dumps(res1, indent=2))

    # Case 2: Complete Joint Care (ClickBank)
    test2_landing = "https://healthierlivingtips.org/int_jp_spl_jjt/?c=wqbo81mtl08t9uphj6om336r&lptoken=1786763155ca428435a6&widget_id=289323&sn=joehoft.com&rc_uuid=7c86c1b5-d441-4721-b42a-bb5bdde8b352"
    test2_offer   = "https://completejointcare.net/vsl/?hop=b1744&hopId=5553ed8c-113c-49af-9e17-31595b23daa8&v=bvsl"
    
    print("\n--- Testing Case 2: ClickBank & Path Analysis ---")
    res2 = extract_offer_intelligence(test2_offer, [], test2_landing)
    print(json.dumps(res2, indent=2))
