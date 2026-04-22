import os
import json
import argparse
from supabase import create_client
from utils.lp_analyzer import is_api_endpoint
from utils.url_blacklist import is_meaningful_url
import tldextract

def clean_database_links(limit=1000):
    """
    Scans the database for 'fake' final_offer_urls (APIs, sync pixels)
    and attempts to recover the real merchant URL from the redirect chain.
    """
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://avxoumymzbioeabxfcca.supabase.co")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

    print(f"Scanning up to {limit} ads for fake links...")
    
    # We look for common API patterns in the final_offer_url
    res = supabase.table("ads").select("id, final_offer_url, redirect_chain_json, landing")\
        .or_("final_offer_url.ilike.%/sync%,final_offer_url.ilike.%/api/%,final_offer_url.ilike.%/collect%,final_offer_url.ilike.%.ashx%,final_offer_url.ilike.%/metrics%")\
        .limit(limit).execute()
        
    ads = res.data if res.data else []
    print(f"Found {len(ads)} suspicious ads.")
    
    fixed_count = 0
    for ad in ads:
        current_final = ad.get("final_offer_url")
        chain_raw = ad.get("redirect_chain_json")
        landing = ad.get("landing")
        
        if not current_final: continue
        
        # If it's an API, try to find a better one
        if is_api_endpoint(current_final) or not is_meaningful_url(current_final):
            try:
                chain = json.loads(chain_raw) if chain_raw else []
                if not isinstance(chain, list): chain = []
            except:
                chain = []
                
            recovered_url = None
            # Search chain in reverse for a real merchant page
            for r_url in reversed(chain):
                if not is_api_endpoint(r_url) and is_meaningful_url(r_url):
                    recovered_url = r_url
                    break
            
            if not recovered_url:
                # If chain has nothing, fallback to the landing page (better than an API link)
                recovered_url = landing
                
            if recovered_url and recovered_url != current_final:
                print(f"Fixing Ad {ad['id']}:")
                print(f"  Old: {current_final[:100]}...")
                print(f"  New: {recovered_url[:100]}...")
                
                updates = {
                    "final_offer_url": recovered_url,
                    "offer_domain": tldextract.extract(recovered_url).registered_domain if recovered_url else None,
                    "needs_review": True,
                    "classification_reason": "database_link_cleaned"
                }
                supabase.table("ads").update(updates).eq("id", ad["id"]).execute()
                fixed_count += 1

    print(f"\nCleanup complete. Fixed {fixed_count} links.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--limit", type=int, default=100)
    args = parser.parse_args()
    
    clean_database_links(limit=args.limit)
