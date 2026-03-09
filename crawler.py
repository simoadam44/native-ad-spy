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
    try:
        # البحث عن الإعلان لمنع التكرار
        existing = supabase.table("ads").select("id, impressions").eq("landing", data['landing']).execute()
        
        if existing.data:
            new_count = (existing.data[0].get('impressions') or 1) + 1
            supabase.table("ads").update({
                "impressions": new_count,
                "last_seen": "now()" 
            }).eq("id", existing.data[0]['id']).execute()
            print(f"📈 Updated: {data['title'][:30]}")
        else:
            data["impressions"] = 1
            supabase.table("ads").insert(data).execute()
            print(f"✨ New Ad: {data['title'][:30]}")
    except Exception as e:
        print(f"⚠️ Database Error: {e}")

async def scrape_site(browser, url):
    # إنشاء Context مستقل لكل موقع لتفادي أخطاء الـ Logs السابقة
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
    )
    page = await context.new_page()
    
    try:
        print(f"🚀 Starting: {url}")
        # استخدام networkidle لضمان تحميل الإعلانات بالكامل
        await page.goto(url, timeout=90000, wait_until="networkidle")
        
        for _ in range(3):
            await page.mouse.wheel(0, 1000)
            await asyncio.sleep(2)
        
        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        for selector, network_name in NETWORK_MAP.items():
            elements = soup.select(selector)
            for ad in elements:
                try:
                    # حماية ضد 'NoneType' object has no attribute 'get'
                    link_tag = ad.find("a")
                    if not link_tag: continue
                    
                    landing_url = link_tag.get("href")
                    if not landing_url: continue
                    
                    landing = urljoin(url, landing_url)
                    title = ad.get_text(strip=True)
                    
                    # استخراج الصورة مع الحماية
                    img_tag = ad.find("img")
                    image_raw = ""
                    if img_tag:
                        image_raw = img_tag.get("src") or img_tag.get("data-src") or img_tag.get("data-lazy-src") or ""
                    
                    image_url = urljoin(url, image_raw) if image_raw else ""

                    if title and len(title) > 10:
                        ad_obj = {
                            "title": title[:200],
                            "image": image_url,
                            "landing": landing,
                            "source": url,
                            "network": network_name
                        }
                        await save_or_update_ad(ad_obj)
                except Exception as inner_e:
                    continue # تجاهل الإعلان المكسور والانتقال للتالي
                    
    except Exception as e:
        print(f"❌ Failed {url}: {e}")
    finally:
        await page.close()
        await context.close()

async def run_spy():
    sites = [
        "https://www.tips-and-tricks.co/online/sisterrevenge/2/",
        "https://www.dailysportx.com/news/vveins",
        "https://www.tag24.de/anzeige/unglaublich-podcast-spotify-medien-macht-wahrheit-ankuendigung-abnonnieren-3475140",
        "https://www.standard.co.uk/news/world/ukraine-war-russia-putin-b1100000.html"
    ]

    async with async_playwright() as p:
        # تشغيل المتصفح مرة واحدة فقط لجميع المهام
        browser = await p.chromium.launch(headless=True)
        
        # تنفيذ المهام بشكل متوازي (السرعة القصوى)
        tasks = [scrape_site(browser, site) for site in sites]
        await asyncio.gather(*tasks)
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_spy())
