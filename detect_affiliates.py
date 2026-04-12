"""
Batch Affiliate Network Detection Script
Fetches all ads missing an affiliate_network, detects it, and updates the database.
Usage: py detect_affiliates.py
"""

import sys
import time
import os
sys.path.insert(0, os.path.dirname(__file__))

from supabase import create_client
from utils.affiliate_detector import detect_affiliate_network

SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BATCH_SIZE = 100


def run():
    print("=" * 60)
    print("  Affiliate Network Batch Detection Script")
    print("=" * 60)

    total_processed = 0
    total_identified = 0
    page_offset = 0

    while True:
        # Fetch batch of ads without affiliate_network
        res = supabase.table("ads") \
            .select("id, landing, title") \
            .is_("affiliate_network", "null") \
            .range(page_offset, page_offset + BATCH_SIZE - 1) \
            .execute()

        batch = res.data
        if not batch:
            break

        print(f"\nProcessing batch: {page_offset + 1} to {page_offset + len(batch)}...")

        for ad in batch:
            url = ad.get("landing", "")
            result = detect_affiliate_network(url)
            network = result["network"]
            confidence = result["confidence"]

            supabase.table("ads").update({
                "affiliate_network": network
            }).eq("id", ad["id"]).execute()

            if confidence == "high":
                total_identified += 1
                print(f"  [HIGH]    {network:<20} | {url[:50]}")
            elif confidence == "medium":
                print(f"  [MEDIUM]  {network:<20} | {url[:50]}")
            else:
                print(f"  [UNKNOWN] {network:<20} | {url[:50]}")

            total_processed += 1
            time.sleep(0.03)  # Avoid rate limiting

        page_offset += BATCH_SIZE

    print("\n" + "=" * 60)
    print(f"  Done! Processed: {total_processed} ads")
    print(f"  Identified (high confidence): {total_identified} ads")
    print("=" * 60)


if __name__ == "__main__":
    run()
