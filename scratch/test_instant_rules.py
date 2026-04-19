import asyncio
import sys
import os

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.ad_classifier import get_ad_network_fingerprints, is_arbitrage_site
from deep_analyzer import classify_with_full_context

async def run_tests():
    print("Starting Instant Detection Rules Validation Tests...")
    
    # --- Stage 1 Test: Affiliate URL Params ---
    url_s1 = "https://healthierlivingtips.org/int_pp_spl_ee/?cep=TSo577&lptoken=123"
    res1 = await classify_with_full_context(url_s1, "Test Title", "", [], {})
    print(f"\n[Stage 1 Test] URL: {url_s1}")
    print(f"Result: {res1['ad_type']} (Stage {res1['stage']}) | Reason: {res1['reason']}")
    assert res1['ad_type'] == "Affiliate" and res1['stage'] == 1

    # --- Stage 2 Test: Ad Network Fingerprint ---
    content_s2 = '<script async src="https://pagead2.googlesyndication.com/pagead/js/adsbygoogle.js">'
    res2 = await classify_with_full_context("https://test.com", "Title", content_s2, [], {})
    print(f"\n[Stage 2 Test] Content with AdSense snippet")
    print(f"Result: {res2['ad_type']} (Stage {res2['stage']}) | Network: {res2.get('detected_ad_networks')}")
    assert res2['ad_type'] == "Arbitrage" and res2['stage'] == 2

    # --- Stage 3 Test: Pagination ---
    url_s3 = "https://healthyrehabcare.com/trending/celebrities/35"
    structure_s3 = {"is_paginated": True, "page_number": 35}
    res3 = await classify_with_full_context(url_s3, "Trending Celebs", "", [], structure_s3)
    print(f"\n[Stage 3 Test] URL with page 35")
    print(f"Result: {res3['ad_type']} (Stage {res3['stage']}) | Reason: {res3['reason']}")
    assert res3['ad_type'] == "Arbitrage" and res3['stage'] == 3

    # --- Stage 5 Test: Content Scoring ---
    content_s5 = "you might also like... related articles... share this... disqus_config"
    res5 = is_arbitrage_site("https://example.com/trending/", content_s5, [])
    print(f"\n[Stage 5 Test] Arbitrage Content Signals")
    # Score details
    print(f"Result: {res5['is_arbitrage']} | Score: {res5['score']} | Signals: {res5['signals']}")
    assert res5['is_arbitrage'] == True
    
    # --- Bug Fix Test: Variable Naming ---
    try:
        result = is_arbitrage_site("https://test.com", "content", [])
        assert "score" in result
        print("\nNameError bug fixed (variable 'score' used correctly)")
    except NameError as e:
        print(f"\nBug still present: {e}")
        exit(1)

    print("\nALL TESTS PASSED!")

if __name__ == "__main__":
    asyncio.run(run_tests())
