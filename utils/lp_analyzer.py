import asyncio
import random
import re
from urllib.parse import urlparse
from utils.popup_handler import dismiss_popups
from utils.cloak_detector import detect_cloaking
from utils.url_blacklist import is_meaningful_url, is_intermediary_domain, AFFILIATE_SIGNATURES
from utils.url_resolver import resolve_real_url, is_tracking_redirect
import base64
import json
from urllib.parse import urlparse, parse_qs, unquote

# Bug 1 Fix: Offline-safe domain extractor (no DNS/network calls)
def _extract_domain(url: str) -> str:
    """Extract registered domain safely, no network I/O, compatible with all tldextract versions."""
    if not url: return ""
    try:
        import tldextract as _tldm
        try:
            _ext = _tldm.TLDExtract(suffix_list_urls=[])
        except TypeError:
            try:
                _ext = _tldm.TLDExtract(fetch=False)
            except TypeError:
                _ext = _tldm.TLDExtract()
        result = _ext(url)
        if result.registered_domain:
            return result.registered_domain
    except Exception:
        pass
    try:
        netloc = urlparse(url).netloc.lower().split(":")[0]
        return netloc[4:] if netloc.startswith("www.") else netloc
    except Exception:
        return ""

# Bug 5: Domains that cause timeouts or are never affiliate offers
FAST_SKIP_DOMAINS = [
    "independent.co.uk",
    "the-independent.com",
    "viewitquickly.online",
    "go.viewitquickly.online",
    "goodrx.com",
    "rocketmortgage.com",
    "blog.ring.com",
    "ring.com/blog",
    "ancestry.com",
    "barkbox.com",
    "nerdwallet.com",
    "lendingtree.com",
    "profitorapi.com",
    "landerlab.io",
    "track.landerlab.io",
    "analytics.google.com",
    "brainberries.co",
    "herbeauty.co",
    "vsn.ua",
    "goodrx.com",
    "rocketmortgage.com",
    "ring.com",
    "ancestry.com",
    "barkbox.com",
]

CLOUDFLARE_INDICATORS = [
    "challenges.cloudflare.com",
    "cdn-cgi/challenge",
    "Just a moment",           # Cloudflare page title
    "Please wait while we",    # Cloudflare text
    "Checking your browser",   # Cloudflare text
    "DDoS protection by",      # Cloudflare footer
    "Ray ID:",                 # Cloudflare error ID
    "cf-browser-verification", # Cloudflare class
]

def extract_hidden_voluum_offer(url: str):
    """Decodes Voluum Base64 tracking data to find the hidden offer URL."""
    if "voluumdata=" in url:
        try:
            encoded_part = url.split("voluumdata=")[1].split("&")[0]
            # Handle potential padding issues
            missing_padding = len(encoded_part) % 4
            if missing_padding:
                encoded_part += '=' * (4 - missing_padding)
            decoded_str = base64.b64decode(unquote(encoded_part)).decode('utf-8')
            data = json.loads(decoded_str)
            return data.get("offer")
        except:
            return None
    return None

TECHNICAL_NOISE_DOMAINS = [
    "vturb.com.br",    # Video player service
    "api.vturb.com",   # Vturb API
    "djpcraze.com",    # Tracking SDK
    "hotmart.com/embed", # Hotmart video player
    "vimeo.com",
    "cloudfront.net",
    "amazonaws.com",
    "doubleclick.net",
    "google-analytics.com",
    "googletagmanager.com",
    "bluekai.com",
    "adnxs.com",
    "permutive.com",
    "ml314.com",
    "newsroom.bi",
    "tr.outbrain.com",
    "trc.dailylifeinsider.com",
    "hcaptcha.com",
    "recaptcha.net",
    # Production run 2026-05-01: incorrectly captured as background offers
    "a.vturb.net",      # Video CDN endpoint, not an offer
    "vturb.net",
    "youtube.com",       # generate_204 tracking pixel
    "converteai.net",    # Video player SaaS platform
    "c.mgid.com",
    "la-wf.taboola.com",
    "fundingchoicesmessages.google.com",
    "landerlab.io",
    "track.landerlab.io"
]

def get_best_offer_link(links: list) -> str:
    """Filters a list of links and picks the best candidate for an offer URL."""
    from utils.url_blacklist import is_valid_offer_url
    valid_links = []
    for link in links:
        if not link: continue
        l_lower = link.lower()
        
        # 1. Skip technical noise & bot protection
        if any(noise in l_lower for noise in TECHNICAL_NOISE_DOMAINS):
            continue
            
        # 2. Skip obvious technical endpoints via global validator (Bug 2)
        if not is_valid_offer_url(link):
            continue
            
        valid_links.append(link)
    
    if not valid_links:
        return None
    
    # Prefer longest URL as it likely contains the most tracking data
    return max(valid_links, key=len)

def extract_target_from_params(url: str, depth: int = 0) -> str:
    """Attempts to recursively find a destination URL hidden in query parameters (max depth 3)."""
    if not url or depth > 3: return url
    target = None
    
    # Check for hidden Voluum data first
    voluum_offer = extract_hidden_voluum_offer(url)
    if voluum_offer:
        # Recurse on the extracted offer
        return extract_target_from_params(voluum_offer, depth + 1)

    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        # Common 'destination' parameter names for trackers
        dest_params = [
            "requestUrl", "dest", "url", "u", "target", "redirect", "destination",
            "caller_url", "return_url", "final_url", "goto", "next", "landing",
            "event_source_url", "r", "to", "link", "orig", "origin", "src"
        ]
        for p in dest_params:
            if p in params and params[p]:
                target = unquote(params[p][0])
                if target.startswith("http") and target != url:
                    # RECURSIVE: Check if the extracted URL also has a target
                    deeper = extract_target_from_params(target, depth + 1)
                    if deeper != target:
                        return deeper
                    return target
    except: pass
    
    # Validation: Only return if the extracted target is meaningful
    if target and target.startswith("http") and is_meaningful_url(target):
        return target
        
    return url

def is_api_endpoint(url):
    """Returns True if the URL looks like an API/analytics/sync endpoint."""
    if not url: return True
    u = url.lower()
    path = urlparse(u).path
    api_patterns = [
        "/api/", "/v2/", "/v1/", "/v3/", "/internal/", "/metrics",
        "/sync", "/imsync", "/usersync", "/ingest", "/ingest.php",
        "/analytics", "/collect", "/pixel", "/beacon",
        "/track", "/tracker", ".ashx", "permutive.com", "ml314.com", "newsroom.bi",
        "/log?", "collect?", "/events?", "/sdk/", "/conversion", "/check",
        "/vturb/", "/player/", "taboola.com/libtrc/", "/notify", "/ping",
        "cachedclickid", "marketerid", "hcaptcha", "recaptcha",
        "fpjs.io", "ip-api.com"
    ]
    # Check both path and full URL for some specific trackers
    tracking_domains = ["ml314.com", "permutive.com", "newsroom.bi", "vturb.com.br", "djpcraze.com", "bluekai.com", "adnxs.com"]
    return any(p in u for p in api_patterns) or any(d in u for d in tracking_domains)

def extract_affiliate_from_html(html: str, base_url: str = None) -> str:
    """
    HTML-FIRST APPROACH:
    Scan page HTML for affiliate destination URLs. Resolves relative links.
    """
    if not html: return ""
    from urllib.parse import urljoin
    
    # 1. Find all potential URLs (full and relative via href)
    # Regex for full URLs
    full_url_pattern = r"https?://[^\s\"'<>\)\\]+"
    all_urls = set(re.findall(full_url_pattern, html))
    
    # Regex for href attributes (captures relative links like click/1)
    href_pattern = r"href=[\"']([^\"']+)[\"']"
    hrefs = re.findall(href_pattern, html)
    for h in hrefs:
        if base_url:
            all_urls.add(urljoin(base_url, h))
        else:
            if h.startswith("http"):
                all_urls.add(h)

    best_url = ""
    base_domain = _extract_domain(base_url) if base_url else ""
    for url in all_urls:
        url = url.rstrip(".,;)")
        url_lower = url.lower()
        
        # CRITICAL: Skip self-referencing URLs from the same domain
        # e.g. wellnesswiredaily.com/click/1 when base is wellnesswiredaily.com
        url_domain = _extract_domain(url)
        if base_domain and url_domain == base_domain:
            continue
        
        # Check against signatures
        if not any(sig in url_lower for sig in AFFILIATE_SIGNATURES):
            continue
            
        # Filter noise
        if is_api_endpoint(url) or not is_meaningful_url(url):
            continue
            
        skip_domains = [
            "google-analytics", "googletagmanager", "doubleclick",
            "facebook.com/tr", "clickbank.net/sellerhop",
            "tracking.buygoods", "cbtb.clickbank",
            "ml314.com", "permutive.com", "newsroom.bi"
        ]
        if any(sd in url_lower for sd in skip_domains):
            continue
            
        # Priority mapping
        priority_paths = ["/pay/", "/order/", "/checkout/", "/vsl", "/video/", "/buy", "/click?", "click/"]
        if any(p in url_lower for p in priority_paths):
            return url
            
        if not best_url:
            best_url = url
            
    return best_url

async def wait_for_actual_landing(page, max_wait=15000):
    """Waits for network to settle, excluding tracker redirects."""
    try:
        await asyncio.wait_for(
            page.wait_for_load_state("networkidle", timeout=max_wait),
            timeout=float(max_wait/1000) + 2.0
        )
        # Extra wait if we are still on a known tracker/intermediary - max 5s
        waited = 0
        while is_intermediary_domain(page.url) and waited < 5000:
            print(f"Waiting for redirect from intermediary: {page.url}")
            await asyncio.sleep(1.0)
            waited += 1000
    except: pass

EXCLUDED_CTA_PATTERNS = [
    "disclaimer", "privacy policy", "terms of service", "terms & conditions",
    "cookie policy", "about us", "contact us", "sitemap", "legal",
    "©", "copyright", "unsubscribe", "do not sell", "manage preferences",
    "mentions légales", "politique de confidentialité", "conditions générales"
]

def is_valid_cta(element_text: str) -> bool:
    """Returns True if the element text doesn't match excluded patterns (Bug 5)."""
    text_lower = element_text.lower().strip()
    if not text_lower: return False
    return not any(pattern in text_lower for pattern in EXCLUDED_CTA_PATTERNS)

async def click_cta_and_capture(page, ad_type: str = "Affiliate") -> dict:
    """
    Clicks the CTA button and captures the full redirect chain.
    Enhanced with Deep Navigation to bypass cloaking.
    """
    from utils.deep_navigator import find_real_offer_deep
    
    # Extract title if available, otherwise empty
    try:
        title = await page.title()
    except Exception:
        title = ""
        
    deep_result = await find_real_offer_deep(
        page=page,
        landing_url=page.url,
        ad_title=title
    )
    
    final_offer_url = deep_result.get("final_url")
    redirect_chain = deep_result.get("clean_chain", [])
    
    return {
        "cta_found": deep_result.get("success", False),
        "cta_text": deep_result.get("cta_text", "Unknown"),
        "final_offer_url": final_offer_url,
        "redirect_chain": redirect_chain
    }

async def analyze_page_structure(page) -> dict:
    """Detects pagination, galleries, and high ad density."""
    try:
        content = await page.content()
        url = page.url.lower()
        
        # Pagination indicators
        pagination_selectors = [".pagination", ".next-page", ".slideshow-nav", "[class*='pagination']", "[class*='next']"]
        is_paginated = False
        for sel in pagination_selectors:
            try:
                if await page.query_selector(sel):
                    is_paginated = True
                    break
            except: pass
            
        # Ad container signatures
        ad_selectors = [
            "[id*='google_ads']", ".adsbygoogle", "[id*='taboola']", "[id*='outbrain']",
            "[class*='taboola']", "[class*='outbrain']", "[class*='revcontent']",
            ".adsbygoogle", "[class*='dfp']"
        ]
        ad_count = 0
        for sel in ad_selectors:
            try:
                nodes = await page.query_selector_all(sel)
                ad_count += len(nodes)
            except: pass
            
        is_wordpress = "/wp-content/" in content or "wp-json" in content
        has_comments = "disqus" in content or "fb-comments" in content
        
        page_type_guess = "unknown"
        if is_paginated: page_type_guess = "slideshow_arbitrage"
        elif ad_count >= 3: page_type_guess = "article_arbitrage"
        
        return {
            "is_paginated": is_paginated,
            "high_ad_density": ad_count >= 3,
            "ad_count": ad_count,
            "is_wordpress": is_wordpress,
            "is_clickbait": any(k in url for k in ["trending", "believe", "defying", "celebrities"]),
            "has_comments": has_comments,
            "page_type_guess": page_type_guess
        }
    except: return {}

async def wait_for_actual_landing(page, timeout=10000):
    """Wait for the page to settle on a non-intermediary URL."""
    try:
        # Increase settle time for network-heavy pages
        await page.wait_for_load_state("networkidle", timeout=timeout)
    except:
        pass
    
    waited = 0
    while is_intermediary_domain(page.url) and waited < 5000:
        await asyncio.sleep(1.0)
        waited += 1000
    return page.url

async def capture_network_intelligence(page) -> dict:
    """
    Scans background network requests and JS context for affiliate signals.
    """
    intel = {
        "detected_trackers": [],
        "potential_offers": [],
        "js_vars": {}
    }
    
    # 1. Capture common affiliate JS variables
    js_script = """
    () => {
        return {
            voluum_cid: window.__vl_cid || null,
            everflow_ef: window.EF || null,
            binom_id: window.binom_click_id || null,
            clickbank_split: window.cbsplit || null,
            tune_tfa: window._tfa || null,
            cake_id: window.cake_id || null
        }
    }
    """
    try:
        intel["js_vars"] = await page.evaluate(js_script)
    except: pass

    return intel

async def analyze_landing_page_with_page(page, url: str) -> dict:
    """Analyzes a landing page using an existing Playwright page object."""
    result = {
        "final_offer_url": None,
        "page_subtype": "Unknown",
        "has_countdown": False,
        "has_video": False,
        "price_found": None,
        "cta_text": None,
        "cloaking": {},
        "popups": {},
        "text_content": "",
        "full_html": ""
    }

    # QUICK SKIP for known heavy Arbitrage sites we want to avoid
    if "independent.co.uk" in url or "the-independent.com" in url:
        print(f"  [Ad] Skipping {url} (Known Arbitrage/Heavy site per request)")
        return {
            "final_offer_url": url,
            "text_content": "Skipped per user request",
            "full_html": "Skipped",
            "page_subtype": "Advertorial",
            "background_offers": [],
            "clean_redirect_chain": []
        }

    # AD SERVER EXTRACTION: Before analyzing, check if it's an ad server wrapper (Bug 4)
    from utils.url_resolver import extract_real_url_from_ad_server
    real_url = extract_real_url_from_ad_server(url)
    if real_url != url:
        print(f"  [Ad Server] De-wrapped {url[:40]}... -> {real_url[:40]}...")
        url = real_url

    # Bug 5: Fast-skip known non-affiliate / timeout-causing domains
    for skip_domain in FAST_SKIP_DOMAINS:
        if skip_domain in url.lower():
            print(f"  [Ad] Fast-skip: {url} ({skip_domain})")
            return {
                "final_offer_url": url,
                "text_content": "Fast-skipped (known non-affiliate domain)",
                "full_html": "",
                "page_subtype": "Arbitrage",
                "background_offers": [],
                "clean_redirect_chain": [],
                "page_structure": {},
                "fast_skip": True,
                "skip_reason": skip_domain
            }

    try:
        # Handle Initial Page Load
        try:
            # We already navigated in the outer scope, but if we extracted a NEW URL from ad-server, go there
            if url != page.url:
                await asyncio.wait_for(page.goto(url, wait_until="domcontentloaded", timeout=30000), timeout=35.0)
            
            # Check for Cloudflare Block (Bug 3)
            page_title = await asyncio.wait_for(page.title(), timeout=10.0)
            page_content = await asyncio.wait_for(page.content(), timeout=15.0)
            if any(ind in page.url or ind in page_title or ind in page_content for ind in CLOUDFLARE_INDICATORS):
                print(f"  ⚠️ Cloudflare challenge detected for {url}")
                await asyncio.sleep(5.0)
                await asyncio.wait_for(page.reload(wait_until="domcontentloaded"), timeout=20.0)
                await asyncio.sleep(2.0)
                
                # Check again
                if any(ind in page.url or ind in page_title or ind in await asyncio.wait_for(page.content(), timeout=15.0) for ind in CLOUDFLARE_INDICATORS):
                    print(f"  ❌ Cloudflare blocked — saving with flag")
                    return {
                        "final_offer_url": None,
                        "cloudflare_blocked": True,
                        "needs_manual_review": True,
                        "landing_url": url,
                        "error": "cloudflare_bot_challenge"
                    }
                else:
                    print(f"  ✅ Cloudflare challenge auto-solved!")

            # Normal analysis continues...
            await asyncio.wait_for(page.wait_for_load_state("domcontentloaded", timeout=10000), timeout=15.0)
        except Exception as e:
            print(f"  [Ad] Navigation warning for {url}: {e}")
        
        clean_redirect_chain = []
        original_reg_domain = _extract_domain(url)

        def handle_response(response):
            try:
                r_url = response.url
                status = response.status
                if not is_meaningful_url(r_url): return
                if is_api_endpoint(r_url): return
                if status < 200 or status >= 400: return
                url_domain = _extract_domain(r_url)
                if url_domain == original_reg_domain: return
                if r_url not in clean_redirect_chain: clean_redirect_chain.append(r_url)
            except: pass
            
        page.on("response", handle_response)
        
        background_offers = []
        network_intel = {"detected_trackers": [], "potential_offers": [], "js_vars": {}}
    
        # Listen for background requests that look like affiliate offers
        async def on_request(request):
            try:
                req_url = request.url
                # 1. Skip technical noise
                if any(noise in req_url for noise in TECHNICAL_NOISE_DOMAINS):
                    return
                
                # 2. Search for affiliate signals
                affiliate_signals = ['hopid', 'affiliate', 'aff_id', 'clickid', 'tid', 'extclid', 'click_id', 'offer_id']
                if any(sig in req_url.lower() for sig in affiliate_signals):
                    if req_url not in background_offers:
                        background_offers.append(req_url)
            except: pass

        page.on("request", on_request)

        # 0. AGGRESSIVE RESOURCE BLOCKING
        async def block_aggressively(route):
            try:
                bad_types = ["image", "media", "font", "stylesheet"]
                if route.request.resource_type in bad_types:
                    return await route.abort()
                
                url_lower = route.request.url.lower()
                bad_patterns = [".png", ".jpg", ".jpeg", ".gif", ".webp", ".css", ".woff", "google-analytics", "googletagmanager", "doubleclick", "facebook.net"]
                if any(p in url_lower for p in bad_patterns):
                    return await route.abort()
                
                await route.continue_()
            except: pass

        await page.route("**/*", block_aggressively)

        # HARD SAFETY NET
        try:
            print(f"  [Ad] Starting fast-navigation to {url}...", flush=True)
            await asyncio.wait_for(
                page.goto(url, wait_until="domcontentloaded", timeout=45000),
                timeout=50.0
            )
        except:
            print(f"  ⚠️ Timeout/Error during goto for {url}, proceeding with what we have.")
            
        # Increase settle time for network-heavy pages
        await asyncio.sleep(4.0)
        
        # Remove routing for the rest of the analysis
        await page.unroute("**/*", block_aggressively)
        
        # Capture network and JS intelligence
        network_intel = await capture_network_intelligence(page)
        
        final_url = await wait_for_actual_landing(page, 10000)
        
        await page.mouse.wheel(0, 500)
        await asyncio.sleep(1.0)

        # 2. Extract Data
        try: result["popups"] = await asyncio.wait_for(dismiss_popups(page), timeout=20.0)
        except: result["popups"] = {}
        
        try: content = await asyncio.wait_for(page.content(), timeout=15.0)
        except: content = ""
        
        try: text_content = await asyncio.wait_for(page.evaluate("document.body.innerText"), timeout=15.0)
        except: text_content = ""
        
        result["text_content"] = text_content
        result["full_html"] = content
        
        try: has_video = bool(await asyncio.wait_for(page.query_selector("video"), timeout=5.0) or "youtube.com/embed" in content)
        except: has_video = False
        result["has_video"] = has_video
        
        try: has_countdown = bool(await asyncio.wait_for(page.query_selector("[class*='timer'], [id*='timer']"), timeout=5.0))
        except: has_countdown = False
        result["has_countdown"] = has_countdown

        if any(k in text_content.lower() for k in ["add to cart", "buy now", "order now"]):
            result["page_subtype"] = "Direct Sales"
        elif "advertorial" in content.lower():
            result["page_subtype"] = "Advertorial"

        # 3. Final Offer Selection Logic
        best_bg_offer = get_best_offer_link(background_offers)
        html_aff = extract_affiliate_from_html(content, page.url)
        
        if best_bg_offer:
            result["final_offer_url"] = best_bg_offer
        elif html_aff:
            print(f"HTML-First Match: {html_aff[:80]}")
            result["final_offer_url"] = html_aff
        else:
            candidate = extract_target_from_params(page.url)
            if is_meaningful_url(candidate) and not is_api_endpoint(candidate):
                result["final_offer_url"] = candidate
            else:
                for r_url in reversed(clean_redirect_chain):
                    if is_meaningful_url(r_url):
                        result["final_offer_url"] = r_url
                        break

        result["cloaking"] = detect_cloaking(url, result["final_offer_url"], clean_redirect_chain)
        result["page_structure"] = await analyze_page_structure(page)
        result["clean_redirect_chain"] = clean_redirect_chain

    except Exception as e:
        print(f"LP Analysis Error for {url}: {e}")
    finally:
        # Bug 4: Proper cleanup in finally block
        try:
            page.remove_listener("response", handle_response)
            page.remove_listener("request", on_request)
            await page.unroute("**/*", block_aggressively)
        except: pass

    # Capture final HTML for classification
    try:
        final_html = await asyncio.wait_for(page.content(), timeout=10.0)
    except:
        final_html = ""

    # Add background discoveries to intelligence
    result.update({
        "background_offers": background_offers,
        "network_intel": network_intel,
        "full_html": final_html
    })

    return result
