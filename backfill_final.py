"""
Final Production Backfill Script
- Robust Arabic Detection (Regex)
- Full Metadata Identification (Affiliate + Tracking)
- Comprehensive Coverage (Pagination for 7000+ ads)
- Connection Stability (Try/Except)
Usage: py backfill_final.py
"""

import re
import time
import sys
import os
from langdetect import detect
from supabase import create_client

# Correctly import local modules
sys.path.insert(0, os.path.dirname(__file__))
from utils.affiliate_detector import detect_affiliate_network
from utils.tracker_detector import detect_tracking_tool

SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def is_arabic(text):
    if not text: return False
    # Check for Arabic characters range
    return bool(re.search(r'[\u0600-\u06FF]', text))

def run_backfill():
    print("=" * 70)
    print("  STARTING FINAL BATCH BACKFILL OPERATION")
    print("  Target: ~7,105 ads")
    print("=" * 70)

    total_processed = 0
    total_updated = 0
    total_ar = 0
    page = 0
    batch_size = 100
    
    while True:
        try:
            # Fetch ads in range
            res = supabase.table("ads") \
                .select("id, title, landing, language, affiliate_network, tracking_tool") \
                .range(page * batch_size, (page + 1) * batch_size - 1) \
                .execute()
            
            ads = res.data
            if not ads:
                break
            
            print(f"\nProcessing ads {page * batch_size + 1} to {page * batch_size + len(ads)}...")
            
            for ad in ads:
                total_processed += 1
                ad_id = ad['id']
                title = ad.get('title', '')
                url = ad.get('landing', '')
                
                update_data = {}
                
                # 1. Language Check (Prioritize Arabic)
                detected_lang = ad.get('language')
                if is_arabic(title):
                    if detected_lang != 'ar':
                        update_data['language'] = 'ar'
                        total_ar += 1
                elif not detected_lang or detected_lang == "":
                    try:
                        update_data['language'] = detect(title)
                    except:
                        update_data['language'] = 'en'

                # 2. Affiliate Network (Identify if missing or "Direct / Unknown")
                current_aff = ad.get('affiliate_network')
                if not current_aff or current_aff in ["Direct / Unknown", "Unknown Affiliate", ""]:
                    if url:
                        aff_res = detect_affiliate_network(url)
                        # We only update if we found something better than existing
                        if aff_res['network'] != current_aff:
                            update_data['affiliate_network'] = aff_res['network']

                # 3. Tracking Tool (Identify if missing or "No Tracking")
                current_trk = ad.get('tracking_tool')
                if not current_trk or current_trk in ["No Tracking", ""]:
                    if url:
                        trk_res = detect_tracking_tool(url)
                        if trk_res['tracker'] != current_trk:
                            update_data['tracking_tool'] = trk_res['tracker']

                # Execute update if needed
                if update_data:
                    try:
                        supabase.table("ads").update(update_data).eq("id", ad_id).execute()
                        total_updated += 1
                        # print(f"  [Updated {ad_id}]: {update_data}") # Commented for performance
                    except Exception as e:
                        print(f"  Error updating {ad_id}: {e}")

            page += 1
            # Add small delay to avoid CPU/Network spiking
            time.sleep(0.05)
            
        except Exception as e:
            print(f"\nCritical Error in batch processing: {e}")
            print("Retrying in 5 seconds...")
            time.sleep(5)
            continue

    print("\n" + "=" * 70)
    print(f"  BACKFILL COMPLETE!")
    print(f"  - Total Processed: {total_processed}")
    print(f"  - Total Updated:   {total_updated}")
    print(f"  - Arabic Ads Found: {total_ar}")
    print("=" * 70)

if __name__ == "__main__":
    run_backfill()
