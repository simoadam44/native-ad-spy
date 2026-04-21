import asyncio
import os
import sys
import json
from playwright.async_api import async_playwright
from supabase import create_client

# Add current directory to path
sys.path.append(os.getcwd())

# Manually set environment variables from web/.env.local
os.environ["SUPABASE_URL"] = "https://avxoumymzbioeabxfcca.supabase.co"
os.environ["SUPABASE_KEY"] = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"

from deep_analyzer import deep_analyze_ad

# Define local version of fetch_ads_for_analysis since it was missing in imports
def fetch_ads_for_trial(limit=2):
    SUPABASE_URL = os.environ.get("SUPABASE_URL")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # Fetch ads that haven't been deep analyzed yet
    res = supabase.table("ads").select("id, landing, title")\
        .is_("deep_analyzed_at", "null")\
        .limit(limit).execute()
    return res.data

async def main():
    print("Starting Batch Verification [Hardening Part 3]...")
    
    limit = 5
    ads = fetch_ads_for_trial(limit=limit)
    if not ads:
        print("No un-analyzed ads found.")
        return
        
    print(f"Witnessing analysis for {len(ads)} ads...")
    
    for i, ad in enumerate(ads):
        print(f"\n--- Ad {i+1}/{len(ads)}: ID {ad['id']} ---")
        print(f"Landing: {ad['landing']}")
        
        try:
            # Run the actual analyst logic
            result = await deep_analyze_ad(ad['id'], ad['landing'], ad.get('title', 'Unknown'))
            final_offer = result.get('intelligence', {}).get('final_offer_url') or result.get('final_offer_url') or "N/A"
            
            print(f"Final Offer Resolved: {final_offer}")
            
            # STRICT VALIDATION
            media_exts = [".ts", ".m3u8", ".mp4", ".mp3", ".webm"]
            if any(ext in str(final_offer).lower() for ext in media_exts):
                print("!!! FAILED PROTECTION: Media segment detected as final offer !!!")
            else:
                print("PASSED PROTECTION: Final offer is clean of media segments.")
                
        except Exception as e:
            print(f"Error for Ad {ad['id']}: {e}")

if __name__ == "__main__":
    asyncio.run(main())
