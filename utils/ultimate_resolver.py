import re, httpx, asyncio, random, json
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote
from playwright.async_api import async_playwright, Error as PlaywrightError

# Import existing utilities
from utils.url_blacklist import is_valid_offer_url, is_ad_tech_url, is_prelander_domain, is_intermediary_domain
from utils.offer_validator import check_url_health
from utils.ghost_browser import get_profile
from utils.offer_extractor import extract_revcontent_app_config
from utils.url_resolver import resolve_forensically_async

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# BROWSER MANAGEMENT WITH RESILIENCE
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

class BrowserSession:
    """Manages browser lifecycle with automatic recovery and request interception."""
    def __init__(self, playwright_instance, profile):
        self.p = playwright_instance
        self.profile = profile
        self.browser = None
        self.context = None
        self.page = None
        self.is_closed = False

    async def ensure_active(self):
        """Ensures the browser and page are open and responsive."""
        if self.is_closed:
            raise RuntimeError("Session marked as closed")
            
        if not self.browser or not self.browser.is_connected():
            print("  [Browser] Launching browser...")
            # Check CloakBrowser binary path
            cloak_binary = None
            try:
                from cloakbrowser._binary import get_binary_path
                cloak_binary = get_binary_path()
            except: pass
            
            launch_kwargs = {
                "headless": True,
                "args": [
                    "--no-sandbox",
                    "--disable-dev-shm-usage",
                    "--disable-blink-features=AutomationControlled",
                    f"--window-size={self.profile['viewport']['width']},{self.profile['viewport']['height']}",
                ]
            }
            if cloak_binary: launch_kwargs["executable_path"] = cloak_binary
            
            self.browser = await self.p.chromium.launch(**launch_kwargs)
            self.context = None 
            
        if not self.context:
            print("  [Browser] Creating new context...")
            self.context = await self.browser.new_context(
                user_agent=self.profile["user_agent"],
                viewport=self.profile["viewport"],
                locale=self.profile["locale"],
                timezone_id=self.profile["timezone"],
                extra_http_headers={"Accept-Language": self.profile["accept_language"]}
            )
            # Enable Request Interception for performance
            await self.context.route("**/*", self._intercept_requests)
            self.page = None 
            
        if not self.page or self.page.is_closed():
            print("  [Browser] Opening new page...")
            self.page = await self.context.new_page()
            
        return self.page

    async def _intercept_requests(self, route):
        """Blocks media and ad-tech domains to speed up resolution."""
        url = route.request.url.lower()
        
        # 1. Block media types (images, videos, fonts)
        MEDIA_EXTS = [".png", ".jpg", ".jpeg", ".gif", ".svg", ".webp", ".mp4", ".woff", ".woff2", ".ttf", ".ico"]
        if any(url.endswith(ext) for ext in MEDIA_EXTS) or any(ext + "?" in url for ext in MEDIA_EXTS):
            return await route.abort()
            
        # 2. Block infrastructure and ad-tech (centralized in url_blacklist)
        if is_ad_tech_url(url) or any(d in url for d in ["google-analytics", "googletagmanager", "facebook.net", "doubleclick.net"]):
            return await route.abort()
            
        await route.continue_()

    async def close(self):
        """Gracefully closes all resources."""
        self.is_closed = True
        try:
            if self.browser:
                await self.browser.close()
        except: pass

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAYER 0: Mandatory Surface Scan (Simple-First)
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def layer0_simple_mandatory_scan(html: str, base_url: str) -> str | None:
    """
    Rapidly scans HTML for obvious affiliate/offer links.
    Incorporates logic from the 'Simple Extraction Tool' (Layer 0).
    Zero network overhead. Prevents over-calculation fatigue.
    """
    if not html: return None
    
    soup = BeautifulSoup(html, "html.parser")
    
    # 1. Patterns from the Simple Tool
    COMMON_PATTERNS = [
        'a[data-offer]', '.offer-link', '.deal-link', '[href*="offer"]',
        '[href*="deal"]', '[href*="promo"]', '[href*="aff"]', '.btn-offer',
        '.affiliate-link', '.product-link', 'a[href*="click"]', '.cta-button',
        '.buy-button', '.shop-now', '.get-deal', '.get-offer', '.claim-btn',
        '.claim-offer', '.discount-link'
    ]
    
    # 2. Offer Keywords for Validation (from Simple Tool's isValidOfferUrl)
    OFFER_KEYWORDS = [
        'offer', 'deal', 'promo', 'aff', 'click', 'ref', 'link', 
        'product', 'buy', 'shop', 'checkout', 'cart', 'order', 
        'sale', 'discount'
    ]
    
    from utils.url_blacklist import AFFILIATE_SIGNATURES, is_ad_tech_url
    
    candidates = []
    seen_urls = set()
    
    # First pass: Check known patterns (High Confidence)
    for pattern in COMMON_PATTERNS:
        try:
            elements = soup.select(pattern)
            for el in elements:
                href = el.get("href", "").strip()
                if not href or not href.startswith("http") or href in seen_urls: continue
                if is_ad_tech_url(href): continue
                
                # Check for affiliate signatures in URL
                score = 10 if any(sig.lower() in href.lower() for sig in AFFILIATE_SIGNATURES) else 5
                candidates.append((href, score, pattern))
                seen_urls.add(href)
        except: continue

    # Second pass: Fallback to all links with keywords
    if not candidates:
        for a in soup.find_all("a", href=True):
            href = a.get("href", "").strip()
            if not href or not href.startswith("http") or href in seen_urls: continue
            if is_ad_tech_url(href): continue
            
            # Check keywords in URL path/search
            path_lower = href.lower()
            if any(kw in path_lower for kw in OFFER_KEYWORDS):
                candidates.append((href, 3, "generic_keyword"))
                seen_urls.add(href)
            elif "=" in href and len(href) > 25: # Potential tracking URL
                candidates.append((href, 2, "potential_tracker"))
                seen_urls.add(href)

    if candidates:
        # Sort by score (High confidence first)
        candidates.sort(key=lambda x: x[1], reverse=True)
        best_url, best_score, source = candidates[0]
        
        # Mandatory Protocol: If score is high, it's the "Golden Link"
        if best_score >= 8:
            print(f"  [L0] Golden Link found via {source}: {best_url[:60]}")
            return best_url
        
        # If moderate confidence, return the best one found
        print(f"  [L0] Moderate candidate found ({source}): {best_url[:60]}")
        return best_url
        
    return None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAYER 1: HTML Static Extraction
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def layer1_static_extraction(html: str, base_url: str) -> str | None:
    """
    BeautifulSoup4 scans raw HTML for offer URLs.
    Checks 8 patterns in priority order.
    No browser, no network — pure HTML parsing.
    """
    if not html:
        return None

    # 🛡️ FIX 3: Check cep= app config on the landing URL itself
    config = extract_revcontent_app_config(base_url)
    if config.get("offer_url_from_cep"):
        print(f"  [L1] Found offer via cep-decode: {config['offer_url_from_cep'][:60]}")
        return config["offer_url_from_cep"]
    
    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    
    # Pattern 1: CSS class selectors (highest confidence)
    OFFER_CLASSES = [
        "offlink", "offer_link", "offerLink", "offer-link",
        "cta-link", "cta_link", "buy-link", "order-link",
        "checkout-link", "affiliate-link",
    ]
    for cls in OFFER_CLASSES:
        for el in soup.find_all(href=True, class_=re.compile(cls, re.I)):
            href = el.get("href", "")
            if href.startswith("http"):
                candidates.append((href, f"class:{cls}", 10))
    
    # Pattern 2: data attributes
    DATA_ATTRS = [
        "data-offer", "data-href", "data-redirect-url",
        "data-offer-url", "data-link", "data-url", "data-target",
    ]
    for attr in DATA_ATTRS:
        for el in soup.find_all(attrs={attr: True}):
            val = el.get(attr, "")
            if val.startswith("http"):
                candidates.append((val, f"data-attr:{attr}", 9))
    
    # Pattern 3: JavaScript variables in <script> tags
    JS_PATTERNS = [
        r'(?:var\s+|const\s+|let\s+)(?:offerUrl|offer_url|clickUrl|'
        r'click_url|redirectUrl|redirectLink|outUrl|finalUrl|'
        r'ctaUrl|destinationUrl)\s*[=:]\s*["\']?(https?://[^"\';\s]+)',
        r'window\.offerUrl\s*=\s*["\']?(https?://[^"\';\s]+)',
        r'(?:href|url)\s*:\s*["\']?(https?://[^"\';\s,}]+)',
    ]
    for script in soup.find_all("script"):
        text = script.string or ""
        for pattern in JS_PATTERNS:
            for match in re.finditer(pattern, text, re.I):
                url = match.group(1).rstrip("'\",;")
                if url.startswith("http"):
                    candidates.append((url, "js_variable", 8))
    
    # Pattern 4: Known affiliate network domains in any <a> href
    AFFILIATE_DOMAINS = [
        "hop.clickbank.net", "hop-apps.clickbank.net",
        "clickbank.com", "digistore24.com",
        "maxbounty.com", "shareasale.com",
        "awin1.com", "impactradius.com", "prf.hn",
        "linksynergy.com", "cj.com",
        "everad.com", "adcombo.com",
        "cpa.house", "mylead.global",
    ]
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        for domain in AFFILIATE_DOMAINS:
            if domain in href:
                candidates.append((href, f"aff_network:{domain}", 10))
    
    # Pattern 5: Known tracker domains (need browser click)
    # Just detect — mark as needs_click
    TRACKER_DOMAINS = [
        "prough-veridated.icu", "clktrkservices.com",
        "trkflstr.com", "trkerupper.com", "anti-aging.site",
    ]
    tracker_found = None
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        for domain in TRACKER_DOMAINS:
            if domain in href:
                tracker_found = href  # Signal to Layer 4
    
    # Pattern 6: Affiliate params in any href
    AFFILIATE_PARAMS = [
        "hop=", "hopId=", "aff_id=", "affid=", "affiliate_id=",
        "affiliate=", "offer_id=", "offid=", "oid=",
        "bf_lander=", "bf_offer=", "target_offer="
    ]
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        for param in AFFILIATE_PARAMS:
            if param in href:
                candidates.append((href, f"aff_param:{param}", 7))
    
    # Pattern 7: ClickBank hop-apps — extract destinationUrl
    for a in soup.find_all("a", href=True):
        href = a.get("href", "")
        if "hop-apps.clickbank.net" in href:
            params = parse_qs(urlparse(href).query)
            dest = params.get("destinationUrl", [None])[0]
            if dest:
                candidates.append((unquote(dest), "clickbank_hopapps", 10))
    
    # Pattern 8: Meta refresh redirect
    for meta in soup.find_all("meta", attrs={"http-equiv": re.compile("refresh", re.I)}):
        content = meta.get("content", "")
        match = re.search(r'url=(.+)', content, re.I)
        if match:
            url = match.group(1).strip("'\" ")
            if url.startswith("http"):
                candidates.append((url, "meta_refresh", 6))
    
    # Sort by confidence score
    candidates.sort(key=lambda x: x[2], reverse=True)
    
    # Validate and return best candidate
    for url, source, score in candidates:
        if is_valid_offer_url(url):
            print(f"  [L1] Found via {source}: {url[:60]}")
            return url
    
    # Return tracker URL if found (signals Layer 4 needed)
    if tracker_found:
        print(f"  [L1] Tracker detected — Layer 4 needed: {tracker_found[:60]}")
        return f"__TRACKER__:{tracker_found}"
    
    return None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAYER 2: HTTPX Redirect Chain Following
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def layer2_httpx_redirect(url: str) -> str | None:
    """
    HTTPX follows the complete HTTP redirect chain.
    Works for simple redirects that don't need JavaScript.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/124.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
        "Accept-Language": "en-US,en;q=0.9",
        "Accept-Encoding": "gzip, deflate, br",
        "DNT": "1",
        "Sec-Fetch-Mode": "navigate",
        "Sec-Fetch-Site": "none",
        "Sec-Fetch-Dest": "document",
        "Upgrade-Insecure-Requests": "1",
    }
    
    redirect_chain = [url]
    
    try:
        async with httpx.AsyncClient(
            follow_redirects=True,
            timeout=15.0,
            max_redirects=15,
            headers=headers,
        ) as client:
            response = await client.get(url)
            
            # Capture full redirect history
            for resp in response.history:
                location = resp.headers.get("location", "")
                if location and location not in redirect_chain:
                    redirect_chain.append(location)
            
            final_url = str(response.url)
            
            # Check if final URL differs from start
            # or if any URL in the chain looks like an offer
            for chain_url in reversed(redirect_chain + [final_url]):
                if is_valid_offer_url(chain_url) and chain_url != url:
                    print(f"  [L2] HTTPX final: {chain_url[:60]}")
                    return chain_url
            
            return None
    
    except httpx.TooManyRedirects:
        print(f"  [L2] Too many redirects for: {url[:50]}")
        return None
    except Exception as e:
        print(f"  [L2] HTTPX error: {e}")
        return None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAYER 3: BeautifulSoup Deep Pattern Scan
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def layer3_deep_pattern_scan(landing_url: str) -> str | None:
    """
    Fetches the landing page with requests and scans
    for EVERY possible offer URL pattern.
    """
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 Chrome/124.0.0.0 Safari/537.36"
        ),
        "Referer": "https://www.google.com/",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    try:
        async with httpx.AsyncClient(timeout=15.0, headers=headers,
                                      follow_redirects=True) as client:
            response = await client.get(landing_url)
            html = response.text
    except Exception as e:
        print(f"  [L3] Fetch error: {e}")
        return None
    
    # Try Layer 1 patterns on the fetched HTML first
    l1_result = layer1_static_extraction(html, landing_url)
    if l1_result and not l1_result.startswith("__TRACKER__"):
        return l1_result
    
    soup = BeautifulSoup(html, "html.parser")
    candidates = []
    
    # Deep scan: Find ALL URLs in script blocks
    url_pattern = re.compile(r'https?://[^\s"\'<>{}\[\]\\,;()\|]+')
    
    for script in soup.find_all("script"):
        script_text = script.string or script.get_text() or ""
        
        # Try to parse as JSON (some pages embed config objects)
        json_matches = re.findall(r'\{[^{}]{20,500}\}', script_text)
        for json_str in json_matches:
            try:
                data = json.loads(json_str)
                
                def extract_urls_from_json(obj, depth=0):
                    if depth > 5:
                        return []
                    found = []
                    if isinstance(obj, str) and obj.startswith("http"):
                        found.append(obj)
                    elif isinstance(obj, dict):
                        for v in obj.values():
                            found.extend(extract_urls_from_json(v, depth+1))
                    elif isinstance(obj, list):
                        for item in obj:
                            found.extend(extract_urls_from_json(item, depth+1))
                    return found
                
                for url in extract_urls_from_json(data):
                    candidates.append((url, "json_config", 7))
            except Exception:
                pass
        
        # Raw URL scan in script text
        for url in url_pattern.findall(script_text):
            url = url.rstrip("'\".,;)")
            if len(url) > 15 and "." in url:
                candidates.append((url, "script_url", 5))
    
    # Scan onclick handlers
    for el in soup.find_all(onclick=True):
        onclick = el.get("onclick", "")
        for url in url_pattern.findall(onclick):
            url = url.rstrip("'\".,;)")
            candidates.append((url, "onclick", 6))
    
    # Scan noscript tags
    for noscript in soup.find_all("noscript"):
        for a in BeautifulSoup(str(noscript), "html.parser").find_all("a", href=True):
            href = a.get("href", "")
            if href.startswith("http"):
                candidates.append((href, "noscript", 7))
    
    # Filter and validate
    SKIP_PATTERNS = [
        "google-analytics", "googletagmanager", "doubleclick",
        "facebook.com/tr", "connect.facebook", "pixel",
        "analytics", "taboola.com", "outbrain.com", "prebid",
        "cookie", "sync", ".css", ".js", ".png", ".jpg",
        "cloudflare.com/cdn-cgi",
    ]
    
    valid_candidates = []
    for url, source, score in candidates:
        if any(skip in url.lower() for skip in SKIP_PATTERNS):
            continue
        if is_valid_offer_url(url):
            # 🛡️ STRICT DOMAIN CHECK: Reject same-domain links unless they have high scores
            # (Arbitrage sites often link to their own articles which look like offers)
            from deep_analyzer import _extract_domain
            lp_domain = _extract_domain(landing_url)
            cand_domain = _extract_domain(url)
            
            if lp_domain and cand_domain == lp_domain:
                # Same domain - usually not the real offer unless it's a direct sale
                # We'll keep it with a very low base score
                valid_candidates.append((url, source, 1))
            else:
                valid_candidates.append((url, source, score))
    
    # Boost score for affiliate signals
    AFFILIATE_SIGNALS = [
        ("hop=", 5), ("hopId=", 5), ("aff_id=", 5),
        ("affid=", 5), ("offer_id=", 4), ("offid=", 4),
        ("oid=", 3), ("affiliate=", 4), ("checkout", 3),
        ("/vsl/", 3), ("/landers/", 3), ("/text.php", 3),
        ("clickbank", 5), ("digistore24", 5),
        ("bf_lander", 6), ("bf_offer", 6), ("melodyeu", 4)
    ]
    
    scored = []
    for url, source, score in valid_candidates:
        for signal, boost in AFFILIATE_SIGNALS:
            if signal in url.lower():
                score += boost
        scored.append((url, source, score))
    
    scored.sort(key=lambda x: x[2], reverse=True)
    
    if scored:
        best_url, source, score = scored[0]
        print(f"  [L3] Deep scan found ({source}, score={score}): {best_url[:60]}")
        return best_url
    
    return None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAYER 4: Playwright + CloakBrowser
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

MAX_CLICK_DEPTH = 3  # Max pre-lander chain depth

async def follow_prelander_chain(
    page,
    current_url: str,
    landing_url: str,
    depth: int = 0
) -> str | None:
    """
    Follows the chain: pre-lander → pre-lander → real offer
    Keeps clicking CTAs until reaching a valid offer page or hitting max depth.
    """
    if depth >= MAX_CLICK_DEPTH:
        print(f"  [Chain] Max depth reached at: {current_url[:50]}")
        return current_url
    
    # If current URL is NOT a pre-lander → it's the real offer
    if not is_prelander_domain(current_url):
        if is_valid_offer_url(current_url):
            print(f"  [Chain] ✅ Real offer at depth {depth}: {current_url[:60]}")
            return current_url
    
    print(f"  [Chain] Pre-lander at depth {depth}: {current_url[:60]}")
    print(f"  [Chain] Clicking through to next level...")
    
    # Navigate to pre-lander if not already there
    if page.url != current_url:
        try:
            await page.goto(current_url, wait_until="domcontentloaded", timeout=25000)
            await asyncio.sleep(2.0)
        except Exception as e:
            print(f"  [Chain] Nav error: {e}")
            return current_url
    
    # Check cep= app config decode first (wellnesspeek pattern)
    url = page.url
    config_result = extract_revcontent_app_config(url)
    if config_result.get("offer_url_from_cep"):
        offer = config_result["offer_url_from_cep"]
        return await follow_prelander_chain(page, offer, landing_url, depth+1)
    
    # Try static extraction on this pre-lander page
    try:
        html = await page.content()
        static = layer1_static_extraction(html, url)
        if static and not static.startswith("__TRACKER__"):
            if not is_prelander_domain(static):
                return await follow_prelander_chain(page, static, landing_url, depth+1)
    except: pass
    
    # Human warm-up on this page
    for _ in range(random.randint(2, 4)):
        await page.mouse.wheel(0, random.randint(150, 350))
        await asyncio.sleep(random.uniform(0.3, 0.7))
    await asyncio.sleep(random.uniform(1.0, 2.5))
    
    # Find CTA on this pre-lander
    CTA_SELECTORS = [
        "a.offlink", "a.offer_link", "a[class*='offlink']", "a[class*='offer-link']",
        "a[class*='cta']", "a[class*='buy']", "a:has-text('Order Now')",
        "a:has-text('Buy Now')", "a:has-text('Get Yours')", "a:has-text('Claim')",
        "a:has-text('Check Availability')", "a:has-text('Try It')", "a:has-text('Start')",
        "button:has-text('Order')", "button:has-text('Buy')", "button:has-text('Get')",
        "button:has-text('Yes')", "[data-offer]",
    ]
    
    cta = None
    for selector in CTA_SELECTORS:
        try:
            el = await page.query_selector(selector)
            if el and await el.is_visible():
                text = await el.text_content() or ""
                skip = ["disclaimer","privacy","terms","cookie","unsubscribe","©","sitemap"]
                if not any(s in text.lower() for s in skip):
                    cta = el
                    break
        except: continue
    
    if not cta:
        print(f"  [Chain] No CTA found at depth {depth}")
        return current_url
    
    # Click CTA
    try:
        new_tab_url = None
        async def capture_new_tab(new_page):
            nonlocal new_tab_url
            try:
                await new_page.wait_for_load_state("domcontentloaded", timeout=10000)
                new_tab_url = new_page.url
            except: pass
        
        page.context.on("page", capture_new_tab)
        
        await cta.scroll_into_view_if_needed()
        await asyncio.sleep(0.5)
        
        try:
            async with page.expect_navigation(timeout=15000, wait_until="domcontentloaded"):
                await cta.click()
        except:
            await cta.click(timeout=5000)
            await asyncio.sleep(4.0)
        
        # Check for new tab
        if new_tab_url and new_tab_url != current_url:
            return await follow_prelander_chain(page, new_tab_url, landing_url, depth+1)
        
        # Check current page
        new_url = page.url
        if new_url and new_url != current_url:
            return await follow_prelander_chain(page, new_url, landing_url, depth+1)
    
    except Exception as e:
        print(f"  [Chain] Click error: {e}")
    
    return current_url

async def layer4_browser_click(
    landing_url: str,
    tracker_url: str = None
) -> dict:
    """
    Full browser simulation with resilience and resource interception.
    """
    profile = get_profile(device_type="desktop", country="us")
    
    all_responses = []
    new_tab_urls = []
    cta_text = ""
    final_url = None
    
    async with async_playwright() as p:
        session = BrowserSession(p, profile)
        
        try:
            # 1. Start session
            page = await session.ensure_active()
            
            # 2. Monitor new tabs
            async def on_new_page(new_page):
                try:
                    await new_page.wait_for_load_state("domcontentloaded", timeout=10000)
                    url = new_page.url
                    if url and url.startswith("http"):
                        new_tab_urls.append(url)
                        print(f"  [L4] New tab: {url[:60]}")
                except: pass
            
            session.context.on("page", on_new_page)
            
            # 3. Monitor network
            def on_response(response):
                url = response.url
                SKIP = [".css", ".js", ".png", ".jpg", ".gif", ".woff", "google-analytics", "doubleclick"]
                if any(s in url.lower() for s in SKIP): return
                all_responses.append({"url": url, "status": response.status})
            
            page.on("response", on_response)
            
            # 4. Navigate with retry logic
            try:
                await page.goto(landing_url, wait_until="domcontentloaded", timeout=40000)
            except PlaywrightError as e:
                if "closed" in str(e).lower():
                    print("  [L4] Connection lost. Recovering...")
                    page = await session.ensure_active()
                    await page.goto(landing_url, wait_until="domcontentloaded", timeout=40000)
                else: raise e
                
            await asyncio.sleep(2.0)
            
            # 5. Multi-level click-through for pre-landers
            final_url = await follow_prelander_chain(
                page=page,
                current_url=page.url,
                landing_url=landing_url,
                depth=0
            )
            
            await asyncio.sleep(2.0)
            
        except Exception as e:
            print(f"  [L4] Browser error: {e}")
        finally:
            await session.close()
            
    return {
        "final_url": final_url,
        "new_tab_urls": new_tab_urls,
        "all_responses": all_responses,
        "cta_text": cta_text,
    }

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAYER 5: Extract from Captures
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def layer5_extract_from_captures(browser_result: dict, landing_url: str) -> str | None:
    """
    Analyzes everything captured during the browser session.
    """
    candidates = []
    
    # Priority 1: New tab URLs
    for url in browser_result.get("new_tab_urls", []):
        if is_valid_offer_url(url):
            candidates.append((url, "new_tab", 15))
    
    # Priority 2: Final page URL
    final = browser_result.get("final_url")
    if final and final != landing_url and is_valid_offer_url(final):
        candidates.append((final, "page_final", 10))
    
    # Priority 3: Network responses
    landing_domain = urlparse(landing_url).netloc.replace("www.", "")
    for resp in browser_result.get("all_responses", []):
        url = resp["url"]
        if is_ad_tech_url(url): continue
        
        resp_domain = urlparse(url).netloc.replace("www.", "")
        if resp_domain == landing_domain: continue
        
        if is_valid_offer_url(url):
            score = 5
            if any(s in url.lower() for s in ["hop=", "affid=", "aff_id=", "clickbank", "digistore", "bf_offer"]):
                score += 8
            if "melodyeu" in url.lower():
                score += 5
            candidates.append((url, f"network_{resp['status']}", score))
            
    if not candidates: return None
    
    candidates.sort(key=lambda x: x[2], reverse=True)
    best_url, source, score = candidates[0]
    print(f"  [L5] Best from captures ({source}, score={score}): {best_url[:60]}")
    return best_url

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAYER 6: Offer Page Validator
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def layer6_validate_and_fix(url: str, all_captured: list) -> str | None:
    """
    Final validation pass.
    """
    if url:
        if not is_valid_offer_url(url):
            url = None
        else:
            health = check_url_health(url)
            if not health["valid"]:
                url = None
                
    if url:
        print(f"  [L6] ✅ Validated: {url[:60]}")
        return url
        
    # Fallback to search all captured
    for candidate in reversed(all_captured):
        if is_valid_offer_url(candidate):
            health = check_url_health(candidate)
            if health["valid"]:
                print(f"  [L6] Alternative found: {candidate[:60]}")
                return candidate
    
    # 🕵️ DEEP FORENSICS: If we have a tracker but no final offer, try to resolve it
    for candidate in reversed(all_captured):
        if is_intermediary_domain(candidate):
            print(f"  [L6] Found potential tracker to resolve: {candidate[:60]}")
            resolution = await resolve_forensically_async(candidate)
            if resolution["success"]:
                final = resolution["final_url"]
                if is_valid_offer_url(final):
                    health = check_url_health(final)
                    if health["valid"]:
                        print(f"  [L6] Forensic resolution successful: {final[:60]}")
                        return final
                        
    return None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MASTER FUNCTION: resolve_offer_url()
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def resolve_offer_url(landing_url: str, landing_html: str = None, ad_title: str = "") -> dict:
    """
    Master resolver — implementing 'Simple-First' Mandatory Protocol.
    Retries 10 times with delay as per requirements.
    """
    print(f"\n  [Resolver] Starting for: {landing_url[:60]}")
    
    MAX_ATTEMPTS = 20
    RETRY_DELAY = 3 # seconds
    
    for attempt in range(1, MAX_ATTEMPTS + 1):
        if attempt > 1:
            print(f"  [Resolver] Attempt {attempt}/{MAX_ATTEMPTS} after {RETRY_DELAY}s delay...")
            await asyncio.sleep(RETRY_DELAY)

        # ── LAYER 0: Mandatory Surface Scan (Simple-First) ───────
        # Note: If landing_html is provided externally, we use it. 
        # If it fails, we fetch fresh HTML in subsequent attempts if needed.
        current_html = landing_html
        if not current_html:
            try:
                async with httpx.AsyncClient(timeout=10.0, follow_redirects=True) as client:
                    resp = await client.get(landing_url)
                    current_html = resp.text
            except: pass

        if current_html:
            l0 = layer0_simple_mandatory_scan(current_html, landing_url)
            if l0:
                health = await check_url_health(l0)
                if health.get("is_healthy") or health.get("valid"):
                    print(f"  [Resolver] ✅ L0_Simple_Scan Success on attempt {attempt}: {l0[:60]}")
                    return {"url": l0, "method": "L0_Simple_Scan", "layers_tried": 0, "attempts": attempt}

        # If it's the first attempt and L0 failed, try other layers immediately
        # OR if we've reached the end of simple attempts, escalate.
        if attempt == 1:
            # ── LAYER 1: Static HTML Analysis ────────────────────────
            if current_html:
                l1 = layer1_static_extraction(current_html, landing_url)
                if l1 and not l1.startswith("__TRACKER__"):
                    v = await layer6_validate_and_fix(l1, [])
                    if v: return {"url": v, "method": "layer1_static", "layers_tried": 1, "attempts": attempt}
                tracker_hint = l1.replace("__TRACKER__:", "") if l1 and l1.startswith("__TRACKER__") else None
            else: tracker_hint = None
            
            # ── LAYER 2: HTTPX Redirect ──────────────────────────────
            l2 = await layer2_httpx_redirect(landing_url)
            if l2:
                v = await layer6_validate_and_fix(l2, [])
                if v: return {"url": v, "method": "layer2_httpx", "layers_tried": 2, "attempts": attempt}

    # ── FINAL ESCALATION: Playwright (If all 10 L0-L2 attempts failed) ────
    print(f"  [Resolver] L0-L2 failed after {MAX_ATTEMPTS} attempts. Escalating to Browser...")
    
    # ── LAYER 3: Deep Pattern Scan ───────────────────────────
    l3 = await layer3_deep_pattern_scan(landing_url)
    if l3:
        v = await layer6_validate_and_fix(l3, [])
        if v: return {"url": v, "method": "layer3_deep_scan", "layers_tried": 3}
        
    # ── LAYER 4 & 5: Browser Click & Capture Analysis ────────
    browser_result = await layer4_browser_click(landing_url)
    all_captured = [r["url"] for r in browser_result.get("all_responses", [])] + browser_result.get("new_tab_urls", [])
    
    l5 = layer5_extract_from_captures(browser_result, landing_url)
    if l5:
        v = await layer6_validate_and_fix(l5, all_captured)
        if v: return {"url": v, "method": "layer5_capture", "layers_tried": 5}
        
    # ── LAYER 6: Final Fallback ──────────────────────────────
    l6 = await layer6_validate_and_fix(None, all_captured)
    if l6: return {"url": l6, "method": "layer6_fallback", "layers_tried": 6}
    
    return {"url": None, "method": "failed", "layers_tried": 6, "attempts": MAX_ATTEMPTS}
