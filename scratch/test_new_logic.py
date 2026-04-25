import sys
import os

# Mock Supabase env vars before importing deep_analyzer
os.environ["SUPABASE_URL"] = "https://placeholder.supabase.co"
os.environ["SUPABASE_KEY"] = "placeholder_key"

# Add parent directory to path to import utils
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.url_resolver import is_tracking_redirect, resolve_tracking_url
from deep_analyzer import clean_url_for_storage, strip_tracking_params

def run_tests():
    print("Running URL Resolution & Cleaning Validation Tests...")
    
    # Test 1: Detect Outbrain tracking URL
    url1 = "https://tr.outbrain.com/cachedClickId?marketerId=008dfd44af69a46f94530c32ffbe21e8bc"
    print(f"Test 1: is_tracking_redirect('{url1[:40]}...')")
    assert is_tracking_redirect(url1) == True
    print("  [OK] Passed")

    # Test 2: Resolve returns different URL
    # Note: This requires network access, so we'll just check if it attempts to resolve
    print(f"Test 2: resolve_tracking_url('{url1[:40]}...')")
    result = resolve_tracking_url(url1)
    print(f"  Result resolved: {result['resolved']}")
    if result["resolved"]:
        print(f"  [OK] Resolved tracking URL -> {result['final'][:60]}...")
        assert "outbrain.com" not in result["final"]
        assert result["final"].startswith("http")
    else:
        print(f"  [WARN] Resolution failed (might be network/proxy issue): {result.get('reason')}")
    print("  [OK] Completed")

    # Test 3: Normal URL passes through unchanged
    url3 = "https://getretinaclear.com/video/?aff_id=57967"
    print(f"Test 3: clean_url_for_storage('{url3}')")
    cleaned3 = clean_url_for_storage(url3)
    assert cleaned3 == url3
    print("  [OK] Passed")

    # Test 4: Strip UTM params but keep affiliate params
    url4 = "https://offer.com/?aff_id=123&utm_source=taboola&fbclid=abc"
    print(f"Test 4: strip_tracking_params('{url4}')")
    cleaned4 = strip_tracking_params(url4)
    assert "aff_id=123" in cleaned4
    assert "utm_source" not in cleaned4
    assert "fbclid" not in cleaned4
    print("  [OK] Passed")

    print("\nAll validation tests finished!")

if __name__ == "__main__":
    run_tests()
