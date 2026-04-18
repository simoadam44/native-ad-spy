import requests
import re
import os
from urllib.parse import urlparse

# Common User-Agents to bypass simple blocks
USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/118.0.0.0 Safari/537.36",
    "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
]

TRACKER_REDIRECT_DOMAINS = [
    "smeagol.revcontent.com",
    "revcontent.com/cv/",
    "trc.taboola.com",
    "taboola.com/cr/",
    "mgid.com/ghits",
    "mgid.com/redir",
    "outbrain.com/network/redir",
    "paid.outbrain.com",
    "clktrk.",
    "trk.",
    "track.",
    "rdtk.io",
    "voluum.com",
    "bemob.com",
]

def resolve_real_url(url: str) -> str:
    """
    Follows tracker redirect URLs to get the real landing page URL.
    Uses requests.head for speed.
    """
    if not url:
        return url
        
    parsed = urlparse(url)
    domain = parsed.netloc.lower()
    
    # Check if URL belongs to a known tracker
    is_tracker = any(t in domain or t in url for t in TRACKER_REDIRECT_DOMAINS)
    
    if not is_tracker:
        return url
        
    print(f"Targeting Tracker Redirect: {domain}...")
    try:
        headers = {"User-Agent": USER_AGENTS[0]}
        # Follow redirects with a limit of 5 and timeout of 10s
        response = requests.head(
            url, 
            headers=headers, 
            allow_redirects=True, 
            timeout=10,
            max_redirects=5
        )
        return response.url
    except Exception as e:
        print(f"Tracker resolution failed: {e}. Using original URL.")
        return url

if __name__ == "__main__":
    # Test
    test_url = "https://smeagol.revcontent.com/cv/v3/fake-id"
    print(f"Resolving: {test_url}")
    print(f"Final Real URL: {resolve_real_url(test_url)}")
