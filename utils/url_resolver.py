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

def resolve_url(url: str, max_redirects: int = 5, timeout: int = 10) -> tuple[str, list[str]]:
    """
    Follows redirects and returns (final_url, full_redirect_chain).
    """
    if not url or not url.startswith("http"):
        return url, [url]

    headers = {
        "User-Agent": USER_AGENTS[0],
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
        "Accept-Language": "en-US,en;q=0.9",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1"
    }

    try:
        # Using the Datacenter Proxy for resolution
        proxy_url = "http://7dce367ee7442e94dcd3:30243fe81b50b2de@gw.dataimpulse.com:823"
        proxies = {"http": proxy_url, "https": proxy_url}
        
        session = requests.Session()
        session.proxies.update(proxies)
        
        # Follow redirects and capture the history
        response = session.get(url, headers=headers, allow_redirects=True, timeout=timeout, stream=True)
        
        # Build the chain: list of all intermediate URLs + the final one
        redirect_chain = [resp.url for resp in response.history] + [response.url]
        final_url = response.url
        
        return final_url, redirect_chain
        
    except Exception:
        return url, [url]

if __name__ == "__main__":
    # Test
    test_url = "https://clck.mgid.com/j/some-fake-id"
    print(f"Resolving: {test_url}")
    print(f"Final: {resolve_url(test_url)}")
