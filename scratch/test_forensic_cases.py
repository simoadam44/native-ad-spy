import json
import asyncio
from utils.offer_extractor import extract_offer_intelligence

async def test_forensic_cases():
    print("=" * 40)
    print("TESTING FORENSIC INTELLIGENCE UPGRADE")
    print("=" * 40 + "\n")

    # Case 1: theenergyrevolution.net (Custom Tracker with lptoken)
    test1_landing = "https://healthierlivingtips.org/int_pp_spl_ee/?c=w9htmg9omb4afuphjsnskcpi&r=289323_joehoft.com_2452300_MA_DESKTOP_Windows&lptoken=17fa761455d13979058f&widget_id=289323&content_id=13840265&boost_id=2452300&sn=joehoft.com&rc_uuid=a350284b-4273-4c4e-b256-39845b301f2d"
    test1_offer   = "https://theenergyrevolution.net/index-ers-auto-lead-39-promise-epp-lead-6-ph.html"
    
    print("CASE 1: theenergyrevolution.net (Custom Tracker)")
    res1 = extract_offer_intelligence(test1_offer, [], test1_landing)
    print(f"  Traffic Source:   {res1.get('traffic_source')}")
    print(f"  Tracker Tool:     {res1.get('tracker_tool')}")
    print(f"  Tracker ID:       {res1.get('tracker_id')}")
    print(f"  Network:          {res1.get('affiliate_network')}")
    print(f"  Click ID:         {res1.get('click_id')}")
    print(f"  Path Segments:    {res1.get('path_segments')}")
    print(f"  Needs Review:     {res1.get('needs_review')}")
    
    # Assertions for Case 1
    assert res1.get('traffic_source') == "Revcontent"
    assert res1.get('tracker_tool') == "Custom/In-house Tracker"
    assert res1.get('tracker_id') == "17fa761455d13979058f"
    assert res1.get('click_id') == "w9htmg9omb4afuphjsnskcpi"
    print("  SUCCESS: Case 1 PASSED\n")

    # Case 2: completejointcare.net (ClickBank via hop= parameter)
    test2_landing = "https://healthierlivingtips.org/int_jp_spl_jjt/?c=wqbo81mtl08t9uphj6om336r&rc_uuid=7c86c1b5-d441-4721-b42a-bb5bdde8b352"
    test2_offer   = "https://completejointcare.net/vsl/?hop=b1744&hopId=5553ed8c-113c-49af-9e17-31595b23daa8&v=bvsl"
    
    print("CASE 2: completejointcare.net (ClickBank)")
    res2 = extract_offer_intelligence(test2_offer, [], test2_landing)
    print(f"  Traffic Source:   {res2.get('traffic_source')}")
    print(f"  Network:          {res2.get('affiliate_network')}")
    print(f"  Affiliate ID:     {res2.get('affiliate_id')} (hop)")
    print(f"  Click ID:         {res2.get('click_id')} (hopId)")
    print(f"  Offer Domain:     {res2.get('offer_domain')}")
    print(f"  Variant (v):      {res2.get('offer_id')}")
    print(f"  Needs Review:     {res2.get('needs_review')}")

    # Assertions for Case 2
    assert res2.get('affiliate_network') == "ClickBank"
    assert res2.get('affiliate_id') == "b1744"
    assert res2.get('click_id') == "5553ed8c-113c-49af-9e17-31595b23daa8"
    assert res2.get('offer_id') == "bvsl"
    print("  SUCCESS: Case 2 PASSED")

if __name__ == "__main__":
    asyncio.run(test_forensic_cases())
