import base64
import json
import re
import tldextract
from urllib.parse import urlparse, parse_qs

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# HELPER FUNCTIONS
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def clean_and_rank_chain(raw_chain: list, landing_url: str) -> list:
    """Filters out technical noise and returns cleaned URLs."""
    cleaned = []
    NOISE_EXTS = {".ts", ".m3u8", ".mp4", ".mp3", ".webm", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".css", ".js", ".woff", ".woff2", ".ico"}
    
    for url in raw_chain:
        if not url or not isinstance(url, str): continue
        u_lower = url.lower()
        if any(u_lower.endswith(ext) for ext in NOISE_EXTS): continue
        if url not in cleaned:
            cleaned.append(url)
    return cleaned

def is_dead_end(url: str) -> bool:
    if not url: return True
    u_lower = url.lower()
    DEAD_END_DOMAINS = ["api.vturb.com.br", "vturb.com", "player.vturb.com", "fast.wistia.net/embed", "vimeo.com/api", "youtube.com/api"]
    POSTBACK_PATTERNS = ["/sdk/conversion", "/postback", "/s2s/", "/server-to-server", "/conversion?effp=", "/track/conversion", "/pixel/fire"]
    AD_TECH = ["/rtb/bid", "/auction", "/prebid"]
    if any(d in u_lower for d in DEAD_END_DOMAINS + POSTBACK_PATTERNS + AD_TECH):
        return True
    return False

def is_ad_tech(url: str) -> bool:
    if not url: return False
    u_lower = url.lower()
    NOISE_PATTERNS = [
        "google-analytics", "gtm.js", "clarity.ms", "facebook.com/tr", "bing.com/bat", "doubleclick.net",
        "deepintent", "stackadapt", "smartadserver", "sync.taboola.com", "id5-sync.com", "adsrvr.org", "adnxs.com",
        "rubiconproject", "prebid", "3lift.com", "onetag-sys.com", "brainlyads.com", "fastlane.json",
        "cdn.taboola.com", "images.taboola.com", "cloudfront.net"
    ]
    return any(p in u_lower for p in NOISE_PATTERNS)

def detect_vertical(url: str) -> str:
    if not url: return "Unknown"
    u_lower = url.lower()
    VERTICAL_KEYWORDS = {
        "Health/Supplements": ["supplement", "health", "natural", "remedy", "formula", "keto", "detox", "slim", "blood", "joint", "pain", "sugar", "memory", "brain", "weight", "loss", "fat", "cholesterol", "derila", "ergo", "retinaclear"],
        "Finance": ["invest", "trading", "forex", "crypto", "insurance", "loan", "credit", "mortgage"],
        "Beauty/Skincare": ["skin", "beauty", "cream", "serum", "collagen", "hair", "anti-aging"],
        "Software/App": ["software", "app", "download", "tool", "platform", "saas"]
    }
    for v, keywords in VERTICAL_KEYWORDS.items():
        if any(k in u_lower for k in keywords):
            return v
    return "Unknown"

def detect_page_type(url: str) -> str:
    if not url: return "Unknown"
    u_lower = url.lower()
    PAGE_TYPES = {
        "/vsl/": "VSL (Video Sales Letter)",
        "/video/": "Video Sales Page",
        "/landers/": "Pre-lander",
        "/lp/": "Landing Page",
        "/checkout/": "Direct Checkout",
        "/order/": "Order Page",
        "/cb/vsl/": "ClickBank VSL"
    }
    for path, name in PAGE_TYPES.items():
        if path in u_lower:
            return name
    return "Landing Page"


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODULE 1: ENCODED PAYLOAD DECODER
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def decode_voluumdata(value: str) -> dict:
    import base64, json
    try:
        padded = value + "=" * (4 - len(value) % 4)
        decoded = base64.b64decode(padded).decode("utf-8")
        data = json.loads(decoded)
        return {
            "offer_id": (data.get("offerId") or
                         data.get("offer_id") or
                         data.get("oid")),
            "affiliate_id": (data.get("affiliateId") or
                             data.get("affiliate_id") or
                             data.get("aid") or
                             data.get("pubId")),
            "campaign_id": data.get("campaignId"),
            "click_id": data.get("clickId"),
            "traffic_source_id": data.get("trafficSourceId"),
            "tracker": "Voluum",
            "raw": data
        }
    except Exception:
        return {}

def extract_revcontent_params(url: str) -> dict:
    from urllib.parse import parse_qs, urlparse
    params = parse_qs(urlparse(url).query)
    return {
        "click_id": params.get("c", [None])[0],
        "widget_id": params.get("widget_id", [None])[0],
        "content_id": params.get("content_id", [None])[0],
        "boost_id": params.get("boost_id", [None])[0],
        "publisher_site": params.get("sn", [None])[0],
        "rc_uuid": params.get("rc_uuid", [None])[0],
        "lptoken": params.get("lptoken", [None])[0],
        "tracker": "Custom/In-house" if params.get("lptoken") else None,
        "traffic_source": "Revcontent"
    }

def decode_clickbank(url: str) -> dict:
    from urllib.parse import parse_qs, urlparse
    import re
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    result = {"network": None, "affiliate_id": None, "click_id": None}

    # Method 1: hop= param
    if "hop" in params:
        result["network"] = "ClickBank"
        result["affiliate_id"] = params["hop"][0]

    # Method 2: hopId= param
    if "hopId" in params:
        result["network"] = "ClickBank"
        result["click_id"] = params["hopId"][0]

    # Method 3: /cb/ in path
    if "/cb/" in parsed.path or "/clickbank/" in parsed.path:
        result["network"] = "ClickBank"

    # Method 4: hop.clickbank.net domain
    if "hop.clickbank.net" in parsed.netloc:
        result["network"] = "ClickBank"
        # Parse: affiliate.product.hop.clickbank.net
        parts = parsed.netloc.split(".")
        if len(parts) >= 4:
            result["affiliate_id"] = parts[0]
            result["offer_domain"] = parts[1]

    # Method 5: affiliate= param with /cb/ path
    if "affiliate" in params and "/cb/" in parsed.path:
        result["network"] = "ClickBank"
        result["affiliate_id"] = params["affiliate"][0]

    return result if result["network"] else {}

def decode_everflow(url: str) -> dict:
    from urllib.parse import parse_qs, urlparse
    params = parse_qs(urlparse(url).query)

    if not any(p in params for p in ["effp","ef_click_id","oid"]):
        if "everflow" not in url.lower() and "djpcraze.com" not in url.lower():
            return {}

    result = {
        "network": "Everflow",
        "tracker": "Everflow",
        "offer_id": params.get("oid", [None])[0],
        "affiliate_id": params.get("affid",
                        params.get("aff_id", [None]))[0],
        "click_id": params.get("effp",
                    params.get("ef_click_id",
                    params.get("transaction_id", [None])))[0],
    }

    # Real offer domain hidden in event_source_url
    if "event_source_url" in params:
        src = params["event_source_url"][0]
        result["real_offer_domain"] = src
        result["final_offer_url"] = (
            src if src.startswith("http")
            else f"https://{src}"
        )

    return result

def decode_hasoffers(url: str) -> dict:
    from urllib.parse import parse_qs, urlparse
    params = parse_qs(urlparse(url).query)
    parsed = urlparse(url)

    is_hasoffers = (
        "hasoffers.com" in parsed.netloc or
        "tune.com" in parsed.netloc or
        "go2cloud.org" in parsed.netloc or
        ("offer_id" in params and "aff_id" in params)
    )

    if not is_hasoffers:
        return {}

    return {
        "network": "Tune/HasOffers",
        "offer_id": params.get("offer_id", [None])[0],
        "affiliate_id": params.get("aff_id", [None])[0],
        "click_id": params.get("aff_click_id",
                    params.get("transaction_id", [None]))[0],
        "sub_id1": params.get("aff_sub", [None])[0],
        "sub_id2": params.get("aff_sub2", [None])[0],
    }

def decode_impact(url: str) -> dict:
    from urllib.parse import parse_qs, urlparse
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    is_impact = any(d in parsed.netloc for d in
                    ["impact.com", "impactradius.com",
                     "sjv.io", "prf.hn"])

    if not is_impact:
        return {}

    return {
        "network": "Impact",
        "affiliate_id": params.get("irpid",
                        params.get("subid1", [None]))[0],
        "offer_id": params.get("campaignid", [None])[0],
        "click_id": params.get("clickid", [None])[0],
    }

def decode_digistore24(url: str) -> dict:
    from urllib.parse import parse_qs, urlparse
    parsed = urlparse(url)
    params = parse_qs(parsed.query)

    if "digistore24.com" not in parsed.netloc:
        return {}

    return {
        "network": "Digistore24",
        "affiliate_id": params.get("aff", [None])[0],
        "offer_id": params.get("pay", params.get("cid", [None]))[0],
        "click_id": params.get("uid", [None])[0],
    }

AFFILIATE_ID_ALIASES = [
    "aff_id", "affid", "affiliate_id", "affiliate", "aid", "a_aid",
    "hop", "aff", "mid", "awinaffid", "irpid", "pid", "pub_id",
    "publisher_id", "partner", "partner_id", "ref", "refid", "promo",
    "u", "uid", "wid",
]

OFFER_ID_ALIASES = [
    "offer_id", "offid", "oid", "prod", "product_id", "campaign_id",
    "cid", "item", "f", "cbid", "pay", "bid", "program_id", "deal_id", "o",
]

SUB_ID_ALIASES = [
    "subid", "subid1", "subid2", "subid3", "sub1", "sub2", "sub3",
    "sub4", "sub5", "aff_sub", "aff_sub2", "aff_sub3", "s1", "s2", "s3",
    "c1", "c2", "c3", "tid", "clickref",
]

CLICK_ID_ALIASES = [
    "clickid", "click_id", "transaction_id", "cid", "hopId", "effp",
    "ef_click_id", "k_click_id", "rtid", "rc_uuid", "tblci", "gclid",
    "fbclid", "ttclid", "msclkid", "uuid",
]

def extract_generic_params(url: str) -> dict:
    from urllib.parse import parse_qs, urlparse
    params = parse_qs(urlparse(url).query)

    def find_first(aliases):
        for alias in aliases:
            if alias in params and params[alias][0]:
                return params[alias][0]
        return None

    return {
        "affiliate_id": find_first(AFFILIATE_ID_ALIASES),
        "offer_id":     find_first(OFFER_ID_ALIASES),
        "sub_id1":      find_first(SUB_ID_ALIASES),
        "click_id":     find_first(CLICK_ID_ALIASES),
    }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODULE 2: NETWORK DETECTOR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

NETWORK_DETECTION_RULES = [

    # ── Tier 1: Domain-based (100% certain) ──────────────────

    {
        "name": "ClickBank",
        "confidence": "high",
        "check": lambda url, p: (
            "hop.clickbank.net" in url or
            "pay.clickbank.net" in url or
            "clickbank.com" in url
        )
    },
    {
        "name": "Everflow",
        "confidence": "high",
        "check": lambda url, p: (
            "everflow.io" in url or
            "eflow.io" in url or
            "effp=" in url or
            "ef_click_id=" in url or
            "djpcraze.com" in url      # known Everflow instance
        )
    },
    {
        "name": "Tune/HasOffers",
        "confidence": "high",
        "check": lambda url, p: (
            "hasoffers.com" in url or
            "tune.com" in url or
            "go2cloud.org" in url
        )
    },
    {
        "name": "Impact",
        "confidence": "high",
        "check": lambda url, p: any(d in url for d in
            ["impactradius.com", "sjv.io", "prf.hn", "impact.com"])
    },
    {
        "name": "ShareASale",
        "confidence": "high",
        "check": lambda url, p: "shareasale.com" in url
    },
    {
        "name": "CJ/Commission Junction",
        "confidence": "high",
        "check": lambda url, p: any(d in url for d in
            ["anrdoezrs.net","dpbolvw.net","tkqlhce.com",
             "jdoqocy.com","qksrv.net"])
    },
    {
        "name": "Awin",
        "confidence": "high",
        "check": lambda url, p: "awin1.com" in url or "awin.com" in url
    },
    {
        "name": "Rakuten",
        "confidence": "high",
        "check": lambda url, p: any(d in url for d in
            ["linksynergy.com","rakutenmarketing.com"])
    },
    {
        "name": "MaxBounty",
        "confidence": "high",
        "check": lambda url, p: (
            "maxbounty.com" in url or "mb103.com" in url
        )
    },
    {
        "name": "Admitad",
        "confidence": "high",
        "check": lambda url, p: (
            "admitad.com" in url or "alitems.com" in url
        )
    },
    {
        "name": "Digistore24",
        "confidence": "high",
        "check": lambda url, p: "digistore24.com" in url or "ds24" in url
    },
    {
        "name": "Partnerize",
        "confidence": "high",
        "check": lambda url, p: (
            "partnerize.com" in url or "prf.hn" in url
        )
    },
    {
        "name": "CPAGrip",
        "confidence": "high",
        "check": lambda url, p: "cpagrip" in url
    },
    {
        "name": "Everad",
        "confidence": "high",
        "check": lambda url, p: "everad" in url
    },
    {
        "name": "AdCombo",
        "confidence": "high",
        "check": lambda url, p: any(d in url for d in
            ["adcombo.com","trkad.com","trkpx.com"])
    },
    {
        "name": "CPA.house",
        "confidence": "high",
        "check": lambda url, p: "cpa.house" in url
    },
    {
        "name": "MyLead",
        "confidence": "high",
        "check": lambda url, p: "mylead" in url
    },
    {
        "name": "ClickDealer",
        "confidence": "high",
        "check": lambda url, p: "clickdealer.com" in url
    },

    # ── Tier 2: Path-based (highly reliable) ─────────────────

    {
        "name": "ClickBank",
        "confidence": "high",
        "check": lambda url, p: (
            "/cb/vsl/" in url or
            ("/cb/" in url and "hopId=" in url)
        )
    },

    # ── Tier 3: Param-based (reliable with context) ──────────

    {
        "name": "Tune/HasOffers",
        "confidence": "high",
        "check": lambda url, p: (
            "offer_id" in p and "aff_id" in p
        )
    },
    {
        "name": "ClickBank",
        "confidence": "medium",
        "check": lambda url, p: (
            "hop" in p and
            "clickbank" not in url and
            len(p.get("hop", [""])[0]) <= 20
        )
    },
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODULE 3: TRACKER DETECTOR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TRACKER_RULES = [
    {
        "name": "Voluum",
        "confidence": "high",
        "url_check": lambda url: (
            "voluum.com" in url or
            "voluumtrk.com" in url or
            "voluumdata=" in url
        ),
        "html_check": lambda html: (
            "voluum.com" in html or
            "voluumdata" in html or
            "__vl_cid" in html
        ),
        "js_vars": ["__vl_cid", "voluumClickId", "voluumdata"],
        "decode_param": "voluumdata",
        "decode_fn": "decode_voluumdata"
    },
    {
        "name": "Binom",
        "confidence": "high",
        "url_check": lambda url: "binom" in url.lower(),
        "html_check": lambda html: "binom.org" in html,
        "js_vars": ["binom_click_id", "binomClickId"],
    },
    {
        "name": "Keitaro",
        "confidence": "high",
        "url_check": lambda url: "keitaro" in url.lower() or "k_click_id=" in url.lower(),
        "html_check": lambda html: "keitaro" in html.lower() or "keitaroclickid" in html.lower(),
        "js_vars": ["keitaroClickId", "k_click_id"],
    },
    {
        "name": "RedTrack",
        "confidence": "high",
        "url_check": lambda url: any(d in url for d in
            ["rdtk.io","redtrack.io"]),
        "html_check": lambda html: "redtrack" in html.lower(),
    },
    {
        "name": "Everflow",
        "confidence": "high",
        "url_check": lambda url: (
            "everflow.io" in url or
            "eflow.io" in url or
            "effp=" in url
        ),
        "html_check": lambda html: (
            "everflow" in html.lower() or
            "window.EF" in html or
            "EverflowClient" in html
        ),
        "js_vars": ["EF", "EverflowClient"],
    },
    {
        "name": "BeMob",
        "confidence": "high",
        "url_check": lambda url: "bemob" in url.lower(),
        "html_check": lambda html: "bemob" in html.lower(),
    },
    {
        "name": "Thrivetracker",
        "confidence": "high",
        "url_check": lambda url: (
            "thrivetracker.com" in url or "thr.io" in url
        ),
        "html_check": lambda html: "thrivetracker" in html.lower(),
    },
    {
        "name": "ClickMagick",
        "confidence": "high",
        "url_check": lambda url: any(d in url for d in
            ["clkmg.com","clkmr.com","clickmagick.com"]),
        "html_check": lambda html: "clickmagick" in html.lower(),
    },
    {
        "name": "FunnelFlux",
        "confidence": "high",
        "url_check": lambda url: "funnelflux" in url.lower(),
        "html_check": lambda html: "funnelflux" in html.lower(),
    },
    {
        "name": "Hyros",
        "confidence": "high",
        "url_check": lambda url: "hyros" in url.lower(),
        "html_check": lambda html: (
            "hyros" in html.lower() or "_hyros" in html
        ),
        "js_vars": ["_hyros", "hyros_data"],
    },
    {
        "name": "Custom/In-house",
        "confidence": "medium",
        "url_check": lambda url: "lptoken=" in url,
        "html_check": lambda html: False,
        "note": "lptoken= signals custom tracker"
    },
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODULE 4: DEAD-END & RESOLUTION ENGINE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def resolve_offer_url(
    raw_final_url, cleaned_chain,
    extracted_params, landing_url
) -> dict:

    # Priority 1: raw_final is valid non-dead-end
    if not is_dead_end(raw_final_url):
        return {"url": raw_final_url, "method": "direct"}

    # Priority 2: event_source_url param (Everflow postbacks)
    if extracted_params.get("real_offer_domain"):
        domain = extracted_params["real_offer_domain"]
        url = domain if domain.startswith("http") \
              else f"https://{domain}"
        return {"url": url, "method": "event_source_url"}

    # Priority 3: last valid URL in cleaned chain
    for url in reversed(cleaned_chain):
        if not is_dead_end(url) and not is_ad_tech(url):
            parsed_domain = tldextract.extract(url).registered_domain
            landing_domain = tldextract.extract(landing_url).registered_domain
            if parsed_domain != landing_domain:
                return {"url": url, "method": "chain_last_valid"}

    # Priority 4: build from known offer domain
    offer_domain = extracted_params.get("offer_domain")
    if offer_domain:
        return {
            "url": f"https://{offer_domain}",
            "method": "constructed_from_domain"
        }

    # Priority 5: unresolved
    return {"url": None, "method": "unresolved",
            "needs_review": True}

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MODULE 5: MAIN ORCHESTRATOR
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def extract_offer_intelligence(
    landing_url: str,
    raw_final_url: str,
    all_captured_urls: list,
    page_html: str = "",
    page_js_vars: dict = None
) -> dict:
    if page_js_vars is None:
        page_js_vars = {}

    # ── Step 1: Build URL pool ────────────────────────────────
    all_urls = list(dict.fromkeys(
        [landing_url] +
        all_captured_urls +
        ([raw_final_url] if raw_final_url else [])
    ))

    # ── Step 2: Clean the pool ────────────────────────────────
    cleaned = clean_and_rank_chain(all_urls, landing_url)

    # ── Step 3: Decode encoded payloads ──────────────────────
    decoded = {}
    
    # Process all URLs first, but process the raw_final_url LAST so its parameters overwrite background noise
    processing_order = [u for u in all_urls if u != raw_final_url]
    if raw_final_url:
        processing_order.append(raw_final_url)

    for url in processing_order:
        if not url: continue
        from urllib.parse import parse_qs, urlparse
        params = parse_qs(urlparse(url).query)

        if "voluumdata" in params:
            d = decode_voluumdata(params["voluumdata"][0])
            decoded.update(d)

        if "cep" in params:
            d = extract_revcontent_params(url)
            decoded.update({k:v for k,v in d.items() if v})

        if "effp" in params or "djpcraze.com" in url:
            d = decode_everflow(url)
            decoded.update({k:v for k,v in d.items() if v})

        if any(p in params for p in ["hop","hopId"]) or \
           "clickbank" in url or "/cb/" in urlparse(url).path:
            d = decode_clickbank(url)
            decoded.update({k:v for k,v in d.items() if v})

        if "hasoffers.com" in url or "tune.com" in url or "go2cloud.org" in url or \
           ("offer_id" in params and "aff_id" in params):
            d = decode_hasoffers(url)
            decoded.update({k:v for k,v in d.items() if v})

        if "digistore24.com" in url:
            d = decode_digistore24(url)
            decoded.update({k:v for k,v in d.items() if v})

        if any(d in url for d in
               ["impactradius.com","sjv.io","prf.hn", "impact.com"]):
            d = decode_impact(url)
            decoded.update({k:v for k,v in d.items() if v})

        if "rc_uuid" in params:
            decoded["rc_uuid"] = params["rc_uuid"][0]
        if "tblci" in params:
            decoded["tblci"] = params["tblci"][0]

        # Always run generic extractor on EVERY URL
        # (this catches aff_id=57967 in final_offer_url)
        generic = extract_generic_params(url)
        for key, val in generic.items():
            if val:
                decoded[key] = val

    # ── Step 4: Detect network ────────────────────────────────
    network = {"name": "Unknown", "confidence": "none"}
    for url in all_urls:
        if not url: continue
        params = parse_qs(urlparse(url).query)
        for rule in NETWORK_DETECTION_RULES:
            if rule["check"](url.lower(), params):
                if rule["confidence"] == "high":
                    network = {
                        "name": rule["name"],
                        "confidence": "high",
                        "detected_in": url[:80]
                    }
                    break
                elif network["confidence"] != "high":
                    network = {
                        "name": rule["name"],
                        "confidence": "medium",
                        "detected_in": url[:80]
                    }
        if network["confidence"] == "high":
            break

    # Use decoded network if better
    if decoded.get("network") and network["name"] == "Unknown":
        network["name"] = decoded["network"]
        network["confidence"] = "high"
        network["source"] = "decoded_payload"

    # Fallback to direct/in-house if IDs found but no network
    if network["name"] == "Unknown" and (decoded.get("affiliate_id") or decoded.get("offer_id")):
        network["name"] = "Direct/In-house"
        network["confidence"] = "low"

    # ── Step 5: Detect tracker ────────────────────────────────
    tracker = {"name": "Unknown", "confidence": "none"}
    for url in all_urls:
        if not url: continue
        for rule in TRACKER_RULES:
            if rule["url_check"](url.lower()):
                tracker = {
                    "name": rule["name"],
                    "confidence": rule["confidence"],
                    "detected_in": url[:80]
                }
                break
        if tracker["confidence"] == "high":
            break

    # Check HTML if still unknown
    if tracker["name"] == "Unknown" and page_html:
        html_lower = page_html.lower()
        for rule in TRACKER_RULES:
            if rule.get("html_check") and \
               rule["html_check"](html_lower):
                tracker = {
                    "name": rule["name"],
                    "confidence": "medium",
                    "detected_in": "page_html"
                }
                break

    # Check JS variables
    if tracker["name"] == "Unknown" and page_js_vars:
        for rule in TRACKER_RULES:
            for js_var in rule.get("js_vars", []):
                if js_var in page_js_vars:
                    tracker = {
                        "name": rule["name"],
                        "confidence": "high",
                        "detected_in": f"js_var:{js_var}"
                    }
                    break

    # ── Step 6: Resolve final offer URL ──────────────────────
    offer_resolution = resolve_offer_url(
        raw_final_url, cleaned, decoded, landing_url
    )

    # ── Step 7: Analyze offer domain ─────────────────────────
    offer_url = offer_resolution["url"]
    offer_domain = None
    offer_vertical = None
    page_type = None
    if offer_url:
        offer_domain = tldextract.extract(offer_url).registered_domain
        offer_vertical = detect_vertical(offer_url)
        page_type = detect_page_type(offer_url)

    # ── Step 8: Compile and return ───────────────────────────
    return {
        # Network & Tracker
        "affiliate_network":    network["name"],
        "network_confidence":   network["confidence"],
        "tracker_tool":         tracker["name"],
        "tracker_confidence":   tracker["confidence"],

        # IDs — check decoded first, then generic extracted
        "affiliate_id": (decoded.get("affiliate_id")),
        "offer_id":     (decoded.get("offer_id")),
        "sub_id1":      (decoded.get("sub_id1")),
        "sub_id2":      (decoded.get("sub_id2")),
        "click_id":     (decoded.get("click_id")),

        # Offer details
        "final_offer_url":  offer_url,
        "offer_url_method": offer_resolution["method"],
        "offer_domain":     offer_domain,
        "offer_vertical":   offer_vertical,
        "page_type":        page_type,

        # Traffic source
        "traffic_source": (
            decoded.get("traffic_source") or
            ("Revcontent" if decoded.get("rc_uuid") else
             "Taboola"    if decoded.get("tblci") else
             "MGID"       if "mgid" in landing_url else
             "Outbrain"   if "outbrain" in landing_url else
             "Unknown")
        ),
        "widget_id":      decoded.get("widget_id"),
        "publisher_site": decoded.get("publisher_site"),

        # Debug
        "needs_review":      offer_resolution.get("needs_review", False),
        "dead_end_detected": is_dead_end(raw_final_url or ""),
        "resolution_method": offer_resolution["method"],
        "urls_analyzed":     len(all_urls),
        "detection_log": {
            "network_found_in": network.get("detected_in"),
            "tracker_found_in": tracker.get("detected_in"),
            "decoded_keys":     list(decoded.keys()),
        }
    }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# VALIDATION: 10 REAL CASES
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def run_all_tests():

    # T1: Voluum + aff_id in final URL
    r = extract_offer_intelligence(
        landing_url="https://wellnessgaze.com/lifehacks-v22/?voluumdata=eyJvZmZlcklkIjoiMTIzIiwiYWZmaWxpYXRlSWQiOiI0NTYifQ",
        raw_final_url="https://getretinaclear.com/video/?aff_id=57967&subid=vcx1676460636",
        all_captured_urls=[]
    )
    assert r["tracker_tool"]    == "Voluum",    f"T1a fail: {r['tracker_tool']}"
    assert r["affiliate_id"]    == "57967",     f"T1b fail: {r['affiliate_id']}"
    assert r["sub_id1"]         == "vcx1676460636", f"T1c fail: {r['sub_id1']}"
    print("✅ T1 passed")

    # T2: ClickBank via /cb/ path + affiliate param
    r = extract_offer_intelligence(
        landing_url="https://calmgrowthcenter.com/crstrenght/cb/vsl/v3/?hopId=3f93&affiliate=supaffcb&tid=289322",
        raw_final_url="https://calmgrowthcenter.com/crstrenght/cb/vsl/v3/?hopId=3f93&affiliate=supaffcb",
        all_captured_urls=[]
    )
    assert r["affiliate_network"] == "ClickBank", f"T2a fail: {r['affiliate_network']}"
    assert r["affiliate_id"]      == "supaffcb",  f"T2b fail: {r['affiliate_id']}"
    assert r["click_id"]          == "3f93",      f"T2c fail: {r['click_id']}"
    print("✅ T2 passed")

    # T3: Everflow postback → event_source_url
    r = extract_offer_intelligence(
        landing_url="https://smarterlivingdaily.org/lps/?cep=someval&lptoken=someval",
        raw_final_url="https://djpcraze.com/sdk/conversion?effp=37fb&oid=7971&affid=5351&event_source_url=get-derila-ergo.com",
        all_captured_urls=[]
    )
    assert r["affiliate_network"] == "Everflow",              f"T3a fail: {r['affiliate_network']}"
    assert r["offer_id"]          == "7971",                  f"T3b fail: {r['offer_id']}"
    assert r["affiliate_id"]      == "5351",                  f"T3c fail: {r['affiliate_id']}"
    assert r["final_offer_url"]   == "https://get-derila-ergo.com", f"T3d fail: {r['final_offer_url']}"
    print("✅ T3 passed")

    # T4: vturb dead-end → unresolved
    r = extract_offer_intelligence(
        landing_url="https://healthheadlines.info/v209659/?cep=someval&lptoken=17fa&widget_id=289322&sn=joehoft.com",
        raw_final_url="https://api.vturb.com.br/vturb/check",
        all_captured_urls=[]
    )
    assert r["dead_end_detected"] == True,    f"T4a fail"
    assert r["final_offer_url"]   is None,    f"T4b fail"
    assert r["tracker_tool"]      == "Custom/In-house", f"T4c fail"
    assert r["traffic_source"]    == "Revcontent",      f"T4d fail"
    assert r["widget_id"]         == "289322",           f"T4e fail"
    print("✅ T4 passed")

    # T5: HasOffers standard params
    r = extract_offer_intelligence(
        landing_url="https://sometracker.go2cloud.org/aff_c?offer_id=123&aff_id=456&aff_click_id=abc",
        raw_final_url="https://sometracker.go2cloud.org/aff_c?offer_id=123&aff_id=456",
        all_captured_urls=[]
    )
    assert r["affiliate_network"] == "Tune/HasOffers", f"T5a fail"
    assert r["offer_id"]          == "123",            f"T5b fail"
    assert r["affiliate_id"]      == "456",            f"T5c fail"
    print("✅ T5 passed")

    # T6: ClickBank via hop.clickbank.net subdomain
    r = extract_offer_intelligence(
        landing_url="https://b1744.completejointcare.hop.clickbank.net/",
        raw_final_url="https://completejointcare.net/vsl/?hop=b1744&hopId=5553ed8c",
        all_captured_urls=[]
    )
    assert r["affiliate_network"] == "ClickBank", f"T6a fail"
    assert r["affiliate_id"]      == "b1744",     f"T6b fail: {r['affiliate_id']}"
    print("✅ T6 passed")

    # T7: Outbrain tracking URL resolved
    import sys, os
    sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    try:
        from utils.url_resolver import is_tracking_redirect
        url = "https://tr.outbrain.com/cachedClickId?marketerId=008dfd44"
        assert is_tracking_redirect(url) == True, "T7 fail"
        print("✅ T7 passed")
    except ImportError:
        print("⚠️ T7 skipped (url_resolver not found in tests)")

    # T8: Digistore24
    r = extract_offer_intelligence(
        landing_url="https://www.digistore24.com/redir/123456/myaffiliate/",
        raw_final_url="https://www.digistore24.com/order/123456?aff=myaffiliate",
        all_captured_urls=[]
    )
    assert r["affiliate_network"] == "Digistore24",   f"T8a fail"
    assert r["affiliate_id"]      == "myaffiliate",   f"T8b fail"
    print("✅ T8 passed")

    # T9: Strip tracking params keep affiliate params
    try:
        from deep_analyzer import strip_tracking_params
        url = "https://offer.com/?aff_id=123&utm_source=taboola&fbclid=abc&subid=xyz"
        cleaned = strip_tracking_params(url)
        assert "aff_id=123" in cleaned,      "T9a fail"
        assert "utm_source" not in cleaned,  "T9b fail"
        assert "fbclid" not in cleaned,      "T9c fail"
        assert "subid=xyz" in cleaned,       "T9d fail"
        print("✅ T9 passed")
    except ImportError:
        print("⚠️ T9 skipped (deep_analyzer not found in tests)")

    # T10: Generic aff_id extracted from final_offer_url
    r = extract_offer_intelligence(
        landing_url="https://wellnesspeek.com/lifehacks/?rc_uuid=76a9ef5c",
        raw_final_url="https://getretinaclear.com/video/?aff_id=57967&subid=clf294",
        all_captured_urls=[]
    )
    assert r["affiliate_id"]   == "57967",      f"T10a fail: {r['affiliate_id']}"
    assert r["sub_id1"]        == "clf294",      f"T10b fail"
    assert r["traffic_source"] == "Revcontent",  f"T10c fail: {r['traffic_source']}"
    print("✅ T10 passed")

    print("\n🎉 All tests passed!")

if __name__ == "__main__":
    run_all_tests()
