import sys
import os
import asyncio

# Fix Windows console encoding
if sys.platform == 'win32':
    import io
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from utils.url_resolver import resolve_url
from utils.advanced_detector import detect_from_chain

async def test():
    print("=" * 60)
    print("Verification: Intelligent Redirection & Detection")
    print("=" * 60)
    
    # Test 1: Simulated Redirect Chain (Voluum -> MaxBounty -> Page)
    print("\n[TEST 1] Simulated Redirect Chain (Voluum -> MaxBounty)")
    mock_chain = [
        "https://track.voluumtrk.com/click-id-123",
        "https://offer.maxbounty.com/landing?p=1",
        "https://finalpage.com/product"
    ]
    
    intel = detect_from_chain(mock_chain)
    print(f"  Detected Tracker: {intel['tracking_tool']}")
    print(f"  Detected Network: {intel['affiliate_network']}")
    
    # Test 2: Parameter-based detection (cid=)
    print("\n[TEST 2] Parameter-based detection (cid=)")
    param_chain = ["https://unknown-domain.com/path?cid=999&aff_id=1"]
    intel_param = detect_from_chain(param_chain)
    print(f"  Detected Tracker (Param): {intel_param['tracking_tool']}")
    
    # Test 3: Real Database Lookup (Requires seeded table)
    print("\n[TEST 3] Real Database Pattern Lookup")
    db_chain = ["https://go2cloud.org/aff_c?offer_id=1"]
    intel_db = detect_from_chain(db_chain)
    print(f"  Detected Network (DB): {intel_db['affiliate_network']}")
    
    print("\n" + "=" * 60)
    print("Test Completed Successfully")

if __name__ == "__main__":
    asyncio.run(test())
