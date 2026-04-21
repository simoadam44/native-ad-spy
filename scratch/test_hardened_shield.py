"""Test: Hardened Shield - Verify that tracker URLs are ALWAYS blocked."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from utils.url_blacklist import is_meaningful_url
from utils.lp_analyzer import extract_target_from_params

# --- URLs that MUST be BLOCKED (return False) ---
MUST_BLOCK = [
    # Google Analytics with affiliate params echoed
    "https://www.google-analytics.com/g/collect?v=2&tid=G-LW27DEZ88B&dl=https%3A%2F%2Fgetretinaclear.com%2Fvideo%2F%3Faff_id%3D57967",
    "https://analytics.google.com/g/collect?v=2&tid=G-2GDKYWYCZF&dl=https%3A%2F%2Fpromo.iredirect.net&dt=Yukon%20Gold",
    # ClickBank sellerhop (tracker, not checkout)
    "https://hop.clickbank.net/sellerhop?vendor=2brainvex&domain=healthdailytipsforyou.com&affiliate=supaffcb&tid=289320&requestUrl=https%3A%2F%2Fhealthdailytipsforyou.com%2Fbrainhoney_cb%2Fvsl01_mod_ml94%2F",
    "https://hop.clickbank.net/sellerhop?vendor=jointvance&domain=wellnesssciencehub.com&affiliate=supaffcb",
    "https://hop.clickbank.net/sellerhop?vendor=slimpiic&domain=totalwellnessreportvitae.com&affiliate=supaffcb",
    # Digistore trusted-badge
    "https://www.digistore24.com/trusted-badge/34430/MmLKLbdgUoWZazW/salespage",
    # ClickBank tracking pixel
    "https://cbtb.clickbank.net/?vendor=jointgen",
    # Zendesk config (not a merchant page)
    "https://commercecore.zendesk.com/embeddable/config",
    # BidSwitch
    "https://x.bidswitch.net/sync?ssp=openx",
    # CDN resources
    "https://vt-h-1.b-cdn.net/x",
    # EveryAction tracking
    "https://secure.everyaction.com/v1/Track/q-hLRG7RpUu_0LzE40PZgA2?formSessionId=226224fb",
    # CheckoutChamp API (not a merchant landing page)
    "https://pages-live-api.checkoutchamp.com/providersApi/V1/SplitTest/clicks/b5626bc4",
]

# --- URLs that MUST PASS (return True) ---
MUST_PASS = [
    # Real merchant landing pages
    "https://wellnesssciencehub.com/jointvance_cb/vsl01mod/?affiliate=supaffcb",
    "https://healthdailytipsforyou.com/brainhoney_cb/vsl01_mod_ml94/?affiliate=supaffcb",
    "https://totalwellnessreportvitae.com/jellyburn_cb/vsl02/?affiliate=supaffcb",
    "https://completejointcare.net/vsl/?hop=b1744&hopId=34918f12",
    "https://getretinaclear.com/video/?aff_id=57967",
    "https://get-derila-ergo.com/tax-rates?vndr=evf&affiliate_id=2051",
    "https://mounjaboost.com/vsla/?aff_id=71627",
    # ClickBank PAY page (valid checkout)
    "https://memoryon.pay.clickbank.net/?cbitems=MEMO2BOTTLES&hop=dhmtmedia",
]

# --- extract_target_from_params tests ---
EXTRACTION_TESTS = [
    (
        "https://hop.clickbank.net/sellerhop?vendor=2brainvex&requestUrl=https%3A%2F%2Fhealthdailytipsforyou.com%2Fbrainhoney_cb%2Fvsl01_mod_ml94%2F%3Faffiliate%3Dsupaffcb",
        "https://healthdailytipsforyou.com/brainhoney_cb/vsl01_mod_ml94/?affiliate=supaffcb"
    ),
    (
        "https://hop.clickbank.net/sellerhop?vendor=jointvance&requestUrl=https%3A%2F%2Fwellnesssciencehub.com%2Fjointvance_cb%2Fvsl01mod%2F",
        "https://wellnesssciencehub.com/jointvance_cb/vsl01mod/"
    ),
]

print("=" * 60)
print("HARDENED SHIELD TEST SUITE")
print("=" * 60)

# Test 1: Blocked URLs
print("\n--- TEST 1: URLs that MUST be BLOCKED ---")
blocked_pass = 0
blocked_fail = 0
for url in MUST_BLOCK:
    result = is_meaningful_url(url)
    if result:
        print(f"  ❌ FAIL (should be blocked): {url[:80]}...")
        blocked_fail += 1
    else:
        print(f"  ✅ BLOCKED: {url[:80]}...")
        blocked_pass += 1

# Test 2: Allowed URLs
print("\n--- TEST 2: URLs that MUST PASS ---")
pass_pass = 0
pass_fail = 0
for url in MUST_PASS:
    result = is_meaningful_url(url)
    if not result:
        print(f"  ❌ FAIL (should pass): {url[:80]}...")
        pass_fail += 1
    else:
        print(f"  ✅ PASSED: {url[:80]}...")
        pass_pass += 1

# Test 3: Extraction
print("\n--- TEST 3: Parameter Extraction ---")
extract_pass = 0
extract_fail = 0
for input_url, expected in EXTRACTION_TESTS:
    result = extract_target_from_params(input_url)
    if result == expected:
        print(f"  ✅ EXTRACTED: {result[:80]}...")
        extract_pass += 1
    else:
        print(f"  ❌ FAIL: Expected {expected[:60]}...")
        print(f"          Got      {result[:60]}...")
        extract_fail += 1

# Summary
print("\n" + "=" * 60)
print("RESULTS SUMMARY")
print("=" * 60)
total_pass = blocked_pass + pass_pass + extract_pass
total_fail = blocked_fail + pass_fail + extract_fail
print(f"  Blocked URLs:  {blocked_pass}/{len(MUST_BLOCK)} passed")
print(f"  Allowed URLs:  {pass_pass}/{len(MUST_PASS)} passed")
print(f"  Extraction:    {extract_pass}/{len(EXTRACTION_TESTS)} passed")
print(f"  TOTAL:         {total_pass}/{total_pass + total_fail} passed")
if total_fail == 0:
    print("\n🛡️  ALL TESTS PASSED - HARDENED SHIELD IS ACTIVE! 🛡️")
else:
    print(f"\n⚠️  {total_fail} TESTS FAILED - NEEDS ATTENTION!")
