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

# دالة لحفظ أو تحديث الإعلان (منع التكرار + زيادة الـ Impressions)
async def save_or_update_ad(data):
    try:
        # التحقق إذا كان الرابط (landing) موجود مسبقاً
        existing = supabase.table("ads").select("id, impressions").eq("landing", data['landing']).execute()
        
        if existing.data:
            # تحديث الإعلان الموجود: زيادة الـ impressions وتحديث وقت آخر ظهور
            new_count = (existing.data[0].get('impressions') or 1) + 1
            supabase.table("ads").update({
                "impressions": new_count,
                "last_seen": "now()" 
            }).eq("id", existing.data[0]['id']).execute()
            print(f"📈 تم تحديث الظهور ({new_count}): {data['title'][:30]}")
        else:
            # إدراج إعلان جديد
            data["impressions"] = 1
            supabase.table("ads").insert(data).execute()
            print(f"✨ إعلان جديد مكتشف: {data['title'][:30]}")
    except Exception as e:
        print(f"⚠️ خطأ أثناء حفظ البيانات: {e}")

async def scrape_site(browser, url):
    print(f"🔍 فحص الموقع: {url}")
    context = await browser.new_context(user_agent="Mozilla/5.0...")
    page = await context.new_page()
    
    try:
        await page.goto(url, timeout=60000, wait_until="domcontentloaded")
        
        # النزول لأسفل لتفعيل تحميل الإعلانات (Lazy Loading)
        for _ in range(3):
            await page.mouse.wheel(0, 1000)
            await asyncio.sleep(1)
        
        await asyncio.sleep(3)
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        # استخراج الإعلانات
        for selector, network_name in NETWORK_MAP.items():
            elements = soup.select(selector)
            for ad in elements:
                title = ad.get_text(strip=True)
                link_tag = ad.find("a")
                landing = urljoin(url, link_tag.get("href")) if link_tag else ""
                
                # استخراج الصورة
                img_tag = ad.find("img")
                image_url = img_tag.get("src") or img_tag.get("data-src") or ""
                image_url = urljoin(url, image_url) if image_url else ""

                if title and len(title) > 15 and landing:
                    ad_obj = {
                        "title": title[:200],
                        "image": image_url,
                        "landing": landing,
                        "source": url,
                        "network": network_name
                    }
                    await save_or_update_ad(ad_obj)
                    
    except Exception as e:
        print(f"❌ خطأ في {url}: {e}")
    finally:
        await page.close()
        await context.close()

async def run_spy():
    # قائمة المواقع المستهدفة
    main_sites = [
        "https://www.tips-and-tricks.co/online/sisterrevenge/2/",
        "https://www.dailysportx.com/news/vveins",
        "https://www.tag24.de/anzeige/unglaublich-podcast-spotify-medien-macht-wahrheit-ankuendigung-abnonnieren-3475140"
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        
        # تشغيل الفحص لكل المواقع في وقت واحد (Parallel)
        tasks = [scrape_site(browser, site) for site in main_sites]
        await asyncio.gather(*tasks)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_spy())
