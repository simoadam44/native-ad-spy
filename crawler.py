import requests
from bs4 import BeautifulSoup
from supabase import create_client

# معلومات Supabase
SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# قائمة المواقع المستهدفة
sites = [
    "https://edition.cnn.com",
    "https://www.tag24.de",
    "https://www.trucs-et-astuces.co",
    "https://edition.cnn.com", 
    "https://www.mirror.co.uk",
    "https://www.elbalad.news",
    "https://www.topbunt.com",
    "https://www.gameswaka.com",
    "https://www.citizen.co.za",
    "https://www.tips-and-tricks.co",
    "https://www.articleskill.com",
    "https://www.articlesvally.com",
    "https://www.dailysportx.com"
]

# قائمة المعرفات (Selectors) لأهم الشبكات (Taboola, Outbrain, MGID)
ad_selectors = [
    ".trc_spotlight_item",      # Taboola
    ".ob-dynamic-rec-container", # Outbrain
    ".mg-item",                 # MGID
    ".mgid_ad_item",            # MGID
    "div[class*='taboola']",     # أي عنصر يحتوي كلاس تابولا
    "div[class*='native-ad']"    # أي عنصر يحتوي كلاس إعلان ناتيف
]

for site in sites:
    print(f"🔍 Visiting {site} ...")
    try:
        # إضافة User-Agent لتقليل فرص الحظر
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(site, timeout=15, headers=headers)
        soup = BeautifulSoup(response.text, "html.parser")

        # البحث بكل المعرفات الممكنة
        for selector in ad_selectors:
            ad_divs = soup.select(selector)

            for ad in ad_divs:
                title = ad.get_text(strip=True)
                
                # استخراج الصورة (أحياناً تكون في data-src بدلاً من src)
                img = ad.find("img")
                image = ""
                if img:
                    image = img.get("src") or img.get("data-src") or img.get("data-lazy-src") or ""

                # رابط Landing Page
                link = ad.find("a")
                landing = link["href"] if link else ""

                # شروط الحفظ: يجب وجود عنوان وصورة ورابط، وألا يكون العنوان قصيراً جداً
                if landing and image and len(title) > 10:
                    data = {
                        "title": title,
                        "image": image,
                        "landing": landing,
                        "source": site
                    }
                    # إرسال البيانات لـ Supabase
                    supabase.table("ads").insert(data).execute()
                    print(f"✅ Saved: {title[:40]}...")

    except Exception as e:
        print(f"❌ Failed to crawl {site}: {e}")
