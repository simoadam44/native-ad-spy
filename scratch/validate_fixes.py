"""
Validation Tests for all 6 Bug Fixes (ASCII-safe output for Windows console).
Run from the project root: py scratch/validate_fixes.py
"""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def ok(msg): print(f"  [PASS] {msg}")
def fail(msg): print(f"  [FAIL] {msg}"); sys.exit(1)

print("=" * 60)
print("VALIDATION SUITE - 6 Bug Fixes")
print("=" * 60)

# -----------------------------------------------------------------
# Bug 1: tldextract imports cleanly without network access
# -----------------------------------------------------------------
print("\n[Bug 1] Testing offline-safe tldextract import...")
import importlib
for mod_name in ["utils.offer_extractor", "utils.lp_analyzer", "deep_analyzer"]:
    try:
        importlib.import_module(mod_name)
        ok(f"{mod_name} imported OK")
    except Exception as e:
        fail(f"{mod_name} FAILED: {e}")

from utils.offer_extractor import _extract_domain
tests = [
    ("https://getretinaclear.com/video/?aff_id=57967", "getretinaclear.com"),
    ("https://hop-apps.clickbank.net?errCode=nowhitelist", "clickbank.net"),
    ("", ""),
]
for url, expected in tests:
    got = _extract_domain(url)
    if got == expected:
        ok(f"_extract_domain({url[:40]!r}) == {expected!r}")
    else:
        fail(f"_extract_domain({url[:40]!r}) expected {expected!r}, got {got!r}")

# None case
try:
    got = _extract_domain(None)
    if got == "":
        ok("_extract_domain(None) == ''")
    else:
        fail(f"_extract_domain(None) expected '', got {got!r}")
except Exception as e:
    fail(f"_extract_domain(None) raised: {e}")

# -----------------------------------------------------------------
# Bug 2: tracker domains rejected as valid offers
# -----------------------------------------------------------------
print("\n[Bug 2] Testing tracker domain rejection...")
from utils.url_blacklist import is_valid_offer_url
from utils.url_resolver import is_tracking_redirect

cases_invalid = [
    "https://trkerupper.com/click",
    "https://go.viewitquickly.online/go/578da148",
    "https://link.anti-aging.site/view",
    "https://ad.rejuvacare.com/click",
    "https://images.unsplash.com/photo-123.jpg",
]
for url in cases_invalid:
    if not is_valid_offer_url(url):
        ok(f"Rejected (invalid offer): {url[:60]}")
    else:
        fail(f"Should be rejected: {url}")

cases_valid = [
    "https://getretinaclear.com/video/?aff_id=57967",
    "https://nervovive.com/text.php",
    "https://completejointcare.net/vsl/?hopId=abc123",
]
for url in cases_valid:
    if is_valid_offer_url(url):
        ok(f"Accepted (valid offer): {url[:60]}")
    else:
        fail(f"Should be accepted: {url}")

if is_tracking_redirect("https://trkerupper.com/click"):
    ok("trkerupper.com flagged as tracking redirect")
else:
    fail("trkerupper.com should be a tracking redirect")

# -----------------------------------------------------------------
# Bug 4: hop-apps.clickbank.net parsed correctly
# -----------------------------------------------------------------
print("\n[Bug 4] Testing hop-apps.clickbank.net extraction...")
from utils.offer_extractor import decode_clickbank

result = decode_clickbank(
    "https://hop-apps.clickbank.net?errCode=nowhitelist"
    "&destinationUrl=https://nervovive.com/text.php"
    "&hop=mrreese"
)
if result.get("network") == "ClickBank":
    ok("network = ClickBank")
else:
    fail(f"network expected ClickBank, got {result.get('network')}")

if result.get("affiliate_id") == "mrreese":
    ok("affiliate_id = mrreese")
else:
    fail(f"affiliate_id expected mrreese, got {result.get('affiliate_id')}")

real_url = result.get("real_offer_url", "")
if "nervovive.com" in real_url:
    ok(f"real_offer_url contains nervovive.com: {real_url}")
else:
    fail(f"real_offer_url missing nervovive.com, got: {real_url!r}")

# -----------------------------------------------------------------
# Bug 5: Fast-skip domains recognized
# -----------------------------------------------------------------
print("\n[Bug 5] Testing FAST_SKIP_DOMAINS...")
from utils.lp_analyzer import FAST_SKIP_DOMAINS
required = ["viewitquickly.online", "goodrx.com", "rocketmortgage.com", "ring.com/blog", "go.viewitquickly.online"]
for domain in required:
    if domain in FAST_SKIP_DOMAINS:
        ok(f"FAST_SKIP_DOMAINS contains: {domain}")
    else:
        fail(f"Missing from FAST_SKIP_DOMAINS: {domain}")

# -----------------------------------------------------------------
# Bug 6: KNOWN_DIRECT_OFFER_DOMAINS populated correctly
# -----------------------------------------------------------------
print("\n[Bug 6] Testing KNOWN_DIRECT_OFFER_DOMAINS...")
from utils.offer_extractor import KNOWN_DIRECT_OFFER_DOMAINS

expected_domains = {
    "nervovive.com": "ClickBank",
    "getretinaclear.com": "Direct Affiliate",
    "menovelle.com": "ClickBank",
    "pronailcomplex.com": "ClickBank",
    "completejointcare.net": "ClickBank",
    "emptybladdersecret.com": "Direct Affiliate",
}
for domain, expected_net in expected_domains.items():
    if domain not in KNOWN_DIRECT_OFFER_DOMAINS:
        fail(f"{domain} missing from KNOWN_DIRECT_OFFER_DOMAINS")
    got = KNOWN_DIRECT_OFFER_DOMAINS[domain].get("network")
    if got == expected_net:
        ok(f"{domain} -> {got}")
    else:
        fail(f"{domain}: expected {expected_net}, got {got}")

# End-to-end test
from utils.offer_extractor import extract_offer_intelligence
r = extract_offer_intelligence(
    landing_url="https://wellnesspeek.com/lifehacks/?rc_uuid=76a9ef5c",
    raw_final_url="https://getretinaclear.com/video/?aff_id=57967&subid=clf294",
    all_captured_urls=[]
)
if r.get("affiliate_id") == "57967":
    ok("affiliate_id = 57967 (end-to-end)")
else:
    fail(f"affiliate_id: expected 57967, got {r.get('affiliate_id')}")

net = r.get("affiliate_network")
if net in ("Direct Affiliate", "ClickBank"):
    ok(f"affiliate_network = {net}")
else:
    fail(f"affiliate_network unexpected: {net}")

print("\n" + "=" * 60)
print("ALL VALIDATION TESTS PASSED")
print("=" * 60)
