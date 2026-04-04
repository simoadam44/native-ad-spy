import asyncio
from playwright.async_api import async_playwright

async def test_resolve():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context()
        url = "https://clck.mgid.com/ghits/22901698/i/57388853/0/src/645596367/pp/4/1"
        source = "https://buzzday.info/"
        print(f"Requesting {url} with referer {source}")
        
        # Test HTTP redirect via APIRequestContext
        try:
            req = await context.request.get(url, headers={"Referer": source})
            print(f"APIRequestContext URL: {req.url}")
            print(f"Status: {req.status}")
        except Exception as e:
            print(f"APIRequestContext Error: {e}")
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_resolve())
