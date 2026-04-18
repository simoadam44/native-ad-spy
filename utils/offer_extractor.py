import json
import tldextract
from urllib.parse import urlparse, parse_qs

TRACKER_SIGNATURES = {
    "Voluum": {
        "domains": ["voluum.com", "voluumtrk.com", "trkvol.com", "clckmg.com"],
        "params": ["cid", "voluum"],
        "url_patterns": ["voluum", "voluumtrk"]
    },
    "Binom": {
        "domains": ["binom.org", "binomtracker.com"],
        "params": ["clickid", "click_id", "binom"],
        "url_patterns": ["binom"]
    },
    "Keitaro": {
        "domains": ["keitaro.io", "ktr.ovh"],
        "params": ["k_click_id", "subid", "keitaro"],
        "url_patterns": ["keitaro", "ktr."]
    },
    "RedTrack": {
        "domains": ["rdtk.io", "redtrack.io"],
        "params": ["rtid", "rt_click_id"],
        "url_patterns": ["redtrack", "rdtk"]
    },
    "Everflow": {
        "domains": ["everflow.io", "eflow.io"],
        "params": ["ef_click_id", "affid", "oid"],
        "url_patterns": ["ef_id", "everflow", "vndr=evf"]
    },
    "BeMob": {
        "domains": ["bemob.com", "bemobtrcks.com"],
        "params": ["click_id"],
        "url_patterns": ["bemob"]
    },
    "Thrivetracker": {
        "domains": ["thrivetracker.com", "thr.io"],
        "params": ["c"],
        "url_patterns": ["thrivetracker", "thr.io"]
    },
    "ClickMagick": {
        "domains": ["clkmg.com", "clkmr.com", "clickmagick.com"],
        "params": [],
        "url_patterns": ["clkmg", "clkmr", "clickmagick"]
    },
    "Hyros": {
        "domains": ["hyr.io", "hyros.com"],
        "params": ["h_ad_id"],
        "url_patterns": ["hyros", "hyr.io"]
    },
    "Tune/HasOffers": {
        "domains": ["tune.com", "hasoffers.com"],
        "params": ["offer_id", "aff_id"],
        "url_patterns": ["hasoffers", "tune.com"]
    },
    "ClickBank": {
        "domains": ["hop.clickbank.net", "clickbank.com"],
        "params": ["tid"],
        "url_patterns": ["clickbank", "hop.clickbank"]
    }
}

NETWORK_SIGNATURES = {
    "ClickBank": {"domains": ["hop.clickbank.net", "clickbank.com"], "url_patterns": ["clickbank"]},
    "MaxBounty": {"domains": ["maxbounty.com", "mb103.com"], "url_patterns": ["maxbounty"]},
    "Admitad": {"domains": ["ad.admitad.com", "alitems.com"], "url_patterns": ["admitad"]},
    "CPA.house": {"domains": ["cpa.house"], "url_patterns": ["cpa.house"]},
    "Everad": {"domains": ["everad.com", "everadtrk.com"], "url_patterns": ["everad"]},
    "AdCombo": {"domains": ["adcombo.com", "trkad.com", "trkpx.com"], "url_patterns": ["adcombo", "trkad", "trkpx"]},
    "CPAgetti": {"domains": ["cpagetti.com"], "url_patterns": ["cpagetti"]},
    "Awin": {"domains": ["awin1.com", "awin.com"], "url_patterns": ["awin"]},
    "Impact": {"domains": ["impact.com", "impactradius.com"], "url_patterns": ["impact"]},
    "ShareASale": {"domains": ["shareasale.com"], "url_patterns": ["shareasale"]},
    "Commission Junction": {"domains": ["cj.com", "jdoqocy"], "url_patterns": ["cj.com"]}
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

def extract_offer_intelligence(final_url: str, redirect_chain: list) -> dict:
    """
    Complete offer intelligence extractor.
    Identifies tracker, network, offer ID, and vertical from a redirect chain.
    """
    all_urls = []
    for item in redirect_chain:
        if isinstance(item, dict):
            all_urls.append(item.get("url") or item.get("from") or "")
        else:
            all_urls.append(str(item))
    all_urls.append(final_url)
    
    # 1. Tracker & Network Detection
    tracker_tool = "No Tracker Detected"
    affiliate_network = "No Network Detected"
    
    for url in all_urls:
        if not url: continue
        parsed = urlparse(url)
        domain = parsed.netloc.lower()
        url_lower = url.lower()
        params = parse_qs(parsed.query)
        
        # Check Trackers
        if tracker_tool == "No Tracker Detected":
            for name, sig in TRACKER_SIGNATURES.items():
                if any(d in domain for d in sig["domains"]) or \
                   any(p in url_lower for p in sig["url_patterns"]) or \
                   any(params.get(pk) for pk in sig["params"]):
                    tracker_tool = name
                    break
        
        # Check Networks
        if affiliate_network == "No Network Detected":
            for name, sig in NETWORK_SIGNATURES.items():
                if any(d in domain for d in sig["domains"]) or \
                   any(p in url_lower for p in sig["url_patterns"]):
                    affiliate_network = name
                    break

    # 2. Parameter Extraction
    collected_params = {}
    offer_id = None
    affiliate_id = None
    sub_id1 = None
    click_id = None

    PARAM_MAP = {
        "offer_id": ["offer_id", "offid", "oid", "product_id", "campaign_id", "cid", "bid"],
        "affiliate_id": ["affiliate_id", "affid", "aff_id", "aid", "pub_id", "publisher_id", "pid", "partner_id", "ref"],
        "sub_id1": ["subid", "subid1", "sub1", "s1", "aff_sub", "c1"],
        "click_id": ["clickid", "click_id", "tid", "transaction_id", "gclid", "fbclid", "ef_click_id"]
    }

    for url in all_urls:
        if not url: continue
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        for k, v in params.items():
            collected_params[k] = v[0]
            
            # Map to specific fields
            if not offer_id:
                for target in PARAM_MAP["offer_id"]:
                    if k.lower() == target: offer_id = v[0]; break
            if not affiliate_id:
                for target in PARAM_MAP["affiliate_id"]:
                    if k.lower() == target: affiliate_id = v[0]; break
            if not sub_id1:
                for target in PARAM_MAP["sub_id1"]:
                    if k.lower() == target: sub_id1 = v[0]; break
            if not click_id:
                for target in PARAM_MAP["click_id"]:
                    if k.lower() == target: click_id = v[0]; break

    # 3. Vertical detection
    ext = tldextract.extract(final_url)
    offer_domain = ext.registered_domain
    offer_path = urlparse(final_url).path.lower()
    
    offer_vertical = "Unknown"
    search_str = (offer_domain + " " + offer_path).lower()
    for vert, keywords in VERTICALS.items():
        if any(k in search_str for k in keywords):
            offer_vertical = vert
            break
            
    return {
        "final_offer_url": final_url,
        "offer_domain": offer_domain,
        "offer_vertical": offer_vertical,
        "affiliate_network": affiliate_network,
        "tracker_tool": tracker_tool,
        "offer_id": offer_id,
        "affiliate_id": affiliate_id,
        "sub_id1": sub_id1,
        "click_id": click_id,
        "redirect_chain": redirect_chain,
        "all_params": collected_params
    }

if __name__ == "__main__":
    test_url = "https://healthierlivingtips.org/int_di_spl_fbpp/?c=test&aff_id=2051&offid=78&sub1=native"
    print(json.dumps(extract_offer_intelligence(test_url, []), indent=2))
