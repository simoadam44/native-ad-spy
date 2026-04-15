import asyncio
from playwright.async_api import async_playwright

async def test():
    async with async_playwright() as p:
        print("Launching browser...")
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        print("Navigating to target...")
        try:
            await page.goto("https://edition.cnn.com", timeout=30000)
            print("Title:", await page.title())
        except Exception as e:
            print("Error:", e)
        await browser.close()
        print("Done.")

if __name__ == "__main__":
    asyncio.run(test())
