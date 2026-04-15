from supabase import create_client
import os

SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_stats():
    res = supabase.table("ads").select("id, language, affiliate_network, tracking_tool").limit(100).execute()
    data = res.data
    
    total = len(data)
    with_lang = len([r for r in data if r.get('language') and r.get('language') != 'en'])
    with_aff = len([r for r in data if r.get('affiliate_network') and r.get('affiliate_network') != 'Direct / Unknown'])
    with_trk = len([r for r in data if r.get('tracking_tool') and r.get('tracking_tool') != 'No Tracking'])
    
    print(f"Total checked: {total}")
    print(f"Ads with non-EN language: {with_lang}")
    print(f"Ads with Affiliate Network: {with_aff}")
    print(f"Ads with Tracking Tool: {with_trk}")
    
    # Check if any new ads (created today) have data
    from datetime import datetime
    today = datetime.now().strftime("%Y-%m-%d")
    res_today = supabase.table("ads").select("id, affiliate_network, tracking_tool").gte("created_at", today).limit(10).execute()
    print(f"\nNew ads today: {len(res_today.data)}")
    for r in res_today.data:
        print(f"  ID: {r['id']} | Aff: {r.get('affiliate_network')} | Trk: {r.get('tracking_tool')}")

if __name__ == "__main__":
    check_stats()
