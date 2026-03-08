import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from supabase import create_client

# --- إعدادات سوبابيز الخاصة بك ---
SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def run_spy():
    # مواقع تحتوي على إعلانات ناتيف بوضوح
    sites = [
        "https://www.tips-and-tricks.co/online/sisterrevenge/2/",
        "https://www.standard.co.uk/news/world/ukraine-war-russia-putin-b1100000.html"
    ]

    async with async_playwright() as p:
        # تشغيل المتصفح مع إعدادات تخطي الحماية
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for site in sites:
            print(f"\n🔍 فحص الموقع: {site}")
            try:
                # محاولة فتح الموقع
                await page.goto(site, timeout=60000, wait_until="domcontentloaded")
                
                # النزول لأسفل لتفعيل الإعلانات
                print("⏬ جاري النزول لأسفل الصفحة (Scroll)...")
                for _ in range(5):
                    await page.mouse.wheel(0, 1500)
                    await asyncio.sleep(1)
                
                await asyncio.sleep(5) # انتظار أخير للتحميل

                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                # محددات الإعلانات الشاملة
                ad_selectors = [
                    ".trc_spotlight_item", ".ob-dynamic-rec-container", 
                    ".mg-item", ".taboola-main-container", "[id*='taboola']",
                    ".item-container-mgid", ".outbrain-column"
                ]
                
                found_elements = []
                for selector in ad_selectors:
                    found_elements.extend(soup.select(selector))
                
                # تنظيف القائمة من العناصر المتكررة
                unique_ads = list(set(found_elements))
                print(f"✅ تم العثور على {len(unique_ads)} عنصر محتمل.")

                for ad in unique_ads:
                    title = ad.get_text(strip=True)
                    img = ad.find("img")
                    image = ""
                    if img:
                        image = img.get("src") or img.get("data-src") or img.get("data-lazy-src") or ""
                    
                    link = ad.find("a")
                    landing = link.get("href") if link else ""

                    if title and len(title) > 15 and landing:
                        if landing.startswith("//"): landing = "https:" + landing
                        
                        data = {"title": title[:200], "image": image, "landing": landing, "source": site}
                        
                        # إرسال البيانات لسوبابيز
                        supabase.table("ads").insert(data).execute()
                        print(f"📥 تم الحفظ: {title[:30]}...")

            except Exception as e:
                print(f"❌ خطأ في {site}: {e}")

        await browser.close()

# --- الجزء الذي تم إصلاحه ليعمل في GitHub ---
if __name__ == "__main__":
    asyncio.run(run_spy())
