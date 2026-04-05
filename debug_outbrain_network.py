import asyncio
from playwright.async_api import async_playwright
import json
import re

async def debug_outbrain_network():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        print("🔍 Scanning for Outbrain network traffic on independent.co.uk...")

        async def handle_response(response):
            try:
                url = response.url.lower()
                if "outbrain.com" in url and ("get" in url or "recommendations" in url or "widget" in url):
                    print(f"✅ Intercepted Response: {url[:100]}...")
                    status = response.status
                    content_type = response.headers.get("content-type", "")
                    print(f"   Status: {status}, Type: {content_type}")
                    
                    if status == 200 and ("json" in content_type or "javascript" in content_type):
                        text = await response.text()
                        print(f"   Preview (100 chars): {text[:100]}")
                        
                        # Check for JSON patterns
                        if "documents" in text or "doc" in text or "ads" in text:
                            print("   ⭐ POTENTIAL AD DATA FOUND!")
            except Exception as e:
                pass

        page.on("response", handle_response)
        
        try:
            # We must scroll to trigger Outbrain (it's often lazy-loaded)
            await page.goto("https://www.independent.co.uk/news/world/americas/us-politics/trump-2024-election-live-updates-b2518428.html", wait_until="networkidle", timeout=60000)
            print("📜 Scrolling down to trigger widgets...")
            for _ in range(10):
                await page.evaluate("window.scrollBy(0, 800)")
                await asyncio.sleep(2)
        except Exception as e:
            print(f"❌ Error during navigation: {e}")
        
        print("🏁 Scant complete.")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_outbrain_network())
