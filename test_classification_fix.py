import asyncio
import json
from utils.ad_classifier import calculate_ad_score, is_arbitrage_site
from utils.url_blacklist import is_meaningful_url

async def test_fixes():
    print("--- 1. Testing URL Blacklist ---")
    urls = [
        "https://sync.taboola.com/sg/usersync?taboola_hm=123",
        "https://fastlane.rubiconproject.com/a/api/fastlane.json",
        "https://completejointcare.net/vsl/?hop=b1744"
    ]
    for url in urls:
        print(f"URL: {url[:60]}... -> Meaningful: {is_meaningful_url(url)}")

    print("\n--- 2. Testing Arbitrage Detector ---")
    # Case 1: healthyrehabcare.com (Arbitrage)
    arb_url_1 = "https://healthyrehabcare.com/trending/you-wont-believe-these-celebrities?v=35"
    arb_content_1 = "Trending Now. you might also like. Advertisement. Related articles."
    
    # Case 2: instantnewsupdate.net (Arbitrage)
    arb_url_2 = "https://instantnewsupdate.net/trending/are-these-a-listers-faking-heights/2"
    arb_content_2 = "Recommended for you. Share this article. 10 Celebs who... By John Doe, Jan 2024"

    # Case 3: completejointcare.net (Affiliate)
    aff_url = "https://completejointcare.net/vsl/?hop=b1744"
    aff_content = "Buy Now. Order Now. Click here to check the discount. Money back guarantee."

    for name, url, content in [("Arb 1", arb_url_1, arb_content_1), ("Arb 2", arb_url_2, arb_content_2), ("Aff 1", aff_url, aff_content)]:
        res = is_arbitrage_site(url, content)
        print(f"{name}: {res['ad_type']} (Score: {res['score']}) Signals: {', '.join(res['signals'])}")

if __name__ == "__main__":
    asyncio.run(test_fixes())
