import re
import time
import sys
import os
from langdetect import detect
from supabase import create_client

sys.path.insert(0, os.path.dirname(__file__))

from utils.affiliate_detector import detect_affiliate_network
from utils.tracker_detector import detect_tracking_tool

SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def is_arabic(text):
    if not text: return False
    return bool(re.search(r'[\u0600-\u06FF]', text))

def run_backfill():
    print("=" * 70)
    print("  RELENTLESS METADATA BACKFILL - PASS 1: ARABIC DETECTION")
    print("=" * 70)

    # 1. Force Arabic detection for titles with Arabic script
    # We fetch chunks of ads and check titles
    updated_ar = 0
    page = 0
    batch_size = 200
    
    while True:
        try:
            res = supabase.table("ads") \
                .select("id, title, language") \
                .range(page * batch_size, (page + 1) * batch_size - 1) \
                .execute()
            
            ads = res.data
            if not ads: break
            
            for ad in ads:
                title = ad.get('title', '')
                if is_arabic(title) and ad.get('language') != 'ar':
                    print(f"  [ARABIC] Found: {title[:30]}... (ID: {ad['id']})")
                    supabase.table("ads").update({"language": "ar"}).eq("id", ad["id"]).execute()
                    updated_ar += 1
            
            page += 1
            if page % 10 == 0: print(f"  Scanned {page * batch_size} ads...")
            time.sleep(0.1)
        except Exception as e:
            print(f"  Batch Error: {e}. Retrying in 5s...")
            time.sleep(5)
            continue
            
    print(f"\n  Done Pass 1! Fixed {updated_ar} Arabic ads.")

    print("\n" + "=" * 70)
    print("  PASS 2: AFFILIATE & TRACKER DETECTION")
    print("=" * 70)
    
    # We target ads that have no affiliate network or the default 'Direct / Unknown'
    # and try to identify them.
    page = 0
    updated_meta = 0
    
    while True:
        try:
            # We fetch ads and filter them in memory to find ones needing an update
            res = supabase.table("ads") \
                .select("id, landing, affiliate_network, tracking_tool") \
                .range(page * batch_size, (page + 1) * batch_size - 1) \
                .execute()
            
            ads = res.data
            if not ads: break
            
            for ad in ads:
                url = ad.get('landing', '')
                if not url: continue
                
                aff_current = ad.get('affiliate_network')
                trk_current = ad.get('tracking_tool')
                
                update_payload = {}
                
                # Try to detect if missing or default
                if not aff_current or aff_current in ["Direct / Unknown", "null", ""]:
                    aff = detect_affiliate_network(url)
                    if aff['network'] != "Direct / Unknown":
                        update_payload['affiliate_network'] = aff['network']
                
                if not trk_current or trk_current in ["No Tracking", "null", ""]:
                    trk = detect_tracking_tool(url)
                    if trk['tracker'] != "No Tracking":
                        update_payload['tracking_tool'] = trk['tracker']
                
                if update_payload:
                    print(f"  [META] Updated ID {ad['id']}: {update_payload}")
                    supabase.table("ads").update(update_payload).eq("id", ad["id"]).execute()
                    updated_meta += 1
            
            page += 1
            time.sleep(0.1)
        except Exception as e:
            print(f"  Batch Error: {e}. Retrying...")
            time.sleep(5)
            continue

    print(f"\n  Done Pass 2! Updated {updated_meta} ads with metadata.")

if __name__ == "__main__":
    run_backfill()
