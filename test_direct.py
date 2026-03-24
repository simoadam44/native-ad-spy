import asyncio
from playwright.async_api import async_playwright

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # استخدام User Agent حقيقي لمتصفح Chrome على ويندوز
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        print("🔍 محاولة اختراق حماية MGID...")
        await page.goto("https://www.standard.co.uk", wait_until="networkidle")
        
        # البحث عن أي رابط يحتوي على كلمة mgid
        links = await page.locator('a[href*="mgid.com"]').all()
        print(f"✅ تم العثور على {len(links)} إعلان محتمل!")
        
        for link in links[:5]:
            title = await link.inner_text()
            href = await link.get_attribute("href")
            print(f"Found: {title[:50]} -> {href[:50]}")
            
        await browser.close()

asyncio.run(run())
