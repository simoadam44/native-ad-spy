import asyncio
import requests
from urllib.parse import urlparse
from utils.url_blacklist import is_valid_offer_url, is_ad_tech_url

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAYER 1: HTTP & Content Weight Check
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

def check_url_health(url: str) -> dict:
    """
    Fast pre-check using requests (no browser needed).
    Checks HTTP status and content size.
    """
    if not url or not url.startswith("http"):
        return {"valid": False, "reason": "invalid_url_format"}
    
    # 🛡️ EARLY EXIT: Don't even hit ad-tech infrastructure
    if is_ad_tech_url(url):
        return {"valid": False, "reason": "ad_tech_infrastructure"}

    try:
        response = requests.get(
            url,
            timeout=8,
            allow_redirects=True,
            headers={
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
                "Accept": "text/html,application/xhtml+xml,*/*;q=0.9",
            }
        )
        
        # Check HTTP status
        if response.status_code == 404:
            return {"valid": False, "reason": "http_404_not_found"}
        if response.status_code == 403:
            return {"valid": False, "reason": "http_403_forbidden"}
        if response.status_code == 500:
            return {"valid": False, "reason": "http_500_server_error"}
        if response.status_code not in [200, 201, 301, 302]:
            return {"valid": False, "reason": f"http_{response.status_code}"}
        
        # Check content size
        content_length = len(response.content)
        if content_length < 3000:
            return {
                "valid": False,
                "reason": "thin_content",
                "size_bytes": content_length,
                "note": "Real offer pages are > 10KB"
            }
        
        # Check if we were redirected to a known bad domain
        final_url = response.url
        if final_url != url:
            if not is_valid_offer_url(final_url):
                return {
                    "valid": False,
                    "reason": "redirected_to_invalid_domain",
                    "final_url": final_url
                }
        
        return {
            "valid": True,
            "status_code": response.status_code,
            "content_size_kb": round(content_length / 1024, 1),
            "final_url": response.url,
            "content_preview": response.text[:500]
        }
    
    except requests.exceptions.ConnectionError:
        return {"valid": False, "reason": "connection_error"}
    except requests.exceptions.Timeout:
        return {"valid": False, "reason": "timeout"}
    except Exception as e:
        return {"valid": False, "reason": str(e)[:80]}


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAYER 2: Page Content Validation
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def validate_page_content(page) -> dict:
    """
    Browser-based content validation.
    Detects tracking pages, thin content, and real offer signals.
    """
    url = page.url
    title = await page.title() or ""
    
    try:
        body_text = await page.inner_text("body") or ""
    except Exception:
        body_text = ""
    
    try:
        full_html = await page.content() or ""
    except Exception:
        full_html = ""
    
    title_lower = title.lower()
    body_lower = body_text.lower()
    html_lower = full_html.lower()
    
    # ── CHECK 1: Tracking/redirect page indicators ──────────
    TRACKING_PAGE_SIGNALS = [
        # Title signals
        "just a moment",          # Cloudflare
        "please wait",
        "loading...",
        "redirecting",
        "checking your browser",
        "one moment",
        "almost there",
        "verifying you",
        # Body signals
        "redirect", "tracking pixel",
        "this page intentionally left blank",
    ]
    
    for signal in TRACKING_PAGE_SIGNALS:
        if signal in title_lower or signal in body_lower[:500]:
            return {
                "valid": False,
                "reason": "tracking_redirect_page",
                "matched_signal": signal
            }
    
    # ── CHECK 2: Thin content (< 500 chars body text) ────────
    body_text_clean = body_text.strip()
    if len(body_text_clean) < 400:
        return {
            "valid": False,
            "reason": "thin_content",
            "body_length": len(body_text_clean)
        }
    
    # ── CHECK 3: Meta tag quality ────────────────────────────
    has_meta_description = (
        'name="description"' in html_lower or
        'property="og:description"' in html_lower or
        'property="og:title"' in html_lower
    )
    
    # ── CHECK 4: Real offer signals (scoring) ───────────────
    offer_score = 0
    offer_signals_found = []
    
    OFFER_SIGNALS = {
        "buy now": 3, "order now": 3, "add to cart": 3,
        "get yours": 2, "claim": 2, "checkout": 3,
        "limited offer": 2, "special offer": 2,
        "money back": 2, "guarantee": 2,
        "free shipping": 2, "discount": 1,
        "price": 1, "buy": 1, "shop": 1,
        "$": 2, "€": 2, "£": 2,
        "only $": 3, "was $": 2, "save ": 2,
    }
    
    for signal, score in OFFER_SIGNALS.items():
        if signal in body_lower:
            offer_score += score
            offer_signals_found.append(signal)
    
    # ── CHECK 5: Arbitrage signals (page has ADs on it) ──────
    arbitrage_score = 0
    ARBITRAGE_SIGNALS = {
        "taboola": 3, "outbrain": 3, "revcontent": 3,
        "adsbygoogle": 3, "googlesyndication": 3,
        "you might also like": 2, "sponsored content": 2,
        "related articles": 2, "continue reading": 1,
        "next page": 2, "slide": 1, "/page/": 1,
    }
    
    for signal, score in ARBITRAGE_SIGNALS.items():
        if signal in html_lower:
            arbitrage_score += score
    
    if arbitrage_score >= 5:
        return {
            "valid": False,
            "reason": "arbitrage_page",
            "arbitrage_score": arbitrage_score,
            "note": "Page has ad networks — it's a publisher, not an offer"
        }
    
    return {
        "valid": True,
        "offer_score": offer_score,
        "offer_signals": offer_signals_found[:5],
        "has_meta": has_meta_description,
        "body_length": len(body_text_clean),
        "title": title[:80],
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAYER 3: Offer Type Classifier
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def classify_offer_type(page, url: str) -> dict:
    """
    Classify what TYPE of offer page this is.
    Returns one of: Affiliate, Dropshipping, CPA,
                    WordPress, Arbitrage, Unknown
    """
    try:
        html = await page.content() or ""
        body_text = await page.inner_text("body") or ""
    except Exception:
        html = ""
        body_text = ""
    
    html_lower = html.lower()
    body_lower = body_text.lower()
    url_lower = url.lower()
    
    scores = {
        "Affiliate/CPA": 0,
        "Dropshipping": 0,
        "Arbitrage": 0,
        "WordPress Blog": 0,
        "Lead Gen": 0,
    }
    signals = {}
    
    # ── Affiliate/CPA signals ────────────────────────────────
    AFFILIATE_SIGNALS = {
        # Strong CTA patterns
        "order now": 4, "rush my order": 4,
        "yes! i want": 4, "claim your": 3,
        "limited time": 2, "only x bottles": 3,
        # Guarantee patterns
        "60-day guarantee": 3, "money back guarantee": 3,
        "satisfaction guaranteed": 2,
        # VSL patterns
        "watch this video": 2, "play video": 2,
        # Countdown
        "countdown": 2, "timer": 1, "expires": 2,
        # Health niche
        "supplement": 2, "formula": 2, "clinically": 2,
        # ClickBank/affiliate footprints
        "clickbank": 3, "hoplink": 3,
        "affiliate": 2, "aff_id": 3,
        # Disclaimers
        "these statements have not been evaluated": 3,
        "fda has not evaluated": 3,
        "individual results may vary": 2,
    }
    for s, v in AFFILIATE_SIGNALS.items():
        if s in body_lower or s in html_lower:
            scores["Affiliate/CPA"] += v
            signals.setdefault("Affiliate/CPA", []).append(s)
    
    # ── Dropshipping signals ─────────────────────────────────
    DROPSHIP_SIGNALS = {
        # Platform footprints
        "shopify": 4, "cdn.shopify": 4, "myshopify": 4,
        "woocommerce": 4, "wp-content/plugins/woocommerce": 5,
        "bigcommerce": 4,
        # Shopping signals
        "add to cart": 3, "add to bag": 3,
        "shopping cart": 3, "checkout": 2,
        "in stock": 2, "out of stock": 2,
        "ships from": 2, "free shipping": 2,
        "quantity": 2, "size": 1, "color": 1,
        # Payment signals
        "paypal": 2, "stripe": 2, "visa": 1, "mastercard": 1,
        "secure checkout": 2,
    }
    for s, v in DROPSHIP_SIGNALS.items():
        if s in body_lower or s in html_lower:
            scores["Dropshipping"] += v
            signals.setdefault("Dropshipping", []).append(s)
    
    # ── Arbitrage signals ────────────────────────────────────
    ARB_SIGNALS = {
        "taboola": 5, "outbrain": 5, "mgid": 4,
        "adsbygoogle": 4, "googlesyndication": 4,
        "you might also like": 3, "recommended for you": 3,
        "sponsored": 2, "next page": 2,
        "comments": 1, "share this": 1,
        "by staff writer": 2, "by admin": 1,
    }
    for s, v in ARB_SIGNALS.items():
        if s in html_lower:
            scores["Arbitrage"] += v
            signals.setdefault("Arbitrage", []).append(s)
    
    # ── WordPress Blog signals ────────────────────────────────
    WP_SIGNALS = {
        "/wp-content/": 5, "/wp-includes/": 5,
        "wordpress": 4, "wp-json": 4,
        "/category/": 3, "/tag/": 2,
        "posted by": 2, "filed under": 2,
        "leave a reply": 3, "leave a comment": 3,
    }
    for s, v in WP_SIGNALS.items():
        if s in html_lower or s in url_lower:
            scores["WordPress Blog"] += v
            signals.setdefault("WordPress Blog", []).append(s)
    
    # ── Lead Gen signals ─────────────────────────────────────
    LEAD_SIGNALS = {
        "enter your email": 3, "get a free quote": 4,
        "get a quote": 4, "free consultation": 3,
        "request a callback": 3, "submit your info": 2,
        "enter your zip": 3, "enter zip code": 3,
        "compare rates": 3, "find your match": 2,
        "how many employees": 2, "what is your budget": 2,
    }
    for s, v in LEAD_SIGNALS.items():
        if s in body_lower:
            scores["Lead Gen"] += v
            signals.setdefault("Lead Gen", []).append(s)
    
    # ── Determine winner ─────────────────────────────────────
    best_type = max(scores, key=scores.get)
    best_score = scores[best_type]
    
    if best_score < 3:
        best_type = "Unknown"
    
    return {
        "offer_type": best_type,
        "confidence": "high" if best_score >= 8
                      else "medium" if best_score >= 4
                      else "low",
        "score": best_score,
        "all_scores": scores,
        "top_signals": signals.get(best_type, [])[:5],
    }


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# LAYER 4: Smart Retry Logic
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def find_real_offer_with_retry(
    page,
    current_offer_url: str,
    landing_url: str,
    max_retries: int = 2
) -> dict:
    """
    If current offer URL fails validation, try to find
    the real offer by clicking deeper into the funnel.
    
    Retry strategy:
      1. Validate current URL
      2. If invalid → look for CTA on current page
      3. Click CTA → check new URL
      4. Repeat up to max_retries times
    """
    
    for attempt in range(max_retries + 1):
        
        url_to_check = current_offer_url if attempt == 0 else page.url
        
        print(f"  [Validator] Attempt {attempt + 1}: {url_to_check[:60]}")
        
        # STEP 1: Fast HTTP check (no browser needed)
        health = check_url_health(url_to_check)
        if not health["valid"]:
            print(f"  [Validator] ❌ HTTP check failed: {health['reason']}")
            if attempt < max_retries:
                # Try to click a CTA on the current page
                found = await try_click_next_cta(page)
                if found:
                    continue
            break
        
        # STEP 2: Navigate to URL (if not already there)
        if page.url != url_to_check:
            # 🛡️ Guard: Check if page is closed
            if page.is_closed():
                return {"valid": False, "reason": "target_closed"}
                
            try:
                await page.goto(url_to_check,
                                wait_until="domcontentloaded",
                                timeout=20000)
                await asyncio.sleep(2.0)
            except Exception as e:
                print(f"  [Validator] Navigation failed: {e}")
                break
        
        # STEP 3: Content validation
        content_check = await validate_page_content(page)
        if not content_check["valid"]:
            print(f"  [Validator] ❌ Content check failed: "
                  f"{content_check['reason']}")
            if attempt < max_retries:
                found = await try_click_next_cta(page)
                if found:
                    continue
            break
        
        # STEP 4: Classify offer type
        offer_class = await classify_offer_type(page, page.url)
        
        print(f"  [Validator] ✅ Valid offer found!")
        print(f"  Type: {offer_class['offer_type']} "
              f"({offer_class['confidence']})")
        
        return {
            "valid": True,
            "final_offer_url": page.url,
            "offer_type": offer_class["offer_type"],
            "offer_type_confidence": offer_class["confidence"],
            "offer_signals": offer_class["top_signals"],
            "retry_count": attempt,
            "content_size": content_check.get("body_length"),
            "title": content_check.get("title"),
        }
    
    # All retries exhausted
    print(f"  [Validator] ⚠️ Could not find valid offer after "
          f"{max_retries + 1} attempts")
    return {
        "valid": False,
        "final_offer_url": None,
        "offer_type": "Unknown",
        "retry_count": max_retries,
        "reason": "max_retries_exhausted"
    }


async def try_click_next_cta(page) -> bool:
    """
    Try to find and click a CTA button on the current page
    to go deeper into the funnel.
    Returns True if navigation happened, False otherwise.
    """
    
    CTA_SELECTORS = [
        # Strong purchase CTAs
        "a:has-text('Order Now')", "button:has-text('Order Now')",
        "a:has-text('Buy Now')", "button:has-text('Buy Now')",
        "a:has-text('Get Yours')", "button:has-text('Get Yours')",
        "a:has-text('Claim')", "button:has-text('Claim')",
        "a:has-text('Check Availability')",
        "a:has-text('Add to Cart')", "button:has-text('Add to Cart')",
        "a:has-text('Continue')", "button:has-text('Continue')",
        "a:has-text('Yes')", "button:has-text('Yes!')",
        "a:has-text('Get Started')",
        # Generic
        "[class*='cta']", "[class*='btn-primary']",
        "[class*='order-btn']", "[class*='buy-btn']",
    ]
    
    current_url = page.url
    
    for selector in CTA_SELECTORS:
        try:
            # 🛡️ Guard: Check if page is still alive
            if page.is_closed():
                return False
                
            element = await page.query_selector(selector)
            if element:
                # 🛡️ Guard: Ensure element is still attached before clicking
                if not await element.is_visible():
                    continue

                text = await element.text_content() or ""
                # Skip non-CTA elements
                skip_words = ["disclaimer", "privacy", "terms",
                              "cookie", "©", "sitemap", "about",
                              "contact", "unsubscribe"]
                if any(w in text.lower() for w in skip_words):
                    continue
                
                print(f"  [Retry] Clicking: {text.strip()[:40]}")
                
                # 🛡️ Hardened scroll with timeout
                try:
                    await asyncio.wait_for(element.scroll_into_view_if_needed(), timeout=5.0)
                except Exception as e:
                    print(f"  [Retry] ⚠️ Scroll timeout (element might be invisible): {e}")
                
                await asyncio.sleep(0.5)
                
                try:
                    # 🛡️ CHECK: Is page still open?
                    if page.is_closed():
                        return False
                        
                    async with page.expect_navigation(
                        timeout=12000,
                        wait_until="domcontentloaded"
                    ):
                        await element.click()
                except Exception as e:
                    if "closed" in str(e).lower():
                        return False
                    pass
                
                await asyncio.sleep(2.0)
                new_url = page.url
                
                if new_url != current_url:
                    print(f"  [Retry] Navigated to: {new_url[:60]}")
                    return True
        except Exception:
            continue
    
    return False


# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# MAIN FUNCTION: validate_and_classify_offer()
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

async def validate_and_classify_offer(
    page,
    offer_url: str,
    landing_url: str
) -> dict:
    """
    Complete offer validation pipeline.
    
    Call this AFTER extracting offer_url from affiliate analysis.
    It validates the URL, classifies the offer type,
    and retries if needed.
    
    Returns complete offer intelligence dict.
    """
    
    print(f"  [Validator] Checking offer: {offer_url[:60]}")
    
    # Quick pre-check — is this obviously invalid?
    from utils.url_blacklist import is_valid_offer_url
    if not is_valid_offer_url(offer_url):
        print(f"  [Validator] ❌ Blacklisted URL — retrying...")
        # Navigate to landing page and try deeper
        try:
            await page.goto(landing_url,
                            wait_until="domcontentloaded",
                            timeout=25000)
            await asyncio.sleep(3.0)
        except Exception:
            pass
        
        result = await find_real_offer_with_retry(
            page=page,
            current_offer_url=offer_url,
            landing_url=landing_url,
            max_retries=2
        )
        return result
    
    # Full validation on the offer URL
    result = await find_real_offer_with_retry(
        page=page,
        current_offer_url=offer_url,
        landing_url=landing_url,
        max_retries=2
    )
    
    return result
