import asyncio
from playwright.async_api import async_playwright

PROXY_CONFIG = {
    "server": "http://gw.dataimpulse.com:823",
    "username": "85ccde32f1cc6c7ad458__country-US",
    "password": "78c188c405598b8a"
}

async def test_iframe():
    publisher_url = "https://brainberries.co/interesting/britney-spears-then-vs-now-her-changing-face-in-photos/"
    tracking_url = "https://clck.mgid.com/ghits/23660602/i/57808524/0/src/950562051/pp/6/1"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, proxy=PROXY_CONFIG)
        context = await browser.new_context(
             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        )
        page = await context.new_page()
        
        # We need to catch the iframe network requests
        network_resolved = None
        async def catch_req(req):
            nonlocal network_resolved
            # If the request matches a document and doesn't belong to tracking domains
            u = req.url
            if req.resource_type in ["document", "sub_document"] and "mgid.com" not in u and "adskeeper" not in u:
                if len(u) > 25:
                    network_resolved = u
                    print(f"CATCHED REDIRECT IN IFRAME: {u}")
                    
        page.on("request", catch_req)
        
        print("Visiting publisher...")
        try:
            await page.goto(publisher_url, timeout=15000)
        except: pass
        
        print("Injecting Iframe...")
        await page.evaluate(f"""
            const iframe = document.createElement('iframe');
            iframe.style.display = 'none';
            iframe.src = '{tracking_url}';
            document.body.appendChild(iframe);
        """)
        
        for _ in range(10):
            if network_resolved:
                print(f"SUCCESS: {network_resolved}")
                break
            await asyncio.sleep(1)
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_iframe())
