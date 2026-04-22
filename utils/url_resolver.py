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

def resolve_url(url: str, max_redirects: int = 10) -> tuple:
    """
    Follows redirects and returns (final_url, redirect_chain).
    Compatible with MGID and Taboola crawlers.
    """
    if not url:
        return "", []
        
    redirect_chain = []
    current_url = url
    
    try:
        headers = {"User-Agent": USER_AGENTS[0]}
        # We use a session to track redirects manually so we can capture the chain
        with requests.Session() as session:
            session.max_redirects = max_redirects
            response = session.get(
                current_url,
                headers=headers,
                allow_redirects=True,
                timeout=15
            )
            
            for resp in response.history:
                redirect_chain.append(resp.url)
            
            final_url = response.url
            return final_url, redirect_chain
    except Exception as e:
        print(f"URL Resolution failed for {url}: {e}")
        return url, []

def resolve_real_url(url: str) -> str:
    """Legacy wrapper for resolve_url that only returns the final string."""
    final, _ = resolve_url(url)
    return final

if __name__ == "__main__":
    # Test
    test_url = "https://smeagol.revcontent.com/cv/v3/fake-id"
    print(f"Resolving: {test_url}")
    print(f"Final Real URL: {resolve_real_url(test_url)}")
