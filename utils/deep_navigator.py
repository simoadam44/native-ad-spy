import asyncio
import re
import random
import time
import httpx
from urllib.parse import urlparse
from utils.url_resolver import resolve_forensically_async
from utils.tech_analyzer import TechAnalyzer
from utils.adblock_detector import is_likely_cta

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PART 1: Find the offer link in HTML
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def extract_offer_link_from_html(page) -> dict:
    """
    Scan page HTML/JS for offer links BEFORE clicking.
    Many pre-landers embed the tracking URL in JS variables
    or data attributes — we can extract without triggering.
    """
    try:
        html = await page.content()
    except Exception:
        html = ""
    
    # Pattern 1: offlink / offer_link CSS class
    # <a class="offlink offer_link" href="...">
    OFFER_LINK_SELECTORS = [
        "a.offlink",
        "a.offer_link",
        "a.offerLink",
        "a[class*='offlink']",
        "a[class*='offer-link']",
        "a[class*='cta-link']",
        "a[data-offer]",
        "a[data-href]",
        "[data-redirect-url]",
        "[data-offer-url]",
    ]
    
    for selector in OFFER_LINK_SELECTORS:
        try:
            elements = await page.query_selector_all(selector)
            for el in elements:
                href = (await el.get_attribute("href") or
                        await el.get_attribute("data-offer") or
                        await el.get_attribute("data-href") or
                        await el.get_attribute("data-redirect-url"))
                if href and href.startswith("http"):
                    return {
                        "found": True,
                        "url": href,
                        "method": f"html_selector:{selector}"
                    }
        except Exception:
            continue
    
    # Pattern 2: Extract from JavaScript variables
    JS_VAR_PATTERNS = [
        # Common JS variable names for offer URLs
        "var offerUrl", "var offer_url", "var clickUrl",
        "var click_url", "var redirectUrl", "var redirect_url",
        "offerLink", "offer_link", "clickLink", "outgoingUrl",
        "destinationUrl", "finalUrl", "ctaUrl",
    ]
    
    for pattern in JS_VAR_PATTERNS:
        if pattern in html:
            # Extract URL from JS: var offerUrl = "https://..."
            match = re.search(
                pattern.replace("var ", r"(?:var\s+)") +
                r'\s*[=:]\s*["\']?(https?://[^"\';\s]+)',
                html
            )
            if match:
                url = match.group(1).rstrip("'\"")
                return {
                    "found": True,
                    "url": url,
                    "method": f"js_variable:{pattern}"
                }
    
    # Pattern 3: Look for tracking domains in all <a> tags
    KNOWN_TRACKER_PATTERNS = [
        "prough-veridated.icu",
        "clktrkservices.com",
        "trends.clktrkservices.com",
        "trkflstr.com",
        "trkerupper.com",
    ]
    
    try:
        all_links = await page.evaluate("""
            () => Array.from(document.querySelectorAll('a[href]'))
                       .map(a => ({href: a.href, text: a.textContent.trim()}))
                       .filter(l => l.href.startsWith('http'))
        """)
        
        for link in all_links:
            href = link.get("href", "")
            for tracker in KNOWN_TRACKER_PATTERNS:
                if tracker in href:
                    return {
                        "found": True,
                        "url": href,
                        "method": f"known_tracker_link:{tracker}",
                        "needs_browser_click": True  # Must click in browser
                    }
    except Exception:
        pass
    
    return {"found": False}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PART 2: Human-like click + full redirect capture
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def deep_click_and_capture(
    page,
    offer_link_url: str = None,
    landing_url: str = None
) -> dict:
    """
    Performs human-like interaction to trigger the tracker,
    then captures the COMPLETE redirect chain including
    all intermediate redirects that happen server-side.
    
    This is the key function that bypasses cloaking.
    """
    
    # ── SETUP: Capture ALL network requests ──────────────────
    all_requests = []
    all_responses = []
    final_urls_seen = []
    
    def on_request(request):
        url = request.url
        if (url.startswith("http") and
            not any(skip in url for skip in [
                ".css", ".js", ".png", ".jpg", ".gif",
                ".woff", "google-analytics", "googletagmanager",
                "facebook.com/tr", "doubleclick", "prebid",
                "cookie", "sync", "pixel"
            ])):
            all_requests.append({
                "url": url,
                "method": request.method,
                "timestamp": time.time()
            })
    
    def on_response(response):
        url = response.url
        status = response.status
        if (url.startswith("http") and
            not any(skip in url for skip in [
                ".css", ".js", ".png", ".jpg", ".gif",
                ".woff", "google-analytics", "googletagmanager",
            ])):
            all_responses.append({
                "url": url,
                "status": status,
                "location": response.headers.get("location", ""),
                "timestamp": time.time()
            })
            if status == 200:
                final_urls_seen.append(url)
    
    # Register listeners BEFORE any click
    page.on("request", on_request)
    page.on("response", on_response)
    
    # Forensic context for new pages
    captured_pages = []
    
    async def handle_new_page(new_page):
        try:
            print(f"  [DeepNav] 🚀 NEW TAB DETECTED: {new_page.url[:60]}")
            captured_pages.append(new_page)
            # Apply same listeners to new page
            new_page.on("request", on_request)
            new_page.on("response", on_response)
            
            # Wait for content to settle in new tab
            await new_page.wait_for_load_state("domcontentloaded", timeout=10000)
            await asyncio.sleep(2) # Human pause
        except Exception:
            pass
            
    page.context.on("page", handle_new_page)
    
    # ── STEP 1: Human warm-up behavior ───────────────────────
    # Simulate reading the article for a few seconds
    
    # Random mouse movements across the page
    for _ in range(random.randint(3, 6)):
        x = random.randint(200, 800)
        y = random.randint(300, 700)
        try:
            await page.mouse.move(x, y)
        except Exception:
            pass
        await asyncio.sleep(random.uniform(0.3, 0.8))
    
    # Scroll down slowly (reading behavior)
    total_scroll = 0
    try:
        page_height = await asyncio.wait_for(page.evaluate("document.body.scrollHeight"), timeout=3.0)
        page_height = min(page_height, 3000) # CAP height to prevent 120s timeout
    except Exception:
        page_height = 2000
    
    while total_scroll < page_height * 0.6:
        scroll_step = random.randint(100, 300)
        try:
            await page.mouse.wheel(0, scroll_step)
        except Exception:
            break
        total_scroll += scroll_step
        await asyncio.sleep(random.uniform(0.4, 1.2))
    
    # Pause at bottom (simulates finishing reading)
    await asyncio.sleep(random.uniform(1.5, 3.0))
    
    # ── STEP 2: Find and click the offer CTA ────────────────
    cta_element = None
    cta_text = ""
    
    # Priority order for CTA selectors
    CTA_SELECTORS = [
        # Direct offer link classes
        ("a.offlink", "offlink class"),
        ("a.offer_link", "offer_link class"),
        ("a[class*='offlink']", "offlink partial"),
        ("a[class*='offer-link']", "offer-link partial"),
        # Specific href patterns
        (f"a[href*='prough-veridated']", "prough tracker"),
        (f"a[href*='clktrkservices']", "clktrkservices tracker"),
        (f"a[href*='trkflstr']", "trkflstr tracker"),
        # Text-based CTAs
        ("a:has-text('Order Now')", "Order Now text"),
        ("a:has-text('Buy Now')", "Buy Now text"),
        ("a:has-text('Check Availability')", "Check Availability"),
        ("a:has-text('Get Yours')", "Get Yours"),
        ("a:has-text('Claim')", "Claim text"),
        ("a:has-text('Click Here')", "Click Here text"),
        ("a:has-text('Watch Video')", "Watch Video text"),
        ("button:has-text('Order')", "Order button"),
        ("button:has-text('Buy')", "Buy button"),
        # If offer_link_url is known — find by href
        (f"a[href*='{offer_link_url[:30]}']" if offer_link_url else None, "known url"),
    ]
    
    for selector, label in CTA_SELECTORS:
        if not selector: continue
        try:
            # Short timeout to avoid hanging
            el = await asyncio.wait_for(page.query_selector(selector), timeout=1.5)
            if el:
                cta_element = el
                cta_text = await el.inner_text()
                print(f"  [DeepNav] Found CTA via {label}: '{cta_text.strip()[:30]}'", flush=True)
                break
        except Exception:
            pass
    
    # ── STEP 2.5: AdBlock Plus Forensic Fallback ───────────
    if not cta_element:
        print("  [DeepNav] Standard CTA search failed, using AdBlock Plus forensic fallback...", flush=True)
        try:
            # Evaluate elements in browser to find likely CTAs
            best_match = await asyncio.wait_for(page.evaluate("""
                () => {
                    const elements = Array.from(document.querySelectorAll('a, button'));
                    for (const el of elements) {
                        const classes = Array.from(el.classList);
                        const id = el.id || "";
                        const text = el.innerText || "";
                        const tagName = el.tagName.toLowerCase();
                        
                        // We use a simplified version of is_likely_cta in JS for speed
                        const combined = (classes.join(" ") + " " + id).toLowerCase();
                        const textLower = text.toLowerCase().trim();
                        
                        if (combined.includes("cta") || combined.includes("button") || combined.includes("offlink") ||
                            textLower.includes("order now") || textLower.includes("buy now") || textLower.includes("check availability")) {
                            return {
                                selector: `a:has-text("${text.slice(0, 20)}")`,
                                text: text
                            };
                        }
                    }
                    return null;
                }
            """), timeout=3.0)
            if best_match:
                cta_element = await page.query_selector(best_match["selector"])
                cta_text = best_match["text"]
                print(f"  [DeepNav] Found via Forensic Fallback: '{cta_text}'")
        except Exception:
            pass
            
    if not cta_element:
        print("  [DeepNav] No CTA found")
        # Cleanup
        try:
            page.remove_listener("request", on_request)
            page.remove_listener("response", on_response)
        except Exception:
            pass
        return {
            "success": False,
            "reason": "no_cta_found",
            "all_requests": all_requests[:10]
        }
    
    # ── STEP 3: Human-like click ─────────────────────────────
    
    try:
        # Get element position
        box = await cta_element.bounding_box()
        if box:
            # Move mouse near element first (natural approach)
            pre_x = box['x'] + box['width'] * 0.3
            pre_y = box['y'] - 30
            await page.mouse.move(pre_x, pre_y)
            await asyncio.sleep(random.uniform(0.2, 0.5))
            
            # Move to element center with tiny random offset
            center_x = box['x'] + box['width']/2 + random.randint(-3, 3)
            center_y = box['y'] + box['height']/2 + random.randint(-2, 2)
            await page.mouse.move(center_x, center_y)
            await asyncio.sleep(random.uniform(0.1, 0.3))
        
        # Scroll into view
        await cta_element.scroll_into_view_if_needed()
        await asyncio.sleep(random.uniform(0.3, 0.7))
    except Exception as e:
        print(f"  [DeepNav] Error during mouse movement: {e}")
    
    # ── STEP 4: Click and wait for all redirects ─────────────
    
    # (Handled by global context listener above)
    
    try:
        async with page.expect_navigation(
            timeout=20000,
            wait_until="domcontentloaded"
        ):
            await cta_element.click()
    except Exception:
        # Navigation may have opened new tab or used JS redirect
        pass
    
    # Wait for all server-side redirects to complete
    await asyncio.sleep(3.0)
    
    try:
        await page.wait_for_load_state("networkidle", timeout=8000)
    except Exception:
        pass
    
    # Additional wait for slow redirect chains
    await asyncio.sleep(2.0)
    
    # ── STEP 5: Determine final URL ──────────────────────────
    
    final_url = None
    
    # Priority 1: New tab opened
    if captured_pages:
        # Use the latest meaningful page opened
        final_page = captured_pages[-1]
        final_url = final_page.url
        print(f"  [DeepNav] Final URL from new tab: {final_url[:60]}")
    
    # Priority 2: Current page URL changed
    elif page.url != landing_url:
        final_url = page.url
    
    # Priority 3: Extract from all captured responses
    # Find the last 200 response with affiliate/offer signals
    if not final_url or final_url == landing_url:
        for resp in reversed(all_responses):
            url = resp["url"]
            if (resp["status"] == 200 and
                url != landing_url and
                _looks_like_offer_url(url)):
                final_url = url
                break
    
    # Remove listeners
    try:
        page.remove_listener("request", on_request)
        page.remove_listener("response", on_response)
        page.context.remove_listener("page", handle_new_page)
    except Exception:
        pass
    
    # Build clean redirect chain
    clean_chain = []
    for resp in all_responses:
        url = resp["url"]
        if (resp["status"] in [200, 301, 302, 303, 307, 308] and
            url not in [c["url"] for c in clean_chain] and
            not any(skip in url for skip in [
                "google-analytics", "doubleclick",
                "cookie", "sync", "pixel", "beacon"
            ])):
            clean_chain.append({
                "url": url,
                "status": resp["status"],
                "location": resp.get("location", "")
            })
    
    # Analyze chain with Wappalyzer
    print(f"  [DeepNav] Analyzing redirect chain for affiliate networks...", flush=True)
    tech = TechAnalyzer()
    for item in clean_chain:
        if "google" not in item["url"]:
            site_tech = tech.analyze(item["url"])
            if site_tech.get("tracking_software"):
                item["tracking_software"] = site_tech["tracking_software"]
                print(f"  [DeepNav] 🔍 Found tracker in chain: {site_tech['tracking_software']} at {item['url'][:40]}...")
    
    print(f"  [DeepNav] Captured {len(clean_chain)} meaningful URLs")
    print(f"  [DeepNav] Final URL: {str(final_url)[:60]}")
    
    return {
        "success": True,
        "final_url": final_url,
        "cta_text": cta_text,
        "clean_chain": clean_chain,
        "all_responses_count": len(all_responses),
        "new_tab": bool(captured_pages)
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PART 3: URL scoring helper
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def _looks_like_offer_url(url: str) -> bool:
    """
    Quick heuristic: does this URL look like a real offer page?
    Not a tracker, not a pixel, not an ad tech URL.
    """
    url_lower = url.lower()
    
    OFFER_SIGNALS = [
        "hop=", "hopId=", "aff_id=", "affid=", "affiliate",
        "offer_id=", "offid=", "oid=",
        "checkout", "order", "buy", "cart", "shop",
        "/vsl/", "/landers/", "/text.php",
        "clickbank", "digistore", "maxbounty",
    ]
    
    BAD_SIGNALS = [
        "google-analytics", "doubleclick", "cookie",
        "sync", "pixel", "beacon", "prebid", "rubicon",
        "taboola.com/sg", "sync.taboola",
        "cloudflare.com/cdn-cgi",
        ".css", ".js", ".jpg", ".png", ".gif",
    ]
    
    if any(bad in url_lower for bad in BAD_SIGNALS):
        return False
    
    if any(good in url_lower for good in OFFER_SIGNALS):
        return True
    
    # Check if domain changed significantly (cloaking detection)
    return True  # Allow for post-filtering


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# PART 4: Master deep navigation function
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def find_real_offer_deep(
    page,
    landing_url: str,
    ad_title: str = ""
) -> dict:
    """
    Complete deep navigation pipeline.
    
    1. Extract offer link from HTML (fast, no click)
    2. If found and not tracker → validate directly
    3. If tracker or not found → deep click + capture
    4. Validate final URL
    5. Return offer intelligence
    """
    
    print(f"\n  [DeepNav] Starting deep navigation...")
    
    # PHASE 1: Try to extract offer link from HTML
    html_result = await extract_offer_link_from_html(page)
    
    if html_result["found"] and not html_result.get("needs_browser_click"):
        offer_url = html_result["url"]
        print(f"  [DeepNav] Found in HTML: {offer_url[:60]}")
        
        # Quick validate: is this already the real offer?
        from utils.url_blacklist import is_valid_offer_url
        if is_valid_offer_url(offer_url):
            return {
                "final_url": offer_url,
                "method": html_result["method"],
                "success": True,
                "clean_chain": [offer_url],
                "deep_click_needed": False
            }
        else:
            # It's a tracker, but maybe we can resolve it FAST via HTTPX
            print(f"  [DeepNav] Tracker detected in HTML, attempting fast forensic resolution...", flush=True)
            httpx_res = await resolve_forensically_async(offer_url)
            if httpx_res["success"] and is_valid_offer_url(httpx_res["final_url"]):
                print(f"  [DeepNav] Fast resolution success: {httpx_res['final_url'][:60]}")
                return {
                    "final_url": httpx_res["final_url"],
                    "method": f"fast_forensic:{html_result['method']}",
                    "success": True,
                    "clean_chain": [c["url"] for c in httpx_res["chain"]],
                    "deep_click_needed": False
                }
            print(f"  [DeepNav] Fast resolution inconclusive, proceeding to deep click.")
    
    # PHASE 2: Must do deep click
    print(f"  [DeepNav] Performing deep click...")
    
    offer_link = html_result.get("url") if html_result["found"] else None
    
    click_result = await deep_click_and_capture(
        page=page,
        offer_link_url=offer_link,
        landing_url=landing_url
    )
    
    if not click_result["success"]:
        return {
            "final_url": None,
            "method": "deep_click_failed",
            "success": False,
            "reason": click_result.get("reason"),
            "clean_chain": []
        }
    
    final_url = click_result["final_url"]
    clean_chain = click_result["clean_chain"]
    
    # PHASE 3: Validate the final URL
    from utils.url_blacklist import is_valid_offer_url
    if not is_valid_offer_url(final_url):
        # Try to find better URL in the chain
        for item in reversed(clean_chain):
            url = item["url"] if isinstance(item, dict) else item
            if is_valid_offer_url(url) and url != landing_url:
                final_url = url
                break
    
    print(f"  [DeepNav] ✅ Final offer: {str(final_url)[:60]}")
    
    return {
        "final_url": final_url,
        "clean_chain": clean_chain,
        "cta_text": click_result.get("cta_text"),
        "method": "deep_click",
        "success": bool(final_url),
        "new_tab": click_result.get("new_tab", False)
    }
