import asyncio
from playwright.async_api import async_playwright
from mgid_crawler import scrape_mgid

async def test_pjmedia():
    async with async_playwright() as p:
        print("Connecting to open Chrome browser (CDP)...")
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        except Exception as e:
            print("Failed to connect to Chrome. Open it with --remote-debugging-port=9222")
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
