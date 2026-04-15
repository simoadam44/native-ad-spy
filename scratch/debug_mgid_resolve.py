import asyncio
from playwright.async_api import async_playwright
import os

async def debug_resolve():
    # User's sample link
    url = "https://clck.mgid.com/ghits/21642847/i/57388854/0/src/645596367/pp/6/1"
    referer = "https://herbeauty.co/ar/altarfih/maqati-video-raqs-zouk-lan-tastatia-at-tawaqquf-an-mushahadatiha-miraran-wa-takraran/"
    
    async with async_playwright() as p:
        # Use a real Chrome-like UA
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
            viewport={"width": 390, "height": 844},
            is_mobile=True,
            has_touch=True
        )
        page = await context.new_page()
        
        print(f"DEBUG: Attempting to resolve: {url}")
        
        # Track all requests to see where it goes
        resolved_url = None
        
        def handle_request(req):
             nonlocal resolved_url
             r_url = req.url.lower()
             if "mgid.com" not in r_url and "adskeeper.com" not in r_url and req.resource_type == "document":
                 if not resolved_url or len(r_url) > len(resolved_url):
                     resolved_url = req.url
                     print(f"REQUEST -> {req.url}")

        page.on("request", handle_request)
        
        try:
            await page.set_extra_http_headers({"Referer": referer})
            await page.goto(url, wait_until="commit", timeout=15000)
            
            # Wait for some time to catch JS redirects or meta refreshes
            for _ in range(10):
                await asyncio.sleep(1)
                curr = page.url
                if "mgid.com" not in curr and "ploynest.com" not in curr:
                    print(f"FOUND IN PAGE.URL: {curr}")
                    break
            
            print(f"FINAL RESULT: {page.url}")
        except Exception as e:
            print(f"ERROR: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_resolve())
