"""
Tracking Tool Detector
Analyzes landing URLs to identify which tracking/analytics platform the advertiser uses.
"""
from urllib.parse import urlparse, parse_qs

TRACKING_FINGERPRINTS = {
    "Voluum": {
        "domains": ["voluum.com", "voluumtrk.com", "trkvol.com", "vlm.io"],
        "url_patterns": ["voluum", "vlm.io", "voluumtrk"],
        "color": "#E84D1C",
    },
    "Binom": {
        "domains": ["binom.org"],
        "url_patterns": ["binom", "bnm."],
        "color": "#FF6B00",
    },
    "Prosper202": {
        "domains": ["prosper202.com"],
        "url_patterns": ["prosper202", "tracking202", "p202"],
        "color": "#4A90D9",
    },
    "Thrive": {
        "domains": ["thrivetracker.com", "thrivecart.com"],
        "url_patterns": ["thrivetracker", "thrivecart", "thr.io"],
        "color": "#00BCD4",
    },
    "RedTrack": {
        "domains": ["redtrack.io", "rdtk.io"],
        "url_patterns": ["redtrack", "rdtk"],
        "color": "#E53935",
    },
    "ClickMagick": {
        "domains": ["clickmagick.com", "clkmg.com", "clkmr.com"],
        "url_patterns": ["clickmagick", "clkmg", "clkmr"],
        "color": "#7B1FA2",
    },
    "Hyros": {
        "domains": ["hyros.com", "hyr.io"],
        "url_patterns": ["hyros", "hyr.io"],
        "color": "#1565C0",
    },
    "Trackier": {
        "domains": ["trackier.com", "cbleads.com"],
        "url_patterns": ["trackier"],
        "color": "#2E7D32",
    },
    "Keitaro": {
        "domains": ["keitaro.io"],
        "url_patterns": ["keitaro", "ktr."],
        "color": "#F57F17",
    },
    "FunnelFlux": {
        "domains": ["funnelflux.com", "funnelflux.pro"],
        "url_patterns": ["funnelflux", "fnlflx"],
        "color": "#6A1B9A",
    },
    "CPVLab": {
        "domains": ["cpvlab.com"],
        "url_patterns": ["cpvlab"],
        "color": "#37474F",
    },
    "iMobiTrax": {
        "domains": ["imobitrax.com"],
        "url_patterns": ["imobitrax"],
        "color": "#00695C",
    },
    "AdsBridge": {
        "domains": ["adsbridge.com", "adbridg.com"],
        "url_patterns": ["adsbridge"],
        "color": "#C62828",
    },
    "BeMob": {
        "domains": ["bemob.com", "bemobtrcks.com"],
        "url_patterns": ["bemob"],
        "color": "#1B5E20",
    },
    "OctoTracker": {
        "domains": ["octotracker.com"],
        "url_patterns": ["octotracker", "octo8r"],
        "color": "#4A148C",
    },
    "Scaleo": {
        "domains": ["scaleo.io"],
        "url_patterns": ["scaleo"],
        "color": "#0D47A1",
    },
    "AffiliaXe": {
        "domains": ["affiliaxe.com", "axetrack.com"],
        "url_patterns": ["affiliaxe", "axetrack"],
        "color": "#BF360C",
    },
    "Facebook Pixel": {
        "domains": ["facebook.com/tr"],
        "url_patterns": ["fbclid", "fb_click_id"],
        "color": "#1877F2",
    },
    "TikTok Pixel": {
        "domains": ["analytics.tiktok.com"],
        "url_patterns": ["ttclid", "tiktok_pixel"],
        "color": "#010101",
    },
    "Google Analytics": {
        "domains": ["google-analytics.com", "googletagmanager.com"],
        "url_patterns": ["utm_source", "utm_medium", "utm_campaign", "gtm="],
        "color": "#F9A825",
    },
}

UNKNOWN_TRACKER = {"tracker": "No Tracking", "confidence": "unknown", "color": "#6B7280"}


def detect_tracking_tool(url: str) -> dict:
    """
    Analyzes a landing URL and returns detected tracking tool info.

    Returns:
        {
            "tracker": str,      # e.g "Voluum" or "No Tracking"
            "confidence": str,   # "high" | "medium" | "unknown"
            "color": str         # hex color
        }
    """
    if not url or not isinstance(url, str) or len(url) < 10:
        return UNKNOWN_TRACKER

    try:
        parsed = urlparse(url.lower().strip())
        hostname = parsed.hostname or ""
        full_url = url.lower()
        params = parse_qs(parsed.query)

        # Special high-confidence signals first
        if "fbclid" in params or "fb_click_id" in params:
            return {"tracker": "Facebook Pixel", "confidence": "high", "color": "#1877F2"}
        if "ttclid" in params:
            return {"tracker": "TikTok Pixel", "confidence": "high", "color": "#010101"}

        # Step 1: Domain match (high confidence)
        for tracker_name, cfg in TRACKING_FINGERPRINTS.items():
            for domain in cfg.get("domains", []):
                domain_lower = domain.lower()
                if hostname == domain_lower or hostname.endswith("." + domain_lower):
                    return {"tracker": tracker_name, "confidence": "high", "color": cfg["color"]}

        # Step 2: URL pattern match (medium-high confidence)
        for tracker_name, cfg in TRACKING_FINGERPRINTS.items():
            for pattern in cfg.get("url_patterns", []):
                if pattern.lower() in full_url:
                    return {"tracker": tracker_name, "confidence": "medium", "color": cfg["color"]}

        # Step 3: UTM params = Google Analytics / some tracker
        if any(k in params for k in ["utm_source", "utm_medium", "utm_campaign"]):
            return {"tracker": "Google Analytics", "confidence": "medium", "color": "#F9A825"}

        return UNKNOWN_TRACKER

    except Exception:
        return UNKNOWN_TRACKER
