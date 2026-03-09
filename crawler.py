
import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from supabase import create_client
from urllib.parse import urljoin
import re

# --- إعدادات سوبابيز ---
SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

NETWORK_MAP = {
    ".trc_spotlight_item": "Taboola",
    ".taboola-main-container": "Taboola",
    "[id*='taboola']": "Taboola",
    ".mg-item": "MGID",
    ".item-container-mgid": "MGID",
    ".outbrain-column": "Outbrain",
    ".ob-dynamic-rec-container": "Outbrain"
}

async def save_or_update_ad(data):
    """حفظ إعلان جديد أو تحديث إعلان موجود لزيادة الـ Impressions"""
    try:
        # التحقق من وجود الإعلان مسبقاً بناءً على رابط الهبوط
        existing = supabase.table("ads").select("id, impressions").eq("landing", data['landing']).execute()
        
        if existing.data:
            # تحديث الإعلان الحالي: زيادة الـ impressions وتحديث last_seen
            current_imp = existing.data[0].get('impressions') or 1
            supabase.table("ads").update({
                "impressions": current_imp + 1,
                "last_seen": "now()" 
            }).eq("id", existing.data[0]['id']).execute()
            print(f"📈 تم تحديث الظهور ({current_imp + 1}): {data['title'][:30]}...")
        else:
            # إدراج إعلان جديد لأول مرة مع القيم الافتراضية
            data["impressions"] = 1
            data["last_seen"] = "now()"
            supabase.table("ads").insert(data).execute()
            print(f"✨ إعلان جديد مكتشف: {data['title'][:30]}...")
    except Exception as e:
        print(f"⚠️ خطأ في قاعدة البيانات: {e}")

async def scrape_site(browser, url, semaphore):
    """فحص موقع واحد مع الحماية من الـ NoneType والـ Timeout"""
    async with semaphore: # التحكم في عدد المواقع المتوازية
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"🚀 جاري فحص: {url}")
            # استخدام domcontentloaded لسرعة الاستجابة
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            # انتظار يدوي بسيط بدلاً من الانتظار اللانهائي للشبكة
            await asyncio.sleep(5) 
            
            # تمرير الصفحة لتحفيز الإعلانات
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
            await asyncio.sleep(2)

            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            for selector, network_name in NETWORK_MAP.items():
                elements = soup.select(selector)
                for ad in elements:
                    try:
                        # حماية ضد أخطاء الـ NoneType
                        link_tag = ad.find("a")
                        if not link_tag or not link_tag.get("href"):
                            continue
                        
                        landing = urljoin(url, link_tag.get("href"))
                        title = ad.get_text(strip=True)
                        
                        # استخراج الصورة مع حماية
                        img_tag = ad.find("img")
                        image_raw = ""
                        if img_tag:
                            image_raw = img_tag.get("src") or img_tag.get("data-src") or img_tag.get("data-lazy-src") or ""
                        
                        image_url = urljoin(url, image_raw) if image_raw else ""

                        if title and len(title) > 12:
                            await save_or_update_ad({
                                "title": title[:200],
                                "image": image_url,
                                "landing": landing,
                                "source": url,
                                "network": network_name
                            })
                    except:
                        continue
                        
        except Exception as e:
            print(f"⚠️ فشل الموقع {url}: {str(e)[:50]}...")
        finally:
            await page.close()
            await context.close()

async def run_spy():
    sites = [
        "https://www.tips-and-tricks.co/online/sisterrevenge/2/",
        "https://www.dailysportx.com/news/vveins",
        "https://www.tag24.de/anzeige/unglaublich-podcast-spotify-medien-macht-wahrheit-ankuendigung-abnonnieren-3475140",
        "https://www.standard.co.uk/news/world/ukraine-war-russia-putin-b1100000.html",
        "https://www.articleskill.com/fitness-health/lazfit"
    ]

    # تحديد موقعين فقط في نفس الوقت لتفادي ضغط GitHub Actions
    semaphore = asyncio.Semaphore(2)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # تنفيذ الفحص المتوازي (السرعة القصوى الآمنة)
        tasks = [scrape_site(browser, site, semaphore) for site in sites]
        await asyncio.gather(*tasks)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_spy())
