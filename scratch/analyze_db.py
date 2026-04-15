import re
from supabase import create_client
import os

SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def is_arabic(text):
    if not text: return False
    return any('\u0600' <= c <= '\u06FF' for c in text)

def analyze():
    print("Fetching all ads from database...")
    all_ads = []
    page = 0
    batch_size = 1000
    
    while True:
        res = supabase.table("ads").select("id, title, language, affiliate_network, tracking_tool").range(page * batch_size, (page + 1) * batch_size - 1).execute()
        batch = res.data
        if not batch:
            break
        all_ads.extend(batch)
        page += 1
        print(f"  Fetched {len(all_ads)} ads...")

    print(f"\nTotal ads: {len(all_ads)}")
    
    arabic_ads = []
    empty_aff = []
    empty_trk = []
    empty_lang = []
    
    for a in all_ads:
        title = a.get('title') or ''
        lang = a.get('language')
        aff = a.get('affiliate_network')
        trk = a.get('tracking_tool')
        
        if is_arabic(title):
            arabic_ads.append(a)
        
        if not aff or aff == "":
            empty_aff.append(a['id'])
        if not trk or trk == "":
            empty_trk.append(a['id'])
        if not lang or lang == "":
            empty_lang.append(a['id'])
            
    print(f"Arabic ads found by script: {len(arabic_ads)}")
    
    lang_stats = {}
    mislabeled_ar = []
    for a in arabic_ads:
        l = a.get('language')
        lang_stats[l] = lang_stats.get(l, 0) + 1
        if l != 'ar':
            mislabeled_ar.append(a)
    
    print(f"Language tags for Arabic ads: {lang_stats}")
    print(f"Ads with Arabic titles but NOT tagged 'ar': {len(mislabeled_ar)}")
    
    print(f"Empty affiliate_network (NULL/''): {len(empty_aff)}")
    print(f"Empty tracking_tool (NULL/''): {len(empty_trk)}")
    print(f"Empty language (NULL/''): {len(empty_lang)}")
    
    if mislabeled_ar:
        print("\nExamples of mislabeled Arabic ads:")
        for a in mislabeled_ar[:5]:
            print(f"ID: {a['id']} | Title: {a['title']} | Lang: {a['language']}")

if __name__ == "__main__":
    analyze()
