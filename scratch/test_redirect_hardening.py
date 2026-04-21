import asyncio
from playwright.async_api import async_playwright
from utils.lp_analyzer import analyze_landing_page_with_page
from utils.offer_extractor import extract_offer_intelligence
import json

async def test_redirect():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        context = await browser.new_context()
        page = await context.new_page()

        # This is a sample click tracking link that redirects to a landing page, then possibly another
        test_url = "https://smeagol.revcontent.com/cv/v3/L_ZsMrIw4J6RRjD3Xlq_QZ5UIfT2E5w0L55S2XkMkqQzK7_a6w2T9TqYqD3Xlq_QZ5UIfT2XkMkqQzK7_a6"
        
        print(f"Testing URL: {test_url}")
        
        result = await analyze_landing_page_with_page(page, test_url)
        
        print("\n--- LP Analyzer Result ---")
        print(f"Final Offer URL: {result.get('final_offer_url')}")
        print(f"Clean Redirect Chain: {result.get('clean_redirect_chain')}")
        
        extractor_res = extract_offer_intelligence(result.get("final_offer_url"), result.get("clean_redirect_chain"), test_url)
        print("\n--- Offer Extractor Result ---")
        print(json.dumps(extractor_res, indent=2))
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(test_redirect())
