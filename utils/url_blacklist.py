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
    "g.doubleclick.net",
    "converteai.net",
    "customer-f8ksu.cloudflarestream.com",
    "videodelivery.net",
    "google.co.ma", "adservice.google.com", "bidswitch.net", "x.bidswitch.net",
    "analytics.twitter.com", "analytics.google.com", "pixel.facebook.com"
]

# ══════════════════════════════════════
# BLACKLIST: HARD BLOCKS (Never meaningful as final offers)
# If a URL originates from these domains, it is DISQUALIFIED.
# ══════════════════════════════════════

STRICT_BLOCK_DOMAINS = [
    "google-analytics.com", "analytics.google.com", "googletagmanager.com",
    "google.com", "facebook.com", "twitter.com", "linkedin.com", "bing.com",
    "clarity.ms", "doubleclick.net", "adservice.google", "bidswitch",
    "posthog.com", "hotjar.com", "newrelic.com", "nr-data.net",
    "sellerhop", "trusted-badge",
    "hcaptcha.com", "recaptcha.net", "tr.outbrain.com", "trc.dailylifeinsider.com",
    "api.hcaptcha.com", "api.recaptcha.net",
    # ClickBank infrastructure (NOT checkout pages)
    "cbtb.clickbank.net", "hop.clickbank.net",
    # Support / SaaS widgets (never final offers)
    "zendesk.com", "intercom.io", "tawk.to", "crisp.chat",
    # CDN / media delivery
    "b-cdn.net", "bunnycdn.com",
    # Nonprofit / donation tracking
    "everyaction.com", "actionnetwork.org",
    # Checkout platform APIs (backend, not landing pages)
    "checkoutchamp.com",
    # Affiliate click trackers (intermediate, not merchant pages)
    "tracking.buygoods.com", "track.buygoods.com",
    "go2cloud.org", "go2jump.org",  # Commission Junction trackers
    "pntra.com", "pntat.com",       # Other CJ tracker domains
    "ml314.com", "permutive.com", "newsroom.bi", "news-feed.com",
    "us-wf.taboola.com", "cmpv2.independent.co.uk", "adtrafficquality.google",
    "live.primis.tech", "trk-adv.rixbeedesk.com", "tealiumiq.com", "freshchat.com"
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
    "trkerupper.com", "clktrservices.com", "clktrack.com",
    "be-mob.com", "bemob.com", "trk.healthyinsightjournal.com",
    "tr.outbrain.com", "trc.dailylifeinsider.com"
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
    
    # Static assets / Media streams
    ".jpg", ".jpeg", ".png", ".gif", ".svg",
    ".css", ".js", ".woff", ".woff2",
    ".ts", ".m3u8", ".mp4", ".mp3", ".webm",
    "/wp-content/uploads/",
    "/libtrc/static/thumbnails/",
    "image/fetch/",
    "/sellerhop?", "/trusted-badge/", "/pixel/register/trigger/",
    "analytics.google.com/g/collect", "events.devcycle.com",
    "us.i.posthog.com", "bam.nr-data.net",
    "/tr/", "/collect?", "/pixel?", "/track?", "/log?", "/events?",
    "/Track/", "/providersApi/", "/embeddable/config",
    "/cdn-cgi/",  # Cloudflare RUM / monitoring endpoints
    "cachedClickId", "marketerId", "/view?clickid=", "hcaptcha", "recaptcha", "getcaptcha",
    "VideoBidRequestHandlerServlet", "liveVideo.php", "/report?tntId="
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
    "aff_id", "aff_click_id", "req_id", "sub1", "sub2", "sub3", "transaction_id",
    "voluumdata=", "voluum", "bsl=", "click/", "/click?", "/outgoing", "/goto/", "/redir/",
    "track.", "clck."
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

    # RULE -1: SKIP LIST (Arbitrage sources we don't want to re-process)
    SKIP_ANALYSIS_DOMAINS = ["independent.co.uk", "the-independent.com"]
    for skipped in SKIP_ANALYSIS_DOMAINS:
        if skipped in url_lower:
            # Check if it's the main domain (not a parameter)
            if url_lower.startswith(f"https://{skipped}") or url_lower.startswith(f"http://{skipped}") or f".{skipped}" in url_lower:
                 # Logic for skipping could be added here if we wanted to abort analysis
                 pass

    # RULE 0: ABSOLUTE MEDIA/STATIC BLOCK
    # Media segments and static assets are NEVER meaningful offer destinations
    media_exts = [".ts", ".m3u8", ".mp4", ".mp3", ".webm", ".jpg", ".jpeg", ".png", ".gif", ".svg", ".css", ".js", ".woff", ".woff2", ".ico"]
    if any(ext in url_lower for ext in media_exts):
        return False

    url_lower = url.lower()
    parsed = urlparse(url_lower)
    domain = parsed.netloc
    
    # RULE 0: ATOMIC BLACKLIST (STRICT DOMAIN BLOCK)
    # These domains never represent a final affiliate offer.
    for blocked in STRICT_BLOCK_DOMAINS:
        if blocked in domain or blocked in url_lower:
            return False

    # RULE 1: AD TECH BLOCK (Pattern & Domain)
    # This MUST come before signatures because pixels often echo page parameters
    for blocked_domain in AD_TECH_DOMAINS:
        if blocked_domain in domain:
            return False
            
    for pattern in AD_TECH_URL_PATTERNS:
        if pattern in url_lower:
            return False

    # RULE 2: PRIORITY OVERRIDE (Affiliate detection)
    # If it survived the blacklist, then signatures make it meaningful
    if any(sig in url_lower for sig in AFFILIATE_SIGNATURES):
        return True

    # Rule 3: Skip very long URLs (ad tech tends to be huge)
    if len(url) > 800:
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
    
