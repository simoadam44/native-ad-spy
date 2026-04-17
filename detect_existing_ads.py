import asyncio
import argparse
import os
from tqdm import tqdm
from supabase import create_client
from deep_analyzer import deep_analyze_ad

# Supabase Setup
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://avxoumymzbioeabxfcca.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def batch_process(limit=10, network=None, delay=0):
    """
    Fetches ads from Supabase that haven't been deep analyzed and processes them.
    """
    print(f"Fetching up to {limit} un-analyzed ads...")
    
    query = supabase.table("ads").select("id, landing, title, network").is_("deep_analyzed_at", "null")
    
    if network:
        query = query.eq("network", network)
    
    res = query.limit(limit).execute()
    ads = res.data if res.data else []
    
    if not ads:
        print("No ads pending analysis. You are all caught up!")
        return

    print(f"Starting batch analysis of {len(ads)} ads...")
    
    stats = {"Affiliate": 0, "Arbitrage": 0, "Unknown": 0, "Failed": 0}
    
    # Progress Bar
    pbar = tqdm(total=len(ads), desc="Analyzing Ads")
    
    async def wrapped_analyze(ad):
        try:
            result = await deep_analyze_ad(ad['id'], ad['landing'], ad['title'])
            if "error" in result:
                stats["Failed"] += 1
            else:
                stats[result.get("ad_type", "Unknown")] += 1
        except Exception as e:
            print(f"Error in batch: {e}")
            stats["Failed"] += 1
        finally:
            pbar.update(1)
            pbar.set_postfix(stats)

    # We use gather but deep_analyze_ad has internal Semaphore(3)
    # to prevent system collapse
    tasks = [wrapped_analyze(ad) for ad in ads]
    await asyncio.gather(*tasks)
    
    pbar.close()
    print("\n" + "="*30)
    print("Batch Analysis Summary")
    print("="*30)
    print(f"Affiliate: {stats['Affiliate']}")
    print(f"Arbitrage: {stats['Arbitrage']}")
    print(f"Unknown:   {stats['Unknown']}")
    print(f"Failed:    {stats['Failed']}")
    print("="*30)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch Ad Deep Analyzer")
    parser.add_argument("--limit", type=int, default=10, help="Max ads to process")
    parser.add_argument("--network", type=str, help="Filter by network (Taboola, MGID, etc.)")
    parser.add_argument("--delay", type=float, default=0, help="Optional delay between ads")
    
    args = parser.parse_args()
    
    asyncio.run(batch_process(limit=args.limit, network=args.network, delay=args.delay))
