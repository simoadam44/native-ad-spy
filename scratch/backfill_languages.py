
from langdetect import detect
from supabase import create_client
import time

supabase_url = "https://avxoumymzbioeabxfcca.supabase.co"
supabase_key = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"
supabase = create_client(supabase_url, supabase_key)

def backfill():
    print("--- Starting language backfill for existing ads ---")
    # Get ads where language is null (or you can use .eq('language', 'en') to re-detect everything)
    res = supabase.table('ads').select('id, title').is_('language', 'null').limit(500).execute()
    
    if not res.data:
        print("Done: No ads found that need language detection.")
        return

    print(f"Found {len(res.data)} ads to process...")
    for ad in res.data:
        try:
            lang = detect(ad['title'])
            supabase.table('ads').update({'language': lang}).eq('id', ad['id']).execute()
            print(f"OK: Ad {ad['id'][:8]} identified as [{lang}]")
        except Exception as e:
            print(f"Error: Ad {ad['id'][:8]} failed: {e}")
        time.sleep(0.05)

if __name__ == '__main__':
    backfill()
