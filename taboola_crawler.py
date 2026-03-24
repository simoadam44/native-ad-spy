import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from supabase import create_client
from urllib.parse import urljoin, unquote # أضفنا unquote
import os
import re

# إعدادات سوبابيز (تأكد من وجودها في GitHub Secrets)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# استهداف المواقع التي أثبتت التقارير أنها تحتوي على طابولا نشط ومقالات
TABOOLA_ARTICLE_SITES = [
    "https://www.independent.co.uk/news/world/americas/us-politics/trump-vance-kamala-harris-b2585299.html", # مقال مباشر
    "https://www.standard.co.uk/news/politics/keir-starmer-rishi-sunak-general-election-b1161234.html", # مقال مباشر
    "https://www.dailysportx.com/news/vveins",
    "https://www.tips-and-tricks.co/online/sisterrevenge/2/"
]

async def save_or_update_ad(data):
    try:
        # منع تكرار الروابط وتنظيفها
        clean_landing = data['landing'].split('?')[0].split('#')[0]
        data['landing'] = clean_landing
        
        existing = supabase.table("ads").select("id, impressions").eq("landing", clean_landing).execute()
        
        if existing.data:
            new_count = (existing.data[0].get('impressions') or 1) + 1
            supabase.table("ads").update({
                "impressions": new_count,
                "last_seen": "now()"
            }).eq("id", existing.data[0]['id']).execute()
            print(f"📈 [TABOOLA]: تحديث ({new_count}): {data['title'][:30]}")
        else:
            data.update({"impressions": 1, "last_seen": "now()"})
            supabase.table("ads").insert(data).execute()
            print(f"✨ [TABOOLA]: صيد جديد: {data['title'][:30]}")
    except Exception as e:
        print(f"⚠️ [TABOOLA] DB Error: {e}")

async def scrape_taboola(browser, url, semaphore):
    async with semaphore:
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        try:
            print(f"🚀 [TABOOLA]: فحص مقال/قسم مباشر: {url}")
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            # محاكاة التمرير لتفعيل Lazy Loading للصور
            await asyncio.sleep(5)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight/2)")
            await asyncio.sleep(3)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight/1.2)") # تمرير أعمق للمقالات
            await asyncio.sleep(3)
            
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # محددات طابولا الأكثر شيوعاً
            selectors = [".trc_spotlight_item", ".taboola-main-container", "[id*='taboola']", ".trc_item"]
            
            for selector in selectors:
                elements = soup.select(selector)
                for ad in elements:
                    try:
                        link_tag = ad.find("a")
                        if not link_tag or not link_tag.get("href"): continue
                        
                        title_el = ad.find(class_=re.compile(r"video-title|trc_label|title"))
                        title = title_el.get_text(strip=True) if title_el else ad.get_text(strip=True)
                        landing = urljoin(url, link_tag.get("href"))

                        # --- منطق استخراج الصور المطور وحل مشكلة الاختفاء ---
                        img_tag = ad.find("img")
                        image_raw = ""
                        if img_tag:
                            image_raw = (
                                img_tag.get("data-src") or 
                                img_tag.get("src") or 
                                img_tag.get("data-lazy-src") or 
                                img_tag.get("srcset") or ""
                            )
                            if "," in image_raw:
                                image_raw = image_raw.split(",")[0].split(" ")[0]

                        # البحث في الخلفيات إذا لم نجد وسم img
                        if not image_raw:
                            bg_el = ad.find(style=re.compile(r"background-image"))
                            if bg_el:
                                style = bg_el.get("style", "")
                                match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style)
                                if match: image_raw = match.group(1)

                        # --- الحيلة السحرية: تنظيف رابط طابولا المؤقت ---
                        if "cdn.taboola.com" in image_raw or "images.taboola.com" in image_raw:
                            # 1. فك تشفير الرابط إذا كان مصغراً عبر CDN
                            if "/ui/?src=" in image_raw:
                                match = re.search(r"/ui/\?src=(.*?)&", image_raw)
                                if match:
                                    image_raw = unquote(match.group(1)) # unquote لفك تشفير الرموز
                            
                            # 2. إزالة البارامترات التي تجعل الرابط مؤقتاً (مثل توقيع الأمان &s=...)
                            image_raw = image_raw.split('?')[0]

                        # تنظيف الرابط النهائي للصورة
                        image_url = urljoin(url, image_raw) if image_raw else ""
                        if image_url.startswith("//"): image_url = "https:" + image_url
                        
                        # استثناء صور البروفايل أو الأيقونات الصغيرة جداً (التي لا تبدأ بـ https بعد التنظيف)
                        if title and len(title) > 10 and image_url.startswith("https://"):
                            await save_or_update_ad({
                                "title": title[:200],
                                "image": image_url,
                                "landing": landing,
                                "source": url,
                                "network": "Taboola"
                            })
                    except: continue
                    
        except Exception as e:
            print(f"⚠️ [TABOOLA] Error في {url}: {str(e)[:50]}")
        finally:
            await page.close()
            await context.close()

async def run_spy():
    semaphore = asyncio.Semaphore(1) 
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        await asyncio.gather(*[scrape_taboola(browser, s, semaphore) for s in TABOOLA_ARTICLE_SITES])
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_spy())
