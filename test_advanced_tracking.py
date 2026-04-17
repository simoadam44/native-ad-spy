import asyncio
from playwright.async_api import async_playwright
import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from utils.lp_analyzer import analyze_landing_page_with_page
from utils.param_extractor import extract_affiliate_params

async def stress_test():
    urls = [
        # GiddyUp / Custom Tracker style
        "https://wellnesspeek.com/lifehacks_001/",
        # Standard VSL / ClickBank style (Approximate)
        "https://healthierlivingtips.org/int_jp_spl/",
        # Common pre-lander / Advertorial
        "https://hot.healthtrending.org/v608558-en-V4/index.php"
    ]

    print("🚀 Starting Advanced Intelligence Stress Test")
    print("="*60)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            viewport={"width": 1280, "height": 800}
        )
        
        for idx, url in enumerate(urls, 1):
            print(f"\n[{idx}/3] Analyzing: {url[:60]}...")
            page = await context.new_page()
            
            try:
                # 1. Analyze Landing Page
                lp_data = await analyze_landing_page_with_page(page, url)
                
                # 2. Extract final URL params
                final_url = lp_data.get("final_offer_url", url)
                print(f"   -> Final URL Resolved: {final_url[:80]}...")
                
                # 3. Network & Param Extraction
                params = extract_affiliate_params(final_url)
                
                print("   📊 Extraction Results:")
                print(f"      - CTA Found:        {lp_data.get('cta_text')}")
                print(f"      - Subtype:          {lp_data.get('page_subtype')}")
                print(f"      - Detected Network: {params.get('detected_network')}")
                print(f"      - Affiliate ID:     {params.get('affiliate_id')}")
                print(f"      - Offer ID:         {params.get('offer_id')}")
                
            except Exception as e:
                print(f"   ❌ Error: {e}")
            finally:
                await page.close()

        await browser.close()
    print("\n✅ Stress Test Completed!")

if __name__ == "__main__":
    asyncio.run(stress_test())
