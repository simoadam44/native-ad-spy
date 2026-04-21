import asyncio
import os
import sys

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deep_analyzer import deep_analyze_ad

async def test_strict_rule():
    urls = [
        {
            "name": "Affiliate Lander (healthierlivingtips.org)",
            "url": "https://healthierlivingtips.org/int_jp_spl/?c=wnqbaf1roqf9qfqh3do1qi9k&rc_uuid=885d2d24-8586-4732-af4d-2e0bb6027e07",
            "title": "Surgeon Reveals: Simple Method Ends Joint Pain",
            "expected": "Affiliate"
        },
        {
            "name": "Publisher Site (Independent.co.uk)",
            "url": "https://www.independent.co.uk/bulletin/news/trump-jesus-image-blasphemy-b2958020.html",
            "title": "Donald Trump shares AI image of Jesus helping him in court",
            "expected": "Arbitrage"
        }
    ]
    
    for test in urls:
        print(f"\n--- Testing: {test['name']} ---")
        result = await deep_analyze_ad(random.randint(1000, 9999), test['url'], test['title'])
        
        print("\nAd Classification Result:")
        print(f"Type: {result.get('ad_type')}")
        print(f"Confidence: {result.get('confidence')}")
        print(f"Reason: {result.get('reason')}")
        print(f"Networks: {result.get('detected_ad_networks')}")
        
        if result.get('ad_type') == test['expected']:
            print(f"SUCCESS: Correctly classified as {test['expected']}.")
        else:
            print(f"FAILURE: Expected {test['expected']} but got {result.get('ad_type')}.")

if __name__ == "__main__":
    import random
    asyncio.run(test_strict_rule())
