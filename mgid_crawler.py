import asyncio, os, random, sys, re
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from supabase import create_client

# إعداد سوبابيز
try:
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    supabase = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None
except Exception:
    supabase = None

# إعدادات الدولة والبروكسي
TARGET_COUNTRY = os.environ.get("TARGET_COUNTRY", "US")
PROXY_CONFIG = {
    "server": "http://gw.dataimpulse.com:823",
    "username": f"85ccde32f1cc6c7ad458__country-{TARGET_COUNTRY}",
    "password": "78c188c405598b8a"
}

COUNTRY_CONFIGS = {
    "US": {"locale": "en-US", "timezone_id": "America/New_York"},
    "MA": {"locale": "ar-MA", "timezone_id": "Africa/Casablanca"},
    # ... باقي الإعدادات تظل كما هي
}
GEO = COUNTRY_CONFIGS.get(TARGET_COUNTRY, COUNTRY_CONFIGS["US"])

MGID_TARGETS = [
    "https://pjmedia.com/vodkapundit/2026/03/23/are-you-ready-for-the-dems-2028-presidential-childhood-trauma-olympics-n4950953",
    "https://www.ibtimes.com/us-secured-secret-deal-cameroon-deport-migrants-using-aid-leverage-report-3800110",
    "https://brainberries.co/interesting/britney-spears-then-vs-now-her-changing-face-in-photos/",
    "https://buzzday.info/2026/02/13/what-happens-if-you-consume-ginger-every-day/?utm_id=57223822&utm_medium=cpc&utm_source=mgid.com",
]

# ✅ وظيفة مستخرج الروابط (Link Extractor) للوصول للرابط النهائي
async def get_final_url(browser, tracking_url):
    if not tracking_url or "mgid.com" not in tracking_url:
        return tracking_url
    
    context = await browser.new_context(no_viewport=True)
    page = await context.new_page()
    final_url = tracking_url
    
    try:
        # اعتراض الطلبات لمنع تحميل الموقع النهائي بالكامل (توفير داتا)
        await page.route("**/*", lambda route: 
            route.abort() if route.request.resource_type in ["image", "media", "font", "stylesheet"] 
            else route.continue_())
        
        # الانتقال للرابط وانتظار أول تغيير في العنوان
        response = await page.goto(tracking_url, wait_until="commit", timeout=15000)
        await asyncio.sleep(2) # انتظار بسيط للتحويلات (Redirects)
        final_url = page.url.split('?')[0] # تنظيف الرابط من التتبع
        
    except Exception as e:
        print(f"  [Link Extractor] Error resolving {tracking_url[:30]}: {e}")
    finally:
        await page.close()
        await context.close()
    return final_url

async def save_to_supabase(ad):
    try:
        if not ad.get('title') or not ad.get('landing'): return
        
        res = supabase.table("ads").select("id, impressions").eq("landing", ad['landing']).execute()
        
        if res.data:
            new_imp = (res.data[0].get('impressions') or 1) + 1
            supabase.table("ads").update({
                "impressions": new_imp, 
                "last_seen": "now()", 
                "country_code": TARGET_COUNTRY
            }).eq("id", res.data[0]['id']).execute()
            print(f"[MGID] Updated: {ad['title'][:40]}... ({new_imp} times)")
        else:
            ad.update({"impressions": 1, "last_seen": "now()", "country_code": TARGET_COUNTRY})
            supabase.table("ads").insert(ad).execute()
            print(f"✨ [MGID] New Ad Captured: {ad['title'][:40]}...")
    except Exception as e:
        print(f"[DB ERROR]: {e}")

async def scrape_mgid(browser, url):
    mgid_ads = []
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        locale=GEO["locale"],
        timezone_id=GEO["timezone_id"]
    )
    page = await context.new_page()
    await Stealth().apply_stealth_async(page)

    # حظر الموارد لتقليل الاستهلاك
    await page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff2}", lambda route: route.abort())

    async def handle_response(response):
        if "mgid.com" in response.url and response.status == 200:
            try:
                data = await response.json()
                items = data.get('items') or data.get('ads') or []
                for item in items:
                    if isinstance(item, dict) and (item.get('title') or item.get('text')):
                        mgid_ads.append({
                            "title": (item.get('title') or item.get('text', '')).strip(),
                            "landing": item.get('url') or item.get('clickUrl') or item.get('link'),
                            "image": item.get('mainImage') or item.get('thumbnail') or "",
                            "source": url,
                            "network": "MGID"
                        })
            except: pass

    page.on("response", handle_response)

    try:
        await page.goto(url, wait_until="domcontentloaded", timeout=40000)
        await asyncio.sleep(5)
        # التمرير لتنشيط الإعلانات
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, 1000)")
            await asyncio.sleep(1)

        # فلترة النتائج واستخراج الروابط النهائية
        unique_ads = {}
        for ad in mgid_ads:
            if not ad['landing'] or len(ad['title']) < 5: continue
            
            # منع التكرار بناءً على العنوان
            key = ad['title'][:80].lower()
            if key not in unique_ads:
                print(f"🔗 [Extractor] Resolving final URL for: {ad['title'][:30]}...")
                # ✅ استخدام المستخرج هنا قبل الحفظ
                ad['landing'] = await get_final_url(browser, ad['landing'])
                unique_ads[key] = ad

        for ad in unique_ads.values():
            await save_to_supabase(ad)

    except Exception as e:
        print(f"[Scrape Error]: {e}")
    finally:
        await page.close()
        await context.close()

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(
            headless=True,
            proxy=PROXY_CONFIG,
            args=["--no-sandbox", "--disable-dev-shm-usage"]
        )
        try:
            for target in MGID_TARGETS:
                print(f"\n🚀 Processing: {target}")
                await scrape_mgid(browser, target)
                await asyncio.sleep(random.uniform(2, 5))
        finally:
            await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
