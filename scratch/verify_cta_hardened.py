import asyncio
import os
import sys
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

# Add current directory to path
sys.path.append(os.getcwd())

from utils.lp_analyzer import click_cta_and_capture

async def verify_hardened_cta():
    # A SellerHop URL provided by the user that was incorrectly captured
    url = "https://hop.clickbank.net/sellerhop?vendor=jointvance&domain=wellnesssciencehub.com&affiliate=supaffcb&tid=288384&requestUrl=https%3A%2F%2Fwellnesssciencehub.com%2Fjointvance_cb%2Fvsl01mod%2F%3Faffiliate%3Dsupaffcb%26extclid%3Dd4vj7nuq6cvcrdrh3mtp9ef4%26tid%3D288384&extclid=d4vj7nuq6cvcrdrh3mtp9ef4"
    
    print(f"Testing Hardened Resolution for: {url}")
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        try:
            print("Navigating to lander...")
            await page.goto(url, wait_until="networkidle", timeout=60000)
            await asyncio.sleep(5) # Wait for page to fully load elements
            
            print("Running click_cta_and_capture...")
            result = await click_cta_and_capture(page)
            
            print("\n--- TEST RESULTS ---")
            print(f"CTA Found: {result['cta_found']}")
            print(f"CTA Text: {result['cta_text']}")
            print(f"Final Offer URL: {result['final_offer_url']}")
            
            print("\n--- REDIRECT CHAIN (Cleaned) ---")
            for i, r in enumerate(result['redirect_chain']):
                print(f"{i+1}. {r}")
                
            # Internal Verification: Check for .ts files in the chain
            has_ts = any(".ts" in r.lower() for r in result['redirect_chain'])
            if has_ts:
                print("\n- FAILED: .ts segments found in redirect chain!")
            else:
                print("\n- PASSED: No .ts segments in redirect chain.")
                
            # Verify if Final Offer is a known tracker or media file
            if ".ts" in result['final_offer_url'].lower() or "converteai.net" in result['final_offer_url']:
                 print("- FAILED: Final Offer is a media file/video hosting link!")
            else:
                 print("- PASSED: Final Offer is not a media file.")

        except Exception as e:
            print(f"Test Error: {e}")
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(verify_hardened_cta())
