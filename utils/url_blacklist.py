# ══════════════════════════════════════
# BLACKLIST A: Domains to ALWAYS ignore
# These are Ad Tech infrastructure only (Cookie matching, Header bidding)
# ══════════════════════════════════════

AD_TECH_DOMAINS = [
    # Cookie Syncing / DMPs
    "deepintent.com", "match.deepintent.com",
    "srv.stackadapt.com", "sync.srv.stackadapt.com",
    "smartadserver.com", "ssbsync.smartadserver.com",
    "rtb-csync.smartadserver.com",
    "sync.taboola.com", "trc.taboola.com",
    "us-vid-events.taboola.com", "us-wf.taboola.com",
    "adform.net", "c1.adform.net",
    "id5-sync.com",
    "adsrvr.org", "match.adsrvr.org",
    "adnxs.com", "secure.adnxs.com",
    "b1sync.outbrain.com",
    "ssp.disqus.com",
    "bfmio.com", "sync.bfmio.com",
    "360yield.com", "ad.360yield.com",
    "sonobi.com", "sync.go.sonobi.com",
    "3lift.com", "tlx.3lift.com", "eb2.3lift.com",
    "onetag-sys.com",
    "ce.lijit.com",
    "admanmedia.com", "cs.admanmedia.com",
    
    # Header Bidding / SSPs
    "rubiconproject.com", "fastlane.rubiconproject.com",
    "criteo.com", "gum.criteo.com",
    "brainlyads.com", "report2.hb.brainlyads.com",
    "doubleclick.net", "securepubads.g.doubleclick.net",
    "googletagmanager.com", "google-analytics.com",
    "googlesyndication.com",
    
    # Analytics / Tracking pixels (not affiliate)
    "profitorapi.com", "trk.profitorapi.com",
    "clarity.ms", "c.clarity.ms",
    "bing.com",
    "facebook.com/tr",
    "connect.facebook.net",
    "trc-events.taboola.com",
    "id-msp.newsbreak.com",
    "business.newsbreak.com",
    "ads.rmbl.ws",
    "cdn-cgi/rum",
    
    # CDN / Static Assets
    "cdn.taboola.com",
    "images.taboola.com",
    "cloudfront.net",
    "fastly.net",
    "googleapis.com",
    "fonts.gstatic.com",
    "g.doubleclick.net"
]

# ══════════════════════════════════════
# BLACKLIST: Intermediary Ad Network Click Trackers
# ══════════════════════════════════════
INTERMEDIARY_DOMAINS = [
    "revcontent.com", "smeagol.revcontent.com",
    "idealmedia.io", "clck.idealmedia.io",
    "mgid.com", "clck.mgid.com", "adskeeper.co.uk", "clck.adskeeper.com",
    "taboola.com", "trc.taboola.com",
    "outbrain.com", "traffic.outbrain.com", "paid.outbrain.com",
    "yahoo.com/p?prd=",
]

# ══════════════════════════════════════
# BLACKLIST B: URL Patterns to ignore
# Match against full URL string
# ══════════════════════════════════════

AD_TECH_URL_PATTERNS = [
    # Cookie sync patterns
    "/usersync/", "/sync?", "/cookie_sync",
    "/user_sync", "/usermatch", "/getuid",
    "/redirectuser", "taboola_hm=",
    "gdpr_consent=", "/rtb-h/",
    
    # Header bidding patterns
    "/header/auction", "/OpenRTB/",
    "/fastlane.json", "/prebid-request",
    "/gampad/ads", "/pcs/view",
    "pbjs", "prebid", "hb_bidder",
    
    # Analytics patterns
    "event=bidRequested", "event=pv",
    "event=no_fill", "site/events",
    
    # Static assets
    ".jpg", ".jpeg", ".png", ".gif", ".svg",
    ".css", ".js", ".woff", ".woff2",
    "/wp-content/uploads/",
    "/libtrc/static/thumbnails/",
    "image/fetch/",
]

# ══════════════════════════════════════
# WHITELIST: Patterns that are ALWAYS meaningful
# (Priority override for long URLs)
# ══════════════════════════════════════

AFFILIATE_SIGNATURES = [
    "lptoken=", "clickid=", "subid=", "affid=", "hop=", 
    "utm_campaign=", "utm_content=", "cep=", "widget_id=", 
    "content_id=", "boost_id=", "click_id=", "affiliate_id=",
    "offer_id=", "cbid=", "tblci=", "ob_click_id=",
    "aff_id", "aff_click_id", "req_id", "sub1", "sub2", "transaction_id"
]

def is_meaningful_url(url: str) -> bool:
    """
    Returns True ONLY if URL could be an affiliate link.
    Returns False for all ad tech infrastructure / static assets.
    """
    from urllib.parse import urlparse
    
    if not url or not url.startswith("http"):
        return False
        
    url_lower = url.lower()

    # RULE 0: PRIORITY OVERRIDE
    # If it has affiliate patterns, it's meaningful regardless of length or domain
    if any(sig in url_lower for sig in AFFILIATE_SIGNATURES):
        return True

    # Rule 3: Skip very long URLs (ad tech tends to be huge)
    if len(url) > 800:
        return False
        
    url_lower = url.lower()
    parsed = urlparse(url_lower)
    domain = parsed.netloc
    
    # Rule 1: Check domain blacklist
    for blocked_domain in AD_TECH_DOMAINS:
        if blocked_domain in domain:
            return False
            
    # Rule 2: Check URL pattern blacklist
    for pattern in AD_TECH_URL_PATTERNS:
        if pattern in url_lower:
            return False
    
    return True

def is_intermediary_domain(url: str) -> bool:
    """Returns True if the URL is an ad network click tracker (e.g. revcontent.com, clck.mgid.com)."""
    if not url: return False
    from urllib.parse import urlparse
    domain = urlparse(url.lower()).netloc
    for intermediary in INTERMEDIARY_DOMAINS:
        if intermediary in domain:
            return True
    return False
    
