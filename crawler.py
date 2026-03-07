# crawler.py
import requests
from bs4 import BeautifulSoup
from supabase import create_client

# معلومات الاتصال بـ Supabase
SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"

# إنشاء العميل للتواصل مع Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# الموقع الذي سيتم جمع الإعلانات منه
site = "https://edition.cnn.com"

# جلب الصفحة
html = requests.get(site).text
soup = BeautifulSoup(html,"html.parser")

# البحث عن عناصر الإعلانات
ads = soup.select(".trc_spotlight_item")

# حفظ كل إعلان في قاعدة البيانات
for ad in ads:
    title = ad.get_text(strip=True)
    img = ad.find("img")
    image = img["src"] if img else ""
    link = ad.find("a")
    landing = link["href"] if link else ""
    
    # تحضير البيانات للحفظ
    data = {
        "title": title,
        "image": image,
        "landing": landing,
        "source": site
    }
    
    # إدخال البيانات في جدول ads
    supabase.table("ads").insert(data).execute()
    print("Saved:", title)
