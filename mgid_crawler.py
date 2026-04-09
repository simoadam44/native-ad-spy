import asyncio
import os
import random
import sys
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from supabase import create_client

# إعداد الإخراج ليدعم اليونيكود
sys.stdout.reconfigure(encoding='utf-8')

# --- إعدادات سوبابيز ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY) if SUPABASE_URL and SUPABASE_KEY else None

# --- إعدادات الدولة والبروكسي (DataImpulse) ---
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
    "MA": {"locale": "ar-MA", "timezone_id": "Africa/Casablanca"},
    "SA": {"locale": "ar-SA", "timezone_id": "Asia/Riyadh"},
    "AE": {"locale": "ar-AE", "timezone_id": "Asia/Dubai"},
}
GEO = COUNTRY_CONFIGS.get(TARGET_COUNTRY, COUNTRY_CONFIGS["US"])

# --- قائمة الأهداف ---
MGID_TARGETS = [
    "https://pjmedia.com/vodkapundit/2026/03/23/are-you-ready-for-the-dems-2028-presidential-childhood-trauma-olympics-n4950953",
    "https://www.ibtimes.com/us-secured-secret-deal-cameroon-deport-migrants-using-aid-leverage-report-3800110",
    "https://brainberries.co/interesting/britney-spears-then-vs-now-her-changing-face-in-photos/",
    "https://herbeauty.co/ar/altarfih/maqati-video-raqs-zouk-lan-tastatia-at-tawaqquf-an-mushahadatiha-miraran-wa-takraran/",
    "https://buzzday.info/2026/02/13/what-happens-if-you-consume-ginger-every-day/?utm_source=mgid.com",
    "https://zestradar.com/celebrities/the-worst-beckham-family-rumors-theyll-never-outrun/"
]

async def save_to_supabase(ad):
    if not supabase or not ad.get('title') or not ad.get('landing'):
        return
    try:
        # تنظيف الرابط من البارامترات الزائدة
        clean_url = ad['landing'].split('?')[0]
        res = supabase.table("ads").select("id, impressions").eq("landing", clean_url).execute()
        
        if res.data:
            new_imp = (res.data[0].get('impressions') or 1) + 1
            supabase.table("ads").update({
                "impressions": new_imp, 
                "last_seen": "now()", 
                "country_code": TARGET_COUNTRY
            }).eq("id", res.data[0]['id']).execute()
            print(f"[UPDATE] {TARGET_COUNTRY}: ({new_imp} imps) - {ad['title'][:50]}...")
        else:
            ad.update({"landing": clean_url, "impressions": 1, "last_seen": "now()", "country_code": TARGET_COUNTRY})
            supabase.table("ads").insert(ad).execute()
            print(f"[NEW AD] {TARGET_COUNTRY}: {ad['title'][:50]}...")
    except Exception as e:
        print(f"[DB ERROR]: {e}")

async def handle_route(route):
    """حظر الموارد غير الضرورية لتوفير الداتا والسرعة"""
    req = route.request
    excluded_types = ["image", "media", "font", "stylesheet", "websocket", "manifest"]
    
    if req.resource_type in excluded_types:
        return await route.abort()
    
    url = req.url.lower()
    # حظر سكريبتات التتبع والطرف الثالث باستثناء MGID
    blocked_patterns = ["google-analytics", "facebook", "tiktok", "hotjar", "clarity", "doubleclick"]
    if any(p in url for p in blocked_patterns) and "mgid" not in url:
        return await route.abort()
        
    await route.continue_()

async def scrape_mgid(page, url):
    print(f"🔍 Scanning: {url}")
    mgid_ads = []

    # اعتراض استجابات الـ JSON من سيرفرات MGID مباشرة
    async def intercept_response(response):
        if "mgid.com" in response.url and response.status == 200:
            try:
                data = await response.json()
                items = data.get('items') or data.get('data') or []
                for item in items:
                    if isinstance(item, dict) and (item.get('title') or item.get('text')):
                        mgid_ads.append({
                            "title": (item.get('title') or item.get('text')).strip(),
                            "landing": item.get('articleUrl') or item.get('targetUrl') or item.get('url'),
                            "image": item.get('mainImage') or item.get('thumbnail'),
                            "network": "MGID",
                            "source": url
                        })
            except: pass

    page.on("response", intercept_response)

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        # محاكاة التصفح لتفعيل Lazy Load
        for _ in range(3):
            await page.mouse.wheel(0, 1000)
            await asyncio.sleep(1.5)

        # استخراج من خلال JavaScript (في حال كانت البيانات مخزنة في Window Object)
        js_results = await page.evaluate("""
            () => {
                let found = [];
                for (let key in window) {
                    if (key.includes('mgid') && typeof window[key] === 'object') {
                        let data = window[key].items || window[key].ads || [];
                        if (Array.isArray(data)) {
                            data.forEach(item => {
                                if (item.title) found.push({
                                    title: item.title,
                                    landing: item.articleUrl || item.url,
                                    image: item.mainImage || item.thumbnail
                                });
                            });
                        }
                    }
                }
                return found;
            }
        """)
        for item in js_results:
            mgid_ads.append({**item, "network": "MGID", "source": url})

        # معالجة النتائج وإزالة التكرار
        unique_ads = {}
        for ad in mgid_ads:
            if not ad.get('title') or not ad.get('landing'): continue
            key = ad['title'].lower()[:60]
            if key not in unique_ads or ("clck.mgid" in unique_ads[key]['landing'] and "clck.mgid" not in ad['landing']):
                unique_ads[key] = ad

        for ad in unique_ads.values():
            await save_to_supabase(ad)

    except Exception as e:
        print(f"⚠️ Error on {url}: {e}")
    finally:
        page.remove_listener("response", intercept_response)

async def run():
    async with async_playwright() as p:
        print(f"🚀 Starting Scraper for {TARGET_COUNTRY} via DataImpulse...")
        
        browser = await p.chromium.launch(
            headless=True,
            proxy=PROXY_CONFIG,
            args=["--no-sandbox", "--disable-setuid-sandbox", "--disable-dev-shm-usage"]
        )
        
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            locale=GEO["locale"],
            timezone_id=GEO["timezone_id"]
        )

        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        # تفعيل نظام حظر الموارد لتقليل الاستهلاك
        await page.route("**/*", handle_route)

        for target in MGID_TARGETS:
            await scrape_mgid(page, target)
            await asyncio.sleep(random.uniform(2, 5))

        await browser.close()
        print("🏁 Task Completed.")

if __name__ == "__main__":
    asyncio.run(run())
