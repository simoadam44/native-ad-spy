import asyncio
from playwright.async_api import async_playwright
from mgid_crawler import scrape_mgid

async def test_pjmedia():
    async with async_playwright() as p:
        print("Launching independent Chrome browser...")
        try:
            browser = await p.chromium.launch(headless=True)
            # إعداد السياق مع تقنيات التخفي
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            from playwright_stealth import stealth_async
            page = await context.new_page()
            await stealth_async(page)
        except Exception as e:
            print(f"Error: {e}")
            return
            
        url = "https://pjmedia.com/vodkapundit/2026/03/23/are-you-ready-for-the-dems-2028-presidential-childhood-trauma-olympics-n4950953"
        print(f"Checking target: {url}")
        ads = await scrape_mgid(browser, url)
        
        print("\n--- Results ---")
        if ads:
            print(f"Found {len(ads)} ads!")
            for i, ad in enumerate(ads, 1):
                print(f"{i}. {ad.get('headline')} - {ad.get('advertiser')}")
        else:
            print("No ads found.")

if __name__ == "__main__":
    asyncio.run(test_pjmedia())
