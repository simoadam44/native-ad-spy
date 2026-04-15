import asyncio
from playwright.async_api import async_playwright

async def main():
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        url = "https://www.telegraph.co.uk/news/"
        
        async def handle_resp(res):
            try:
                u = res.url.lower()
                if "outbrain" in u:
                    print(f"OB REQ: {u[:150]}")
            except: pass
            
        page.on("response", handle_resp)
        
        print(f"Loading {url}")
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except: pass
        
        print("Scrolling...")
        for i in range(15):
            await page.evaluate(f"window.scrollBy(0, 800)")
            await asyncio.sleep(1)
            
        ob_html = await page.evaluate("""
            () => {
                let div = document.querySelector('.OUTBRAIN, [id^="outbrain"]');
                return div ? div.innerHTML : "Not found";
            }
        """)
        print(f"OB DIV HTML: {ob_html[:500]}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
