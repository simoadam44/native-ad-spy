import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from supabase import create_client

# إعداداتك
SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def run_spy():
    # استعملنا رابط مقال مباشر لأنه يحتوي دائماً على إعلانات في الأسفل
    sites = [
        "https://www.tips-and-tricks.co/online/sisterrevenge/2/",
        "https://www.standard.co.uk/news/world/ukraine-war-russia-putin-b1100000.html"
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # إضافة User-Agent قوي جداً
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for site in sites:
            print(f"\n🔍 فحص الموقع: {site}")
            try:
                # لا ننتظر networkidle لأنه يأخذ وقتاً طويلاً، ننتظر فقط تحميل المحتوى الأساسي
                await page.goto(site, timeout=45000, wait_until="domcontentloaded")
                
                print("⏬ جاري النزول لأسفل الصفحة (Scroll) بقوة...")
                # ننزل للأسفل عدة مرات لضمان ظهور الإعلانات
                for _ in range(5):
                    await page.mouse.wheel(0, 1500)
                    await asyncio.sleep(1)
                
                # انتظار إضافي بسيط
                await asyncio.sleep(5)

                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                # محددات "عامة" جداً تبحث عن أي رابط داخل حاوية إعلانات مشهورة
                # هذه المحددات تغطي Taboola و Outbrain و MGID بشكل أفضل
                ad_selectors = [
                    ".trc_spotlight_item", ".ob-dynamic-rec-container", 
                    ".mg-item", ".taboola-main-container", "[id*='taboola']",
                    ".item-container-mgid", ".outbrain-column"
                ]
                
                found_ads = []
                for selector in ad_selectors:
                    found_ads.extend(soup.select(selector))
                
                # إزالة التكرار
                found_ads = list(set(found_ads))
                print(f"✅ تم العثور على {len(found_ads)} عنصر إعلاني محتمل.")

                for ad in found_ads:
                    title = ad.get_text(strip=True)
                    img = ad.find("img")
                    # محاولة جلب الصورة من src أو data-src (لأنها تكون مخفية أحياناً)
                    image = ""
                    if img:
                        image = img.get("src") or img.get("data-src") or img.get("data-lazy-src") or ""
                    
                    link = ad.find("a")
                    landing = link.get("href") if link else ""

                    if title and len(title) > 15 and landing:
                        # تنظيف الرابط إذا كان ناقصاً
                        if landing.startswith("//"): landing = "https:" + landing
                        
                        data = {"title": title[:200], "image": image, "landing": landing, "source": site}
                        
                        # الحفظ في سوبابيز
                        supabase.table("ads").insert(data).execute()
                        print(f"📥 تم الحفظ بنجاح: {title[:40]}...")

            except Exception as e:
                print(f"❌ خطأ في {site}: {e}")

        await browser.close()
        print("\n🏁 انتهت المهمة!")

# تشغيل في Colab
await run_spy()
