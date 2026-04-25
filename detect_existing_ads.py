import asyncio
import argparse
import os
from tqdm import tqdm
from supabase import create_client
from deep_analyzer import deep_analyze_ad

async def batch_process(limit=10, network=None, delay=0, reanalyze_arbitrage=False, reanalyze_affiliates=False):
    """
    Fetches ads from Supabase and processes them.
    By default, fetches un-analyzed ads.
    """
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://avxoumymzbioeabxfcca.supabase.co")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    if reanalyze_arbitrage:
        print(f"Re-analyzing up to {limit} Arbitrage ads to fix potential bias...")
        query = supabase.table("ads").select("id, landing, title, network").eq("ad_type", "Arbitrage")
    elif reanalyze_affiliates:
        print(f"Re-analyzing up to {limit} Affiliate ads to fix false positives...")
        query = supabase.table("ads").select("id, landing, title, network")\
            .eq("ad_type", "Affiliate")\
            .or_("redirect_chain_json.ilike.%taboola_hm%,redirect_chain_json.ilike.%rubiconproject%,redirect_chain_json.ilike.%gdpr_consent%,redirect_chain_json.ilike.%deepintent%")
    else:
        print(f"Fetching up to {limit} un-analyzed ads...")
        # Strict filter: ONLY ads that haven't been deep analyzed AND don't have a final ad_type yet
        # and aren't already flagged as needing review (which usually means they failed before)
        query = supabase.table("ads").select("id, landing, title, network")\
            .is_("deep_analyzed_at", "null")\
            .or_("ad_type.is.null,ad_type.eq.Unknown")\
            .not_.eq("needs_review", "true")
    
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
    
    PER_AD_TIMEOUT = 120  # seconds - hard limit per ad

    async def wrapped_analyze(ad):
        ad_id = ad['id']
        landing = ad['landing']
        try:
            print(f"\n[Analysing Ad {ad_id}] {landing[:60]}...", flush=True)
            result = await asyncio.wait_for(
                deep_analyze_ad(ad_id, landing, ad['title']),
                timeout=PER_AD_TIMEOUT
            )
            if "error" in result:
                stats["Failed"] += 1
            else:
                rtype = result.get("ad_type", "Unknown")
                stats[rtype] = stats.get(rtype, 0) + 1
        except asyncio.TimeoutError:
            print(f"\nTIMEOUT: Ad {ad_id} exceeded {PER_AD_TIMEOUT}s limit - skipping", flush=True)
            stats["Failed"] += 1
        except Exception as e:
            print(f"\nError for ad {ad_id}: {e}", flush=True)
            stats["Failed"] += 1
        finally:
            pbar.update(1)
            pbar.set_postfix(stats)

    for i in range(len(ads)):
        ad = ads[i]
        await wrapped_analyze(ad)
        await asyncio.sleep(1.0) # Yield and settle
    
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
    parser.add_argument("--reanalyze-affiliates", action="store_true", help="Re-run analysis on Affiliate ads to fix false positives")
    
    args = parser.parse_args()
    
    asyncio.run(batch_process(
        limit=args.limit, 
        network=args.network, 
        delay=args.delay, 
        reanalyze_arbitrage=args.reanalyze_arbitrage,
        reanalyze_affiliates=args.reanalyze_affiliates
    ))
