import asyncio
import os
import sys
from playwright.async_api import async_playwright

async def debug_cta():
    url = "https://wellnessgaze.com/13592_dbt_t/?s=2673040405"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page()
        print(f"Navigating to {url}...")
        await page.goto(url, wait_until="networkidle", timeout=60000)
        
        selectors = "a, button, [role='button'], [class*='btn'], [class*='button']"
        elements = await page.query_selector_all(selectors)
        
        for el in elements:
            text = await el.inner_text()
            if "Watch The Full Video" in text:
                html = await el.evaluate("el => el.outerHTML")
                print(f"FOUND CTA HTML: {html}")
                
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_cta())
