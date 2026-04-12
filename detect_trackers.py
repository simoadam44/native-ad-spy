"""
Batch Tracking Tool Detection Script
Fetches all ads missing a tracking_tool, detects it, and updates the database.
Usage: py detect_trackers.py
"""
import sys
import time
import os
sys.path.insert(0, os.path.dirname(__file__))

from supabase import create_client
from utils.tracker_detector import detect_tracking_tool

SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

BATCH_SIZE = 100


def run():
    print("=" * 65)
    print("  Tracking Tool Batch Detection Script")
    print("=" * 65)

    summary: dict[str, int] = {}
    total_processed = 0
    page_offset = 0

    while True:
        res = supabase.table("ads") \
            .select("id, landing") \
            .is_("tracking_tool", "null") \
            .range(page_offset, page_offset + BATCH_SIZE - 1) \
            .execute()

        batch = res.data
        if not batch:
            break

        print(f"\nProcessing batch: {page_offset + 1} - {page_offset + len(batch)}")

        for ad in batch:
            url = ad.get("landing", "")
            result = detect_tracking_tool(url)
            tracker = result["tracker"]
            confidence = result["confidence"]

            supabase.table("ads").update({"tracking_tool": tracker}).eq("id", ad["id"]).execute()

            summary[tracker] = summary.get(tracker, 0) + 1
            label = f"[{confidence.upper():<7}]"
            print(f"  {label} {tracker:<20} | {url[:55]}")

            total_processed += 1
            time.sleep(0.03)

        page_offset += BATCH_SIZE

    print("\n" + "=" * 65)
    print(f"  Done! Total processed: {total_processed} ads")
    print("\n  Summary by tracker:")
    for tracker, count in sorted(summary.items(), key=lambda x: -x[1]):
        bar = "#" * min(count // 5, 40)
        print(f"    {tracker:<25} {count:>5}  {bar}")
    print("=" * 65)


if __name__ == "__main__":
    run()
