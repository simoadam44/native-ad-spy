import sys
import os
sys.path.append(os.getcwd())

from utils.ad_classifier import classify_ad

def test_mechanics():
    cases = [
        ("https://sportpirate.com/trending/von-berlin/2", "Celeb Story", "Arbitrage"),
        ("https://herbeauty.co/tr/lifestyle/muz", "Banana Article", "Arbitrage"),
        ("https://tradingblvd.com/news/celebs", "News Story", "Arbitrage"),
        ("https://best-offer.com/page/5", "Listicle", "Arbitrage"),
        ("https://secure.checkout.com/buy", "Main Product", "Affiliate")
    ]
    
    print("Testing Classification Logic Hardening...")
    for url, title, expected in cases:
        res = classify_ad(url, title)
        passed = res['ad_type'] == expected
        status = "✅ PASS" if passed else "❌ FAIL"
        print(f"[{status}] URL: {url} | Result: {res['ad_type']} (Confidence: {res['confidence']})")

if __name__ == "__main__":
    test_mechanics()
