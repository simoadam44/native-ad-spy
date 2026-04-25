import requests
import re
import os
import concurrent.futures
from urllib.parse import urlparse

# Common User-Agents to bypass simple blocks
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
]

# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
# TRACKING REDIRECT DOMAINS TO FOLLOW
# ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

TRACKING_REDIRECT_DOMAINS = [
    # Outbrain
    "tr.outbrain.com",           # cachedClickId redirects
    "paid.outbrain.com",
    "ob.outbrain.com",
    "outbrain.com/network/redir",

    # Taboola
    "trc.taboola.com",
    "clk.taboola.com",
    "taboola.com/cr/",

    # Revcontent
    "smeagol.revcontent.com",
    "revcontent.com/click",
    "revcontent.com/cv/",

    # MGID
    "mgid.com/ghits",
    "mgid.com/redir",

    # Generic trackers
    "voluum.com",
    "voluumtrk.com",
    "rdtk.io",
    "bemob.com",
    "keitaro.io",
    "thrivetracker.com",
    "clkmg.com",
    "clkmr.com",
    "clktrk.",
    "trk.",
    "track.",
    "trc.",
    "click.",

    # Specific Trackers identified by user
    "trendingboom.com",
    "trendygadgetreviews.com",
    "genius-markets.com",
    "geniustech-magazine.com",
    "gphops.site",
    "syndicatedsearch.goog",
    "healthtrending.org",
    "healthheadlines.info",
    "dailyactunews.com",
    "novatrendnews.com",
    "prough-veridated.icu",
    "prouseum-cheads.xyz",
    "rejuvacare.com",
    "adtrafficquality.google",
    "googlesyndication.com",

    # ClickBank intermediate
    "hop.clickbank.net",

    # Affiliate networks
    "maxbounty.com/links",
    "shareasale.com/r.",
    "awin1.com/cread.php",
    "linksynergy.com/click",
    "cj.com/click",
    "impact.com/click",
    "impactradius.com/click",
    "pxf.io/click",
    "everflow.com",
    "evf.com",
]

def is_tracking_redirect(url: str) -> bool:
    """Check if URL is a tracking redirect that hides real destination."""
    if not url: return False
    u_lower = url.lower()
    domain = urlparse(u_lower).netloc
    
    # Check domains and specific paths
    for tracking_domain in TRACKING_REDIRECT_DOMAINS:
        if tracking_domain in u_lower:
            return True
    return False

def resolve_tracking_url(url: str, timeout: int = 15, max_redirects: int = 10) -> dict:
    """
    Follows a tracking redirect URL and returns the real destination.
    Uses requests (fast, no browser needed for simple redirects).
    """
    if not is_tracking_redirect(url):
        return {"resolved": False, "original": url, "final": url, "reason": "not_a_tracking_domain"}
    
    headers = {
        "User-Agent": USER_AGENTS[0],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
    }
    
    try:
        # We use a session to track redirects manually
        with requests.Session() as session:
            session.max_redirects = max_redirects
            response = session.get(
                url,
                headers=headers,
                allow_redirects=True,
                timeout=timeout
            )
            
            final_url = response.url
            
            if final_url == url and len(response.history) == 0:
                return {
                    "resolved": False,
                    "original": url,
                    "final": url,
                    "reason": "no_redirect_occurred"
                }
            
            return {
                "resolved": True,
                "original": url,
                "final": final_url,
                "redirect_count": len(response.history),
                "status_code": response.status_code,
                "redirect_chain": [r.url for r in response.history]
            }
            
    except requests.exceptions.TooManyRedirects:
        return {"resolved": False, "original": url, "final": url, "reason": "too_many_redirects"}
    except requests.exceptions.Timeout:
        return {"resolved": False, "original": url, "final": url, "reason": "timeout"}
    except Exception as e:
        return {"resolved": False, "original": url, "final": url, "reason": str(e)[:80]}

def resolve_tracking_url_batch(urls: list) -> dict:
    """
    Resolve multiple tracking URLs in parallel.
    Returns dict: {original_url: resolved_url}
    """
    results = {}
    
    # Filter unique URLs to resolve
    unique_urls = list(set(urls))
    to_resolve = [u for u in unique_urls if is_tracking_redirect(u)]
    to_keep = [u for u in unique_urls if not is_tracking_redirect(u)]
    
    # Keep non-tracking URLs as-is
    for url in to_keep:
        results[url] = url
    
    # Resolve tracking URLs in parallel
    if to_resolve:
        with concurrent.futures.ThreadPoolExecutor(max_workers=5) as executor:
            future_to_url = {
                executor.submit(resolve_tracking_url, url): url
                for url in to_resolve
            }
            for future in concurrent.futures.as_completed(future_to_url):
                original = future_to_url[future]
                try:
                    result = future.result()
                    results[original] = result["final"]
                except:
                    results[original] = original
    
    return results

def resolve_url(url: str, max_redirects: int = 10) -> tuple:
    """Legacy support for existing crawlers: returns (final_url, redirect_chain)"""
    res = resolve_tracking_url(url, max_redirects=max_redirects)
    if res["resolved"]:
        return res["final"], res["redirect_chain"]
    return url, []

def resolve_real_url(url: str) -> str:
    """Legacy wrapper for resolve_url that only returns the final string."""
    res = resolve_tracking_url(url)
    return res["final"]

if __name__ == "__main__":
    # Test 1: Detect Outbrain tracking URL
    test_url = "https://tr.outbrain.com/cachedClickId?marketerId=008dfd44af69a46f94530c32ffbe21e8bc"
    print(f"Testing resolution of: {test_url}")
    result = resolve_tracking_url(test_url)
    print(f"Resolved: {result['resolved']}")
    print(f"Final URL: {result['final']}")
