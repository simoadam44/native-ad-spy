import asyncio, os
from playwright.async_api import async_playwright

PROXY_CONFIG = {
    "server": "http://gw.dataimpulse.com:823",
    "username": "85ccde32f1cc6c7ad458__country-US",
    "password": "78c188c405598b8a"
}

async def test_resolve():
    url = "https://clck.mgid.com/ghits/23660602/i/57808524/0/src/950562051/pp/6/1"
    referer = "https://brainberries.co/interesting/britney-spears-then-vs-now-her-changing-face-in-photos/"
    
    print(f"DEBUG: Resolving {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, proxy=PROXY_CONFIG)
        context = await browser.new_context(
             user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
             viewport={"width": 390, "height": 844},
             is_mobile=True,
             has_touch=True
        )
        
        resolver_page = await context.new_page()
        await resolver_page.set_extra_http_headers({"Referer": referer})
        
        network_url = None
        async def catch(req):
            nonlocal network_url
            u = req.url
            if req.resource_type in ["document", "xhr", "fetch"]:
                print(f"Req: {u[:80]}")
                
            is_tracking = any(x in u.lower() for x in ["mgid.com", "adskeeper.com", "clck.", "ghits/", "cookielaw", "onetrust"])
            is_resource = any(x in u.lower() for x in [".png", ".jpg", ".jpeg", ".gif", ".css", ".js", ".woff2"])
            
            if req.resource_type in ["document", "xhr", "fetch"] and not is_tracking and not is_resource:
                from urllib.parse import urlparse
                try:
                    p = urlparse(u)
                    if p.netloc and "." in p.netloc and len(u) > 25:
                        network_url = u
                        print(f"CATCHED NETWORK: {u}")
                except: pass
        
        resolver_page.on("request", catch)
        
        try:
            print("Going to URL...")
            resp = await resolver_page.goto(url, wait_until="domcontentloaded", timeout=15000)
            if resp: print(f"Response status: {resp.status}")
            
            for _ in range(15):
                if network_url:
                    print(f"RETURNING NETWORK URL")
                    break
                curr = resolver_page.url
                if "mgid.com" not in curr and "clck." not in curr and len(curr) > 25: 
                    print(f"FOUND IN URL: {curr}")
                    break
                await asyncio.sleep(1)
                
            print(f"FINAL PAGE HTML (500 chars):\n {await resolver_page.content()} ")
        except Exception as e: print(f"Wait error: {e}")
        finally: await browser.close()

if __name__ == "__main__":
    asyncio.run(test_resolve())
