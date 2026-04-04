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

# إعداد الدولة والبروكسي المتطور (DataImpulse)
TARGET_COUNTRY = os.environ.get("TARGET_COUNTRY", "US")

PROXY_CONFIG = {
    "server": "http://gw.dataimpulse.com:823",
    "username": f"85ccde32f1cc6c7ad458__country-{TARGET_COUNTRY}",
    "password": "78c188c405598b8a"
}

COUNTRY_CONFIGS = {
    "US": {"locale": "en-US", "timezone_id": "America/New_York"},
    "GB": {"locale": "en-GB", "timezone_id": "Europe/London"},
    "CA": {"locale": "en-CA", "timezone_id": "America/Toronto"},
    "AU": {"locale": "en-AU", "timezone_id": "Australia/Sydney"},
    "DE": {"locale": "de-DE", "timezone_id": "Europe/Berlin"},
    "FR": {"locale": "fr-FR", "timezone_id": "Europe/Paris"},
    "IT": {"locale": "it-IT", "timezone_id": "Europe/Rome"},
    "ES": {"locale": "es-ES", "timezone_id": "Europe/Madrid"},
    "NL": {"locale": "nl-NL", "timezone_id": "Europe/Amsterdam"},
    "SE": {"locale": "sv-SE", "timezone_id": "Europe/Stockholm"},
    "SA": {"locale": "ar-SA", "timezone_id": "Asia/Riyadh"},
    "AE": {"locale": "ar-AE", "timezone_id": "Asia/Dubai"},
    "MA": {"locale": "ar-MA", "timezone_id": "Africa/Casablanca"},
    "EG": {"locale": "ar-EG", "timezone_id": "Africa/Cairo"},
    "ZA": {"locale": "en-ZA", "timezone_id": "Africa/Johannesburg"},
    "JP": {"locale": "ja-JP", "timezone_id": "Asia/Tokyo"},
    "KR": {"locale": "ko-KR", "timezone_id": "Asia/Seoul"},
    "IN": {"locale": "en-IN", "timezone_id": "Asia/Kolkata"},
    "BR": {"locale": "pt-BR", "timezone_id": "America/Sao_Paulo"},
    "MX": {"locale": "es-MX", "timezone_id": "America/Mexico_City"}
}
GEO = COUNTRY_CONFIGS.get(TARGET_COUNTRY, COUNTRY_CONFIGS["US"])


# استهداف المواقع التي أثبتت التقارير أنها تحتوي على طابولا نشط ومقالات
TABOOLA_ARTICLE_SITES = [
    "https://www.independent.co.uk/sport/football/fa-cup-draw-semi-final-date-time-tv-ball-numbers-b2950304.html", # مقال مباشر
    "https://www.notimerica.com/politica/noticia-ucrania-zelenski-advierte-rusia-podria-estar-preparando-gran-ataque-aereo-20260323211616.html", # مقال مباشر
    "https://www.notimerica.com/politica/noticia-ucrania-zelenski-advierte-rusia-podria-estar-preparando-gran-ataque-aereo-20260323211616.html",
    "https://www.houseandgarden.co/its-allergy-season-allergy-proof-you-home-with-these-5-tips/#",
    "https://www.trucs-et-astuces.co/online/robocrab/"
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
                "last_seen": "now()",
                "country_code": TARGET_COUNTRY
            }).eq("id", existing.data[0]['id']).execute()
            print(f"📈 [TABOOLA] [{TARGET_COUNTRY}]: تحديث ({new_count}): {data['title'][:30]}")
        else:
            data.update({"impressions": 1, "last_seen": "now()", "country_code": TARGET_COUNTRY})
            supabase.table("ads").insert(data).execute()
            print(f"✨ [TABOOLA] [{TARGET_COUNTRY}]: صيد جديد: {data['title'][:30]}")
    except Exception as e:
        print(f"⚠️ [TABOOLA] DB Error: {e}")


async def scrape_taboola(browser, url, semaphore):
    async with semaphore:
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale=GEO["locale"],
            timezone_id=GEO["timezone_id"],
            permissions=["geolocation"]
        )
        page = await context.new_page()
        
        # 🚫 خطة الحظر العنيفة جداً (Zero-Trust) لتوفير الباندويث
        async def block_resources(route):
            req = route.request
            res_type = req.resource_type
            url = req.url.lower()

            if res_type in ["image", "media", "font", "stylesheet", "websocket", "manifest", "other"]:
                await route.abort()
                return

            blocked_domains = [
                "google", "facebook", "twitter", "tiktok", "snapchat", "pinterest",
                "chartbeat", "btloader", "surveygizmo", "scorecardresearch", "hotjar",
                "criteo", "amazon", "rubicon", "openx", "pubmatic", "quantserve", "adroll",
                "mediavoice", "teads", "clarity", "doubleclick",
                "mgid", "outbrain", "revcontent", "sharethis"
            ]
            
            if any(kw in url for kw in blocked_domains) and "taboola.com" not in url:
                await route.abort()
                return

            if res_type in ["script", "fetch", "xhr"]:
                if "taboola.com" in url:
                    await route.continue_()
                    return
                # حظر ملفات الفيديو واللاعبين الثقيلة لتوفير البانوديث
                if any(sub in url for sub in ["player.", "video.", "api."]):
                    await route.abort()
                    return

            await route.continue_()

        await page.route("**/*", block_resources)
        
        try:
            print(f"🚀 [TABOOLA]: فحص مقال/قسم مباشر: {url}")
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            # محاكاة التمرير التدريجي لتحفيز ظهور إعلانات Taboola أسفل المقال
            await asyncio.sleep(3)
            for i in range(1, 8):
                await page.evaluate(f"window.scrollTo(0, document.body.scrollHeight * {i/7})")
                await asyncio.sleep(1.5)
            
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
        print(f"Launching independent Chrome browser with proxy for {TARGET_COUNTRY}...")
        browser = await p.chromium.launch(
            headless=True, 
            proxy=PROXY_CONFIG,
            args=[
                "--blink-settings=imagesEnabled=false",
                "--disable-features=IsolateOrigins,site-per-process",
                "--disable-background-networking",
                "--disable-dev-shm-usage",
                "--disable-extensions",
                "--disable-sync",
                "--no-sandbox"
            ]
        )
        await asyncio.gather(*[scrape_taboola(browser, s, semaphore) for s in TABOOLA_ARTICLE_SITES])
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_spy())
