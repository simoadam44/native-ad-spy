import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def debug_mgid_target():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            viewport={"width": 1920, "height": 1080}
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)

        print("Navigating to https://www.thegatewaypundit.com/ ...")
        
        async def handle_response(response):
            try:
                if "mgid" in response.url.lower():
                    print(f"Intercepted MGID: {response.url}")
            except Exception as e:
                pass

        page.on("response", handle_response)
        
        try:
            await page.goto("https://www.thegatewaypundit.com/", wait_until="domcontentloaded", timeout=45000)
            await asyncio.sleep(5)
            for i in range(5):
                await page.evaluate(f"window.scrollBy(0, 1000)")
                await asyncio.sleep(2)
        except Exception as e:
            pass
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_mgid_target())
