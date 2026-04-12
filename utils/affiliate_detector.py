"""
Affiliate Network Detector
Analyzes landing URLs and matches them to known affiliate network fingerprints.
"""

from urllib.parse import urlparse

# --- Full Fingerprint Dictionary ---
AFFILIATE_FINGERPRINTS = {
    "AdmitAd":       ["ad.admitad.com", "admitad.com", "alitems.com"],
    "CPA.house":     ["cpa.house", "trk.cpa.house"],
    "CpaExchange":   ["cpaexchange.ru", "cpax.ru"],
    "AdCombo":       ["adcombo.com", "trkad.com", "trkpx.com"],
    "MaxBounty":     ["maxbounty.com", "mb103.com"],
    "ClickBank":     ["clickbank.com", "hop.clickbank.net", "cbdistribution.com"],
    "ClickDealer":   ["clickdealer.com", "cddeals.com"],
    "Mobidea":       ["mobidea.com", "mobifire.com"],
    "CPAGrip":       ["cpagripmedia.com", "cpagrip.com"],
    "Everad":        ["everad.com", "everadtrk.com"],
    "MyLead":        ["mylead.global", "mylead.pl"],
    "Encyl":         ["encyl.com"],
    "Advertise":     ["advertise.com"],
    "KMA.BIZ":       ["kma.biz", "kmtrkr.com"],
    "3snet":         ["3snet.com", "3snetwork.com"],
    "DrCash":        ["drcash.com", "drctrk.com"],
    "Adtrafico":     ["adtrafico.com"],
    "Terra Leads":   ["terraleads.com", "tleads.net"],
    "Affstar":       ["affstar.net", "aff.st"],
    "ArabyAds":      ["arabyads.com"],
    "Avazu":         ["avazu.net", "avazutracking.net"],
    "Mobvista":      ["mobvista.com", "mintegral.com"],
    "LoopMe":        ["loopme.com"],
    "MarketHealth":  ["markethealth.com", "mhealthtrack.com"],
    "PeerFly":       ["peerfly.com"],
    "Neverblue":     ["neverblue.com", "nbtracking.com"],
    "Salesdoubler":  ["salesdoubler.ua", "sdtracking.net"],
    "Taptica":       ["taptica.com"],
    "Mobusi":        ["mobusi.com"],
    "Leadzu":        ["leadzu.com"],
    "AdVendor":      ["advendor.com"],
    "CityAds":       ["cityadstrack.com", "cityads.ru"],
    "SellAction":    ["sellaction.com"],
    "CPAgetti":      ["cpagetti.com"],
    "Aff1":          ["aff1.ru", "aff1.net"],
    "7offers":       ["7offers.com"],
    "Money4Leads":   ["money4leads.com"],
    "AdWool":        ["adwool.com"],
    "Adsellerator":  ["adsellerator.com"],
    "LuckyOnline":   ["luckyonline.ru"],
    "Targeleon":     ["targeleon.com"],
    "Rocket10":      ["rocket10.ru"],
    "RocketProfit":  ["rocketprofit.com"],
    "Everyads":      ["everyads.com"],
    "Gambling.pro":  ["gambling.pro"],
    "Affiliaxe":     ["affiliaxe.com", "axetrack.com"],
    "ClickHeaven":   ["clickheaven.net"],
    "W2Mobile":      ["w2mobile.com"],
    "Actionpay":     ["actionpay.ru", "aprtx.com"],
    "AD1":           ["ad1.ru"],
    "AffOcean":      ["affocean.com"],
    "AffShark":      ["affshark.com"],
    "Advidi":        ["advidi.com"],
    "Convert2Media": ["convert2media.com", "c2m.net"],
    "Tapgerine":     ["tapgerine.com"],
    "Unilead":       ["unilead.net"],
    "vCommission":   ["vcommission.com"],
    "WakeApp":       ["wakeapp.com"],
    "MarsAds":       ["marsads.com"],
    "Cpamatica":     ["cpamatica.io"],
    "Mobio":         ["mobio.ru"],
    "AdvGame":       ["advgame.ru"],
    "ShareASale":    ["shareasale.com"],
    "Commission Junction": ["cj.com", "commission-junction.com"],
    "Rakuten":       ["rakuten.com", "linksynergy.com"],
    "Impact":        ["impact.com", "impactradius.com"],
    "PartnerStack":  ["partnerstack.com", "partnerstk.com"],
    "Awin":          ["awin.com", "awinmid.com"],
    "FlexOffers":    ["flexoffers.com"],
    "JVZoo":         ["jvzoo.com", "jvzr.com"],
    "WarriorPlus":   ["warriorplus.com"],
    "Digistore24":   ["digistore24.com"],
    "Amazon Associates": ["amzn.to", "amazon.com/dp", "amazon.com/gp/"],
}

# Generic tracking patterns — lower confidence
GENERIC_TRACKERS = [
    "clktrk", "track.", "trk.", "click.", "redir.", "redirect.",
    "aff.", "ref=", "out.", "link.", "goto.", "s1=", "clickid=",
    "sub1=", "pub_id=", "offer_id=", "affid=", "aff_id="
]

# Color coding by network type
NETWORK_COLORS = {
    # CPA Networks → amber
    "AdmitAd": "#F59E0B", "CPA.house": "#F59E0B", "MaxBounty": "#F59E0B",
    "ClickBank": "#F59E0B", "ClickDealer": "#F59E0B", "Everad": "#F59E0B",
    "MyLead": "#F59E0B", "Encyl": "#F59E0B", "Advertise": "#F59E0B",
    "KMA.BIZ": "#F59E0B", "3snet": "#F59E0B", "DrCash": "#F59E0B",
    "CpaExchange": "#F59E0B", "AdCombo": "#F59E0B", "Adtrafico": "#F59E0B",
    "Terra Leads": "#F59E0B", "Affstar": "#F59E0B", "AffShark": "#F59E0B",
    "CPAGrip": "#F59E0B", "CPAgetti": "#F59E0B", "Aff1": "#F59E0B",
    "Money4Leads": "#F59E0B", "PeerFly": "#F59E0B", "Neverblue": "#F59E0B",
    "FlexOffers": "#F59E0B", "JVZoo": "#F59E0B", "Digistore24": "#F59E0B",
    "Cpamatica": "#F59E0B", "CityAds": "#F59E0B", "SellAction": "#F59E0B",
    # Mobile Networks → blue
    "Mobidea": "#3B82F6", "Mobvista": "#3B82F6", "Avazu": "#3B82F6",
    "Taptica": "#3B82F6", "Mobusi": "#3B82F6", "W2Mobile": "#3B82F6",
    "Mobio": "#3B82F6", "WakeApp": "#3B82F6", "LoopMe": "#3B82F6",
    # Gambling / Gaming → red
    "Gambling.pro": "#EF4444", "AdvGame": "#EF4444",
    # eCommerce / Retail → green
    "Amazon Associates": "#10B981", "ShareASale": "#10B981",
    "Commission Junction": "#10B981", "Rakuten": "#10B981",
    "Awin": "#10B981", "Impact": "#10B981", "PartnerStack": "#10B981",
}

DEFAULT_COLOR = "#6B7280"  # Gray for unknown


def detect_affiliate_network(url: str) -> dict:
    """
    Analyzes a landing URL and returns detected affiliate network info.

    Returns:
        {
            "network": str,        # e.g. "AdmitAd" or "Direct / Unknown"
            "confidence": str,     # "high" | "medium" | "unknown"
            "color": str           # hex color for UI badge
        }
    """
    if not url or not isinstance(url, str) or len(url) < 10:
        return {"network": "Direct / Unknown", "confidence": "unknown", "color": DEFAULT_COLOR}

    try:
        parsed = urlparse(url.lower().strip())
        hostname = parsed.hostname or ""
        full_url = url.lower()

        # Step 1: Match against known fingerprints (high confidence)
        for network, patterns in AFFILIATE_FINGERPRINTS.items():
            for pattern in patterns:
                pattern_lower = pattern.lower()
                # Match domain or subdomain
                if hostname == pattern_lower or hostname.endswith("." + pattern_lower):
                    color = NETWORK_COLORS.get(network, DEFAULT_COLOR)
                    return {"network": network, "confidence": "high", "color": color}
                # Also match as substring in full URL (catches path-based tracking)
                if pattern_lower in full_url:
                    color = NETWORK_COLORS.get(network, DEFAULT_COLOR)
                    return {"network": network, "confidence": "high", "color": color}

        # Step 2: Generic tracker patterns (medium confidence)
        for pattern in GENERIC_TRACKERS:
            if pattern in full_url:
                return {
                    "network": "Unknown Affiliate",
                    "confidence": "medium",
                    "color": DEFAULT_COLOR
                }

        # Step 3: No match
        return {"network": "Direct / Unknown", "confidence": "unknown", "color": DEFAULT_COLOR}

    except Exception:
        return {"network": "Direct / Unknown", "confidence": "unknown", "color": DEFAULT_COLOR}
