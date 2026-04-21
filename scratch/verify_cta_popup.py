import asyncio
import os
import sys
import random
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# Add current directory to path to import utils
sys.path.append(os.getcwd())

from utils.lp_analyzer import click_cta_and_capture

async def test_cta_popup():
    urls = [
        "https://wellnessgaze.com/13592_dbt_t/?s=2673040405",
        "https://viewitquickly.online/video/?bemobdata=c%3D578da148-ed46-4928-93a5-29193ac24a5f"
    ]
    
    async with async_playwright() as p:
        # Launch with some human-like args
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        )
        
        for url in urls:
            print(f"\n--- Testing {url} ---")
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)
            try:
                print(f"Navigating to {url}...")
                await page.goto(url, wait_until="networkidle", timeout=60000)
                await asyncio.sleep(3)
                
                # Take a screenshot before click
                await page.screenshot(path=f"scratch/before_{url.split('/')[2]}.png")
                
                print("Running click_cta_and_capture...")
                result = await click_cta_and_capture(page, "Affiliate")
                
                # Take a screenshot after click
                await page.screenshot(path=f"scratch/after_{url.split('/')[2]}.png")
                
                print("\n--- Test Results ---")
                print(f"CTA Found: {result['cta_found']}")
                print(f"CTA Text: {result['cta_text']}")
                print(f"Final Offer URL: {result['final_offer_url']}")
                
                if result['final_offer_url'] != url:
                    print("SUCCESS: Final Offer URL is different from Landing Page URL.")
                else:
                    print("WARNING: Final Offer URL is the same as Landing Page URL.")
                    
                print(f"Redirect Chain Length: {len(result['redirect_chain'])}")
                if len(result['redirect_chain']) > 0:
                    print(f"Last URL in chain: {result['redirect_chain'][-1]}")
            except Exception as e:
                print(f"Error testing {url}: {e}")
            finally:
                await page.close()
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_cta_popup())
