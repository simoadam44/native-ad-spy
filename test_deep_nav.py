import asyncio
from utils.deep_navigator import _looks_like_offer_url

def run_tests():
    print("Running Deep Navigator Tests...")
    
    # Test 4: _looks_like_offer_url
    assert _looks_like_offer_url("https://completejointcare.net/vsl/?hop=b1744") == True, "Failed Test 4a"
    assert _looks_like_offer_url("https://sync.taboola.com/sg/xxx") == False, "Failed Test 4b"
    assert _looks_like_offer_url("https://challenges.cloudflare.com/cdn-cgi") == False, "Failed Test 4c"
    
    print("All synchronous tests pass. For full browser tests, run deep analyzer directly.")

if __name__ == "__main__":
    run_tests()
