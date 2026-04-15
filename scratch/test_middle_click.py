import asyncio
from playwright.async_api import async_playwright

PROXY_CONFIG = {
    "server": "http://gw.dataimpulse.com:823",
    "username": "85ccde32f1cc6c7ad458__country-US",
    "password": "78c188c405598b8a"
}

async def test_middle_click():
    publisher_url = "https://brainberries.co/interesting/britney-spears-then-vs-now-her-changing-face-in-photos/"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False, proxy=PROXY_CONFIG)
        context = await browser.new_context(
             user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
             viewport={"width": 1280, "height": 800}
        )
        
        page = await context.new_page()
        print("Going to publisher site...")
        try:
            await page.goto(publisher_url, wait_until="domcontentloaded", timeout=20000)
            await asyncio.sleep(5)
        except Exception as e:
            print("Timeout, but proceeding...")
            
        # Find MGID links
        links = await page.locator('.mgline a, .mgbox a, [id^="mgid_"] a').all()
        print(f"Found {len(links)} ads")
        
        if len(links) > 0:
            target_el = links[0]
            href = await target_el.get_attribute("href")
            print(f"Target href: {href}")
            
            # Setup new page listener
            async def handle_new_page(new_page):
                print(f"New page opened: {new_page.url}")
                # Wait for navigation
                try:
                    await new_page.wait_for_load_state("domcontentloaded", timeout=10000)
                except: pass
                print(f"Resolved new page URL: {new_page.url}")
                await new_page.close()
                
            context.on("page", lambda new_page: asyncio.create_task(handle_new_page(new_page)))
            
            # Middle click
            print("Clicking ad with Middle-Click...")
            await target_el.click(button="middle", timeout=5000)
            
            # Wait to observe the result
            await asyncio.sleep(15)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_middle_click())
