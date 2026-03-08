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

async def run_spy():
    sites = [
        "https://www.tips-and-tricks.co/online/sisterrevenge/2/",
        "https://www.tag24.de/anzeige/unglaublich-podcast-spotify-medien-macht-wahrheit-ankuendigung-abnonnieren-3475140",
        "https://www.standard.co.uk/news/world/ukraine-war-russia-putin-b1100000.html"
    ]

    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()

        for site in sites:
            print(f"\n🔍 فحص الموقع: {site}")
            try:
                await page.goto(site, timeout=60000, wait_until="domcontentloaded")
                print("⏬ جاري النزول لأسفل الصفحة...")
                for _ in range(5):
                    await page.mouse.wheel(0, 1500)
                    await asyncio.sleep(1)
                
                await asyncio.sleep(5) 
                content = await page.content()
                soup = BeautifulSoup(content, "html.parser")
                
                ad_selectors = [
                    ".trc_spotlight_item", ".ob-dynamic-rec-container", 
                    ".mg-item", ".taboola-main-container", "[id*='taboola']",
                    ".item-container-mgid", ".outbrain-column"
                ]
                
                found_elements = []
                for selector in ad_selectors:
                    found_elements.extend(soup.select(selector))
                
                unique_ads = list(set(found_elements))
                print(f"✅ تم العثور على {len(unique_ads)} عنصر محتمل.")

                for ad in unique_ads:
                    title = ad.get_text(strip=True)
                    image_url = ""

                    # 1. البحث الشامل عن الصورة: داخل العنصر نفسه أو أي عنصر فرعي (span/div)
                    # هذا الجزء يبحث عن أي عنصر يحتوي على background-image داخل الإعلان
                    bg_elements = ad.find_all(style=re.compile("background-image"))
                    for el in bg_elements:
                        style = el.get("style", "")
                        match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
                        if match:
                            image_url = match.group(1)
                            break # وجدنا الصورة، نخرج من حلقة البحث
                    
                    # 2. الخطة البديلة: البحث عن img
                    if not image_url:
                        img_tag = ad.find("img")
                        if img_tag:
                            image_url = img_tag.get("src") or img_tag.get("data-src") or img_tag.get("data-lazy-src") or ""

                    # تصحيح الرابط
                    if image_url:
                        image_url = urljoin(site, image_url)
                        if image_url.startswith("//"): image_url = "https:" + image_url

                    link_tag = ad.find("a")
                    landing = link_tag.get("href") if link_tag else ""

                    if title and len(title) > 15 and landing:
                        landing = urljoin(site, landing)
                        data = {"title": title[:200], "image": image_url, "landing": landing, "source": site}
                        supabase.table("ads").insert(data).execute()
                        print(f"📥 تم الحفظ: {title[:30]}...")

            except Exception as e:
                print(f"❌ خطأ في {site}: {e}")

        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_spy())
