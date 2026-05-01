"""Test the 4 fixes from production run 2026-05-01."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def ok(msg): print(f"  [PASS] {msg}")
def fail(msg): print(f"  [FAIL] {msg}"); sys.exit(1)

print("=" * 60)
print("PRODUCTION FIX TESTS - 2026-05-01")
print("=" * 60)

# Fix 1: youtube.com/generate_204 blocked
print("\n[Fix 1] youtube.com/generate_204 must be blocked...")
from utils.url_blacklist import is_meaningful_url, is_valid_offer_url
if not is_meaningful_url("https://www.youtube.com/generate_204?abc"):
    ok("youtube.com/generate_204 rejected by is_meaningful_url")
else:
    fail("youtube.com/generate_204 should be rejected")

# Fix 2: a.vturb.net blocked
print("\n[Fix 2] a.vturb.net must be blocked...")
if not is_meaningful_url("https://a.vturb.net/x"):
    ok("a.vturb.net rejected by is_meaningful_url")
else:
    fail("a.vturb.net should be rejected")

if not is_valid_offer_url("https://a.vturb.net/x"):
    ok("a.vturb.net rejected by is_valid_offer_url")
else:
    fail("a.vturb.net should be rejected by is_valid_offer_url")

# Fix 3: Self-referencing HTML match blocked
print("\n[Fix 3] Self-referencing HTML match must be blocked...")
from utils.lp_analyzer import extract_affiliate_from_html

# wellnesswiredaily.com/click/1 should NOT be returned when base is wellnesswiredaily.com
html = '<a href="/click/1?utm_source=revcontent&amp;utm_content_id=1">Click</a>'
result = extract_affiliate_from_html(html, "https://wellnesswiredaily.com/?page=test")
if not result or "wellnesswiredaily.com" not in result:
    ok(f"Self-referencing URL rejected (got: {result!r})")
else:
    fail(f"Self-referencing URL should be rejected, got: {result}")

# But cross-domain should still work
html2 = '<a href="https://theprodentim.com/video.php?aff_id=178086&subid=abc">Watch</a>'
result2 = extract_affiliate_from_html(html2, "https://healthierlivingtips.org/page/")
if result2 and "theprodentim.com" in result2:
    ok(f"Cross-domain match works: {result2}")
else:
    fail(f"Cross-domain match broken, got: {result2}")

# Fix 4: Real offer URLs still accepted
print("\n[Fix 4] Real offers must still pass validation...")
real_offers = [
    "https://getretinaclear.com/video/?aff_id=57967",
    "https://mitolyn.com/science/?affiliate=mweb1&tid=123",
    "https://completejointcare.net/vsl/?hop=mrreese&hopId=abc",
    "https://myprostadine24.com/video.php",
    "https://optivell.site/opv-site/cards",
    "https://flushfactorplus.com/text.php?hop=mrreese",
]
for url in real_offers:
    if is_valid_offer_url(url) and is_meaningful_url(url):
        ok(f"Accepted: {url[:60]}")
    else:
        fail(f"Should be accepted: {url}")

# Fix 5: TECHNICAL_NOISE_DOMAINS updated
print("\n[Fix 5] TECHNICAL_NOISE_DOMAINS updated...")
from utils.lp_analyzer import TECHNICAL_NOISE_DOMAINS
for domain in ["a.vturb.net", "vturb.net", "youtube.com", "converteai.net"]:
    if domain in TECHNICAL_NOISE_DOMAINS:
        ok(f"TECHNICAL_NOISE contains: {domain}")
    else:
        fail(f"Missing from TECHNICAL_NOISE: {domain}")

print("\n" + "=" * 60)
print("ALL PRODUCTION FIX TESTS PASSED")
print("=" * 60)
