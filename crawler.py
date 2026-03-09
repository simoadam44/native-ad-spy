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
        # منع التكرار: البحث عن الإعلان بواسطة الرابط
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
        print(f"⚠️ DB Error: {e}")

async def scrape_site(browser, url, semaphore):
    # التحكم في عدد المواقع المتوازية (مثلاً 2 في نفس الوقت) لتفادي الـ Timeout
    async with semaphore:
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"🚀 Starting: {url}")
            # استخدام domcontentloaded لسرعة الاستجابة وتفادي فشل الانتظار الطويل
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            # انتظار بسيط بدلاً من سكون الشبكة الكامل (networkidle) الذي سبب الفشل سابقاً
            await asyncio.sleep(5) 
            
            # تمرير سريع لتحفيز ظهور الإعلانات
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
            await asyncio.sleep(2)

            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            for selector, network_name in NETWORK_MAP.items():
                elements = soup.select(selector)
                for ad in elements:
                    try:
                        link_tag = ad.find("a")
                        if not link_tag or not link_tag.get("href"): continue
                        
                        landing = urljoin(url, link_tag.get("href"))
                        title = ad.get_text(strip=True)
                        
                        img_tag = ad.find("img")
                        image_raw = img_tag.get("src") or img_tag.get("data-src") or "" if img_tag else ""
                        image_url = urljoin(url, image_raw) if image_raw else ""

                        if title and len(title) > 10:
                            await save_or_update_ad({
                                "title": title[:200],
                                "image": image_url,
                                "landing": landing,
                                "source": url,
                                "network": network_name
                            })
                    except: continue
                    
        except Exception as e:
            print(f"⚠️ Timeout/Error at {url}: {str(e)[:50]}")
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

    # السماح لموقعين فقط بالعمل معاً لتخفيف الضغط على GitHub Actions
    semaphore = asyncio.Semaphore(2)

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        tasks = [scrape_site(browser, site, semaphore) for site in sites]
        await asyncio.gather(*tasks)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_spy())
