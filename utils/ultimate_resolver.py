import re, httpx, asyncio, random, json
from bs4 import BeautifulSoup
from urllib.parse import urlparse, parse_qs, unquote
from playwright.async_api import async_playwright

# Import existing utilities
from utils.url_blacklist import is_valid_offer_url, is_ad_tech_url
from utils.offer_validator import check_url_health
from utils.ghost_browser import get_profile

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
            valid_candidates.append((url, source, score))
    
    # Boost score for affiliate signals
    AFFILIATE_SIGNALS = [
        ("hop=", 5), ("hopId=", 5), ("aff_id=", 5),
        ("affid=", 5), ("offer_id=", 4), ("offid=", 4),
        ("oid=", 3), ("affiliate=", 4), ("checkout", 3),
        ("/vsl/", 3), ("/landers/", 3), ("/text.php", 3),
        ("clickbank", 5), ("digistore24", 5),
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

async def layer4_browser_click(
    landing_url: str,
    tracker_url: str = None
) -> dict:
    """
    Full browser simulation using CloakBrowser binary if available.
    """
    # Get CloakBrowser binary path
    try:
        from cloakbrowser._binary import get_binary_path
        cloak_binary = get_binary_path()
        using_cloak = True
        print("  [L4] Using CloakBrowser binary ✅")
    except (ImportError, Exception):
        cloak_binary = None
        using_cloak = False
        print("  [L4] CloakBrowser not available, using standard Playwright")
    
    profile = get_profile(device_type="desktop", country="us")
    
    all_responses = []
    new_tab_urls = []
    cta_text = ""
    final_url = None
    
    async with async_playwright() as p:
        launch_kwargs = {
            "headless": True,
            "args": [
                "--no-sandbox",
                "--disable-dev-shm-usage",
                "--disable-blink-features=AutomationControlled",
                f"--window-size={profile['viewport']['width']},"
                f"{profile['viewport']['height']}",
            ]
        }
        
        if cloak_binary:
            launch_kwargs["executable_path"] = cloak_binary
        
        try:
            browser = await p.chromium.launch(**launch_kwargs)
            context = await browser.new_context(
                user_agent=profile["user_agent"],
                viewport=profile["viewport"],
                locale=profile["locale"],
                timezone_id=profile["timezone"],
                extra_http_headers={
                    "Accept-Language": profile["accept_language"],
                }
            )
            
            if not using_cloak:
                await context.add_init_script(f"""
                    Object.defineProperty(navigator, 'webdriver', {{get: () => undefined}});
                    window.chrome = {{runtime: {{}}}};
                    Object.defineProperty(navigator, 'plugins', {{get: () => [1,2,3]}});
                    Object.defineProperty(navigator, 'platform', {{get: () => '{profile.get("platform","Win32")}'}});
                """)
            
            # Monitor new tabs
            async def on_new_page(new_page):
                try:
                    await new_page.wait_for_load_state("domcontentloaded", timeout=10000)
                    url = new_page.url
                    if url and url.startswith("http"):
                        new_tab_urls.append(url)
                        print(f"  [L4] New tab: {url[:60]}")
                except: pass
            
            context.on("page", on_new_page)
            
            page = await context.new_page()
            
            # Monitor network
            def on_response(response):
                url = response.url
                SKIP = [".css", ".js", ".png", ".jpg", ".gif", ".woff", "google-analytics", "doubleclick"]
                if any(s in url.lower() for s in SKIP): return
                all_responses.append({"url": url, "status": response.status})
            
            page.on("response", on_response)
            
            # Navigate
            await page.goto(landing_url, wait_until="domcontentloaded", timeout=40000)
            await asyncio.sleep(2.0)
            
            # Human scrolling
            for _ in range(random.randint(3, 6)):
                step = random.randint(150, 400)
                await page.mouse.wheel(0, step)
                await asyncio.sleep(random.uniform(0.3, 0.7))
            
            # Find CTA
            CTA_SELECTORS = [
                "a.offlink", "a.offer_link", "a[class*='offlink']", "a[class*='offer-link']",
                "a[class*='cta']", "a[class*='buy']", "a[class*='order']",
                "a:has-text('Order Now')", "a:has-text('Buy Now')", "a:has-text('Get Yours')",
                "a:has-text('Claim')", "a:has-text('Check Availability')",
                "button:has-text('Order Now')", "button:has-text('Buy Now')",
            ]
            
            if tracker_url:
                tracker_domain = urlparse(tracker_url).netloc
                CTA_SELECTORS.insert(0, f"a[href*='{tracker_domain}']")
            
            cta_element = None
            for selector in CTA_SELECTORS:
                try:
                    el = await page.query_selector(selector)
                    if el and await el.is_visible():
                        cta_element = el
                        cta_text = (await el.text_content() or "").strip()[:30]
                        break
                except: continue
            
            if cta_element:
                print(f"  [L4] Clicking CTA: '{cta_text}'")
                try:
                    # Move mouse to CTA
                    box = await cta_element.bounding_box()
                    if box:
                        await page.mouse.move(box['x'] + box['width']/2, box['y'] + box['height']/2)
                        await asyncio.sleep(0.3)
                    
                    async with page.expect_navigation(timeout=20000, wait_until="domcontentloaded"):
                        await cta_element.click()
                except:
                    # Fallback to direct click
                    try: await cta_element.click(timeout=5000)
                    except: pass
                
                await asyncio.sleep(4.0)
                try: await page.wait_for_load_state("networkidle", timeout=8000)
                except: pass
            
            final_url = page.url
            
            await page.close()
            await context.close()
            await browser.close()
            
        except Exception as e:
            print(f"  [L4] Browser error: {e}")
            
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
            if any(s in url.lower() for s in ["hop=", "affid=", "aff_id=", "clickbank", "digistore"]):
                score += 8
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
                
    return None

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MASTER FUNCTION: resolve_offer_url()
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def resolve_offer_url(landing_url: str, landing_html: str = None, ad_title: str = "") -> dict:
    """
    Master resolver — tries all 6 layers in sequence.
    """
    print(f"\n  [Resolver] Starting for: {landing_url[:60]}")
    
    # ── LAYER 1: Static HTML ─────────────────────────────────
    if landing_html:
        l1 = layer1_static_extraction(landing_html, landing_url)
        if l1 and not l1.startswith("__TRACKER__"):
            v = await layer6_validate_and_fix(l1, [])
            if v: return {"url": v, "method": "layer1_static", "layers_tried": 1}
        tracker_hint = l1.replace("__TRACKER__:", "") if l1 and l1.startswith("__TRACKER__") else None
    else: tracker_hint = None
    
    # ── LAYER 2: HTTPX Redirect ──────────────────────────────
    l2 = await layer2_httpx_redirect(landing_url)
    if l2:
        v = await layer6_validate_and_fix(l2, [])
        if v: return {"url": v, "method": "layer2_httpx", "layers_tried": 2}
        
    # ── LAYER 3: Deep Pattern Scan ───────────────────────────
    l3 = await layer3_deep_pattern_scan(landing_url)
    if l3:
        v = await layer6_validate_and_fix(l3, [])
        if v: return {"url": v, "method": "layer3_deep_scan", "layers_tried": 3}
        
    # ── LAYER 4 & 5: Browser Click & Capture Analysis ────────
    browser_result = await layer4_browser_click(landing_url, tracker_hint)
    all_captured = [r["url"] for r in browser_result.get("all_responses", [])] + browser_result.get("new_tab_urls", [])
    
    l5 = layer5_extract_from_captures(browser_result, landing_url)
    if l5:
        v = await layer6_validate_and_fix(l5, all_captured)
        if v: return {"url": v, "method": "layer5_capture", "layers_tried": 5}
        
    # ── LAYER 6: Final Fallback ──────────────────────────────
    l6 = await layer6_validate_and_fix(None, all_captured)
    if l6: return {"url": l6, "method": "layer6_fallback", "layers_tried": 6}
    
    return {"url": None, "method": "failed", "layers_tried": 6}
