import os
from supabase import create_client

# Use hardcoded credentials from .env.local to ensure it works
supabase_url = "https://avxoumymzbioeabxfcca.supabase.co"
supabase_key = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"
supabase = create_client(supabase_url, supabase_key)

# We can't run raw SQL via the client easily, but we can try to insert a test row with the new column
# If the insert fails with 'column does not exist', we know the user must add it.
# However, I will provide a script for the user to run in their Supabase SQL Editor.

sql_command = """
ALTER TABLE ads ADD COLUMN IF NOT EXISTS language TEXT DEFAULT 'en';
"""

print("Please run the following SQL command in your Supabase SQL Editor:")
print("-" * 50)
print(sql_command)
print("-" * 50)

# Also, let's create the backfill script
backfill_code = """
from langdetect import detect
from supabase import create_client
import time

supabase_url = "https://avxoumymzbioeabxfcca.supabase.co"
supabase_key = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"
supabase = create_client(supabase_url, supabase_key)

def backfill():
    print("🚀 Starting language backfill for existing ads...")
    # Get ads without a language or with default 'en' but potentially different
    res = supabase.table('ads').select('id, title').is_('language', 'null').limit(100).execute()
    
    if not res.data:
        print("✅ No ads need backfilling.")
        return

    for ad in res.data:
        try:
            lang = detect(ad['title'])
            supabase.table('ads').update({'language': lang}).eq('id', ad['id']).execute()
            print(f"✅ Ad {ad['id'][:8]}: {lang} -> {ad['title'][:30]}...")
        except Exception as e:
            print(f"❌ Ad {ad['id'][:8]} failed: {e}")
        time.sleep(0.1)

if __name__ == '__main__':
    backfill()
"""

with open("scratch/backfill_languages.py", "w", encoding='utf-8') as f:
    f.write(backfill_code)

print("Backfill script created at: scratch/backfill_languages.py")
