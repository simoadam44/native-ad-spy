import os
import asyncio
from supabase import create_client
from utils.url_resolver import (
    is_tracking_redirect, 
    resolve_tracking_url
)

# Supabase initialization
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def fix_tracking_urls(limit=100, dry_run=False):
    """
    Finds and fixes ads with tracking redirects or noisy parameters in the database.
    """
    TRACKING_PATTERNS = [
        "tr.outbrain.com/cachedClickId",
        "paid.outbrain.com",
        "trc.taboola.com",
        "clk.taboola.com",
        "smeagol.revcontent.com",
        "hop.clickbank.net",
        "voluum.com",
        "rdtk.io",
        "bemob.com",
        "trendingboom.com",
        "trendygadgetreviews.com",
        "genius-markets.com",
        "geniustech-magazine.com",
        "gphops.site",
        "syndicatedsearch.goog",
    ]
    
    print(f"Searching for ads with tracking patterns (limit={limit})...")
    
    all_ads_to_fix = []
    for pattern in TRACKING_PATTERNS:
        try:
            results = supabase.table("ads")\
                .select("id, landing, final_offer_url")\
                .or_(
                    f"landing.ilike.%{pattern}%,"
                    f"final_offer_url.ilike.%{pattern}%"
                )\
                .limit(limit)\
                .execute()
            if results.data:
                all_ads_to_fix.extend(results.data)
        except Exception as e:
            print(f"Error searching for pattern {pattern}: {e}")
    
    # Deduplicate
    seen_ids = set()
    unique_ads = []
    for ad in all_ads_to_fix:
        if ad["id"] not in seen_ids:
            seen_ids.add(ad["id"])
            unique_ads.append(ad)
    
    if not unique_ads:
        print("No ads found matching tracking patterns.")
        return

    print(f"Found {len(unique_ads)} ads to process.")
    
    fixed = 0
    failed = 0
    
    for ad in unique_ads:
        updates = {}
        ad_id = ad["id"]
        
        for field in ["landing", "final_offer_url"]:
            url = ad.get(field)
            if url and is_tracking_redirect(url):
                print(f"  [Ad {ad_id}] Resolving {field}: {url[:60]}...")
                result = resolve_tracking_url(url)
                if result["resolved"]:
                    updates[field] = result["final"]
                    print(f"    ✅ Resolved -> {result['final'][:60]}...")
                else:
                    print(f"    ⚠️ Resolution failed: {result.get('reason')}")
        
        if updates:
            if not dry_run:
                try:
                    supabase.table("ads")\
                        .update(updates)\
                        .eq("id", ad_id)\
                        .execute()
                    fixed += 1
                except Exception as e:
                    print(f"    ❌ DB update error: {e}")
                    failed += 1
            else:
                print(f"    [DRY RUN] Would update ad {ad_id}")
                fixed += 1
        else:
            print(f"  [Ad {ad_id}] No changes needed or resolution failed.")
    
    print(f"\n{'='*40}")
    print(f"Summary: Fixed {fixed} | Failed {failed} | Dry Run: {dry_run}")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Fix tracking URLs in the database.")
    parser.add_argument("--limit", type=int, default=100, help="Max records per pattern")
    parser.add_argument("--dry-run", action="store_true", help="Don't save changes to DB")
    
    args = parser.parse_args()
    fix_tracking_urls(args.limit, args.dry_run)
