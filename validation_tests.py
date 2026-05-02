
import asyncio
from utils.url_blacklist import is_valid_offer_url
from utils.url_resolver import is_tracking_redirect, extract_real_url_from_ad_server

def test_validation():
    print("Running Validation Tests...")
    
    # Test 1: Cloudflare challenge rejected
    res1 = is_valid_offer_url("https://challenges.cloudflare.com/cdn-cgi/challenge-platform/h/g/pat/9f58a6bf")
    print(f"Test 1 (Cloudflare rejected): {'PASS' if res1 == False else 'FAIL'}")

    # Test 2: trkflstr rejected as offer, added to trackers
    res2a = is_valid_offer_url("https://trkflstr.com/click")
    res2b = is_tracking_redirect("https://trkflstr.com/click")
    print(f"Test 2a (trkflstr not offer): {'PASS' if res2a == False else 'FAIL'}")
    print(f"Test 2b (trkflstr is tracker): {'PASS' if res2b == True else 'FAIL'}")

    # Test 3: optivell.site/opv-site/cards rejected
    res3 = is_valid_offer_url("https://optivell.site/opv-site/cards")
    print(f"Test 3 (optivell cards rejected): {'PASS' if res3 == False else 'FAIL'}")

    # Test 4: idealmedia URL extraction works
    url = "https://servicer.idealmedia.io/1676487/1?cxurl=https%3A%2F%2Fvsn.ua%2Fnews%2Fpoliyte-geran&lu=https%3A%2F%2Fvsn.ua%2Fnews%2Fpoliyte-geran"
    real = extract_real_url_from_ad_server(url)
    print(f"Test 4 (IdealMedia extraction): {'PASS' if 'vsn.ua' in real else 'FAIL'}")

if __name__ == "__main__":
    test_validation()
