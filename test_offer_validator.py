import asyncio
from utils.offer_validator import check_url_health

def run_tests():
    print("Running Validator Tests...")
    
    # Test 1: optivell.site rejected by HTTP check
    print("\nTest 1: HTTP check for internal dashboard")
    health = check_url_health("https://optivell.site/opv-site/cards")
    print(f"Result: {health}")
    assert health["valid"] == False or health.get("content_size_kb", 0) < 5, "Failed Test 1: optivell.site should be rejected or have thin content"
    print("Test 1 PASS")
    
    print("\nAll synchronous tests pass. For browser tests, run deep analyzer directly.")

if __name__ == "__main__":
    run_tests()
