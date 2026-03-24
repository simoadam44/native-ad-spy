import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def debug_mgid():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        print("Navigating to https://www.dailymail.co.uk/news/index.html ...")
        
        async def handle_response(response):
            if "outbrain.com" in response.url.lower() and response.status == 200:
                print(f"Ad Request: {response.url}")
                try:
                    data = await response.json()
                    print(f"JSON Keys: {data.keys() if isinstance(data, dict) else type(data)}")
                    if isinstance(data, dict) and 'response' in data:
                        print(f"Response keys: {data['response'].keys()}")
                        if 'documents' in data['response']:
                            print(f"Found {len(data['response']['documents'])} documents")
                            if len(data['response']['documents']) > 0:
                                print(f"First doc keys: {data['response']['documents'][0].keys()}")
                except Exception as e:
                    print(f"Could not parse JSON: {e}")

        page.on("response", handle_response)
        
        try:
            await page.goto("https://www.dailymail.co.uk/news/index.html", wait_until="domcontentloaded", timeout=45000)
            print("Loaded. Scrolling...")
            for i in range(5):
                await page.evaluate(f"window.scrollBy(0, 1000)")
                await asyncio.sleep(2)
            
            # Check frames
            print(f"Frames count: {len(page.frames)}")
            for f in page.frames:
                if "mgid" in f.url or "outbrain" in f.url:
                    print(f"Ad iframe: {f.url}")
            
            await page.screenshot(path="dailymail_debug.png", full_page=True)
            print("Screenshot saved to dailymail_debug.png")
            
        except Exception as e:
            print(f"Error: {e}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_mgid())
