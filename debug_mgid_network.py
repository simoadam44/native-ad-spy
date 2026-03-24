import sys; sys.stdout.reconfigure(encoding='utf-8')
import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        try:
            browser = await p.chromium.connect_over_cdp('http://localhost:9222')
        except:
            print("Failed to connect to browser on 9222")
            return
            
        context = browser.contexts[0]
        page = await context.new_page()
        print("Page opened. Listening to network...")
        
        def handle_res(res):
            try:
                if 'mgid' in res.url.lower():
                    print(f"MGID Network Request: {res.url}")
            except: pass
            
        page.on('response', handle_res)
        try:
            print("Navigating to pjmedia...")
            await page.goto('https://pjmedia.com/vodkapundit/2026/03/23/are-you-ready-for-the-dems-2028-presidential-childhood-trauma-olympics-n4950953', timeout=45000)
        except Exception as e:
            print(f"Timeout: {e}")
            
        print("Waiting 10 seconds for late requests...")
        await asyncio.sleep(10)
        await page.close()

if __name__ == '__main__':
    asyncio.run(run())
