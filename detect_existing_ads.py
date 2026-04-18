import asyncio
import argparse
import os
from tqdm import tqdm
from supabase import create_client
from deep_analyzer import deep_analyze_ad

async def batch_process(limit=10, network=None, delay=0, reanalyze_arbitrage=False):
    """
    Fetches ads from Supabase and processes them.
    By default, fetches un-analyzed ads.
    If reanalyze_arbitrage is True, fetches ads already marked as Arbitrage.
    """
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://avxoumymzbioeabxfcca.supabase.co")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    if reanalyze_arbitrage:
        print(f"🔄 Re-analyzing up to {limit} Arbitrage ads to fix potential bias...")
        query = supabase.table("ads").select("id, landing, title, network").eq("ad_type", "Arbitrage")
    else:
        print(f"🔍 Fetching up to {limit} un-analyzed ads...")
        query = supabase.table("ads").select("id, landing, title, network").is_("deep_analyzed_at", "null")
    
    if network:
        query = query.eq("network", network)
    
    res = query.limit(limit).execute()
    ads = res.data if res.data else []
    
    if not ads:
        print("No ads matching criteria found.")
        return

    print(f"Starting analysis of {len(ads)} ads...")
    stats = {"Affiliate": 0, "Arbitrage": 0, "Unknown": 0, "Failed": 0, "Manual Review Required": 0}
    pbar = tqdm(total=len(ads), desc="Processing")
    
    async def wrapped_analyze(ad):
        try:
            result = await deep_analyze_ad(ad['id'], ad['landing'], ad['title'])
            if "error" in result:
                stats["Failed"] += 1
            else:
                rtype = result.get("ad_type", "Unknown")
                stats[rtype] = stats.get(rtype, 0) + 1
        except Exception as e:
            print(f"Error for ad {ad['id']}: {e}")
            stats["Failed"] += 1
        finally:
            pbar.update(1)
            pbar.set_postfix(stats)

    # Process in small chunks to ensure stability
    for i in range(0, len(ads), 3):
        chunk = ads[i:i+3]
        tasks = [wrapped_analyze(ad) for ad in chunk]
        await asyncio.gather(*tasks)
        if delay > 0:
            await asyncio.sleep(delay)
    
    pbar.close()
    print("\n" + "="*30)
    print("Execution Summary")
    print("="*30)
    for k, v in stats.items():
        if v > 0: print(f"{k}: {v}")
    print("="*30)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Batch Ad Deep Analyzer")
    parser.add_argument("--limit", type=int, default=10, help="Max ads to process")
    parser.add_argument("--network", type=str, help="Filter by network (Taboola, MGID, etc.)")
    parser.add_argument("--delay", type=float, default=0, help="Optional delay between ads")
    parser.add_argument("--reanalyze-arbitrage", action="store_true", help="Re-run analysis on Arbitrage ads")
    
    args = parser.parse_args()
    
    asyncio.run(batch_process(
        limit=args.limit, 
        network=args.network, 
        delay=args.delay, 
        reanalyze_arbitrage=args.reanalyze_arbitrage
    ))
