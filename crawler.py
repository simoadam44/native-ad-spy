from playwright.sync_api import sync_playwright
from bs4 import BeautifulSoup
from supabase import create_client
import time

# --- ضع بيانات السوبابيز الخاصة بك هنا ---
SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co" # من الصورة السابقة
SUPABASE_KEY = "ضع_هنا_المفتاح_الطويل_جدا_anon_public_key"
# ------------------------------------------

def run_spy():
    supabase = create_client(SUPABASE_URL, SUPABASE_KEY)
    
    # قائمة ببعض المواقع التي تحتوي دائماً على إعلانات Taboola و Outbrain
    sites = [
        "https://www.mirror.co.uk",
        "https://www.express.co.uk",
        "https://edition.cnn.com"
    ]

    print("🚀 بدء عملية التجسس...")

    with sync_playwright() as p:
        # فتح متصفح كروم مخفي
        browser = p.chromium.launch(headless=True)
        page = browser.new_page()

        for site in sites:
            print(f"\n🔍 جاري فحص : {site}")
            try:
                # الذهاب للموقع والانتظار حتى يكتمل تحميل كل شيء
                page.goto(site, timeout=60000, wait_until="networkidle")
                
                # خدعة المحترفين: النزول لأسفل الصفحة ببطء لتفعيل إعلانات الناتيف
                print("⏬ جاري النزول لأسفل الصفحة لتحفيز ظهور الإعلانات...")
                for i in range(5):
                    page.evaluate("window.scrollBy(0, 1000);")
                    time.sleep(1)
                
                # انتظار الإعلانات لتظهر بالكامل
                time.sleep(5)

                # سحب كود HTML بعد ظهور الإعلانات
                html = page.content()
                soup = BeautifulSoup(html, "html.parser")

                # البحث عن كلاسات إعلانات تابولا، أوت براين، أو MGID وغيرها
                # دمجنا عدة محددات برمجية لضمان التقاط الاعلانات من أكثر من شبكة
                ads = soup.select(".trc_spotlight_item, .ob-dynamic-rec-container, .mgid-ad-item, .mgbox")

                print(f"✅ تم العثور على {len(ads)} عنصر يحمل اسم إعلان.")

                for ad in ads:
                    title = ad.get_text(strip=True)
                    
                    img_tag = ad.find("img")
                    image = img_tag["src"] if img_tag and "src" in img_tag.attrs else "No Image"
                    
                    # استخراج رابط الإعلان
                    link_tag = ad.find("a")
                    landing = link_tag["href"] if link_tag and "href" in link_tag.attrs else ""

                    # فلترة: إذا كان العنوان موجوداً وأطول من 10 حروف (للتأكد أنه إعلان حقيقي)
                    if title and len(title) > 10 and landing:
                        data = {
                            "title": title[:200], # أخذ أول 200 حرف حتى لا تقع مشكلة
                            "image": image,
                            "landing": landing,
                            "source": site
                        }
                        
                        # إرسال البيانات فوراً إلى قادة البيانات
                        supabase.table("ads").insert(data).execute()
                        print(f"📥 تم الحفظ بنجاح: {title[:30]}...")

            except Exception as e:
                print(f"❌ حدث خطأ في الموقع {site}: {e}")

        # إغلاق المتصفح عند الانتهاء
        browser.close()
        print("\n🏁 انتهت عملية السحب بنجاح!")

if __name__ == "__main__":
    run_spy()

