
import asyncio
import sys
import os

# Add parent dir to path
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from utils.url_blacklist import is_prelander_domain, is_valid_offer_url, has_unresolved_macros
from utils.offer_extractor import decode_wellnesspeek_cep

def test_pattern_a_e():
    print("Testing Pattern A: Pre-lander detection...")
    url = "https://www.smarthealthpractices.com/adv-rc-bm-ig-us-v1?cep=123&lptoken=456&widget_id=789"
    assert is_prelander_domain(url) == True
    print("PASS: Pattern A/E")

def test_pattern_b():
    print("Testing Pattern B: Unresolved macros...")
    url = "https://mwebtrackerhq.com/8991/1763/3/?subid2=%7B%21subid%21%7D"
    assert has_unresolved_macros(url) == True
    assert is_valid_offer_url(url) == False
    print("PASS: Pattern B")

def test_pattern_d():
    print("Testing Pattern D: Video asset rejection...")
    url = "https://assets.checkoutchamp.com/xxx/video.avif"
    assert is_valid_offer_url(url) == False
    print("PASS: Pattern D")

def test_pattern_f():
    print("Testing Pattern F: healthclubjournal.com acceptance...")
    url = "https://healthclubjournal.com/18800025.php?aff=1834"
    assert is_valid_offer_url(url) == True
    print("PASS: Pattern F")

if __name__ == "__main__":
    try:
        test_pattern_a_e()
        test_pattern_b()
        test_pattern_d()
        test_pattern_f()
        print("\nALL TESTS PASSED!")
    except AssertionError as e:
        print(f"\nTEST FAILED!")
        sys.exit(1)
    except Exception as e:
        print(f"\nERROR: {e}")
        sys.exit(1)
