import requests
from bs4 import BeautifulSoup
from supabase import create_client

# معلومات Supabase
SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# قائمة المواقع
sites = [
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

# زيارة كل موقع وجمع الإعلانات
for site in sites:
    print(f"🔍 Visiting {site} ...")
    try:
        html = requests.get(site, timeout=10).text
        soup = BeautifulSoup(html,"html.parser")

        # تحديد عناصر الإعلانات (يمكن تعديل هذا حسب الموقع)
        ads = soup.select(".trc_spotlight_item")

        for ad in ads:
            title = ad.get_text(strip=True)
            img = ad.find("img")
            image = img["src"] if img else ""
            link = ad.find("a")
            landing = link["href"] if link else ""

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
