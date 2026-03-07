import requests
from bs4 import BeautifulSoup
from supabase import create_client

# معلومات Supabase
SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# قائمة المواقع
sites = [
    "https://edition.cnn.com",
    "https://www.tag24.de",
    "https://www.trucs-et-astuces.co",
    "https://www.topbunt.com",
    "https://www.gameswaka.com",
    "https://www.citizen.co.za",
    "https://www.tips-and-tricks.co",
    "https://www.articleskill.com",
    "https://www.articlesvally.com",
    "https://www.dailysportx.com"
]

# زيارة كل موقع وجمع إعلانات Taboola / Native
for site in sites:
    print(f"🔍 Visiting {site} ...")
    try:
        html = requests.get(site, timeout=10).text
        soup = BeautifulSoup(html, "html.parser")

        # البحث عن divs تحتوي على class تشير إلى Taboola / Native
        ad_divs = soup.find_all("div", class_=lambda x: x and ("trc_spotlight_item" in x or "taboola" in x or "native_ad" in x))

        for ad in ad_divs:
            # العنوان
            title = ad.get_text(strip=True)

            # الصورة
            img = ad.find("img")
            image = img["src"] if img else ""

            # رابط Landing Page
            link = ad.find("a")
            landing = link["href"] if link else ""

            if landing and image:
                data = {
                    "title": title,
                    "image": image,
                    "landing": landing,
                    "source": site
                }
                supabase.table("ads").insert(data).execute()
                print("Saved:", title)

    except Exception as e:
        print(f"❌ Failed to crawl {site}: {e}")
