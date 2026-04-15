import re
from supabase import create_client
import os
from langdetect import detect

SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def is_arabic(text):
    # Regex range for Arabic characters
    return bool(re.search(r'[\u0600-\u06FF]', text))

def fix_languages():
    print("Checking ads for misidentified languages...")
    res = supabase.table("ads").select("id, title, language").limit(1000).execute()
    ads = res.data
    
    updated = 0
    for ad in ads:
        title = ad.get('title', '')
        current_lang = ad.get('language', 'en')
        
        # If it has Arabic characters but marked as something else, fix it to 'ar'
        if is_arabic(title) and current_lang != 'ar':
            print(f"Fixing ID {ad['id']} to 'ar' | Title: {title[:30]}...")
            supabase.table("ads").update({"language": "ar"}).eq("id", ad["id"]).execute()
            updated += 1
        # If it's English alphabet but marked empty, mark as 'en'
        elif not is_arabic(title) and not current_lang:
            supabase.table("ads").update({"language": "en"}).eq("id", ad["id"]).execute()
            updated += 1
            
    print(f"Total fixed: {updated}")

if __name__ == "__main__":
    fix_languages()
