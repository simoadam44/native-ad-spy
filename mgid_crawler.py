import asyncio, os, random, sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from supabase import create_client

# إعداد سوبابيز
try:
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    if supabase_url and supabase_key:
        supabase = create_client(supabase_url, supabase_key)
    else:
        supabase = None
except Exception as e:
    supabase = None

# إعداد الدولة والبروكسي المتطور (DataImpulse)
TARGET_COUNTRY = os.environ.get("TARGET_COUNTRY", "US")

PROXY_CONFIG = {
    "server": "http://gw.dataimpulse.com:823",
    "username": f"85ccde32f1cc6c7ad458__country-{TARGET_COUNTRY}",
    "password": "78c188c405598b8a"
}

COUNTRY_CONFIGS = {
    "US": {"locale": "en-US", "timezone_id": "America/New_York"},
    "MA": {"locale": "ar-MA", "timezone_id": "Africa/Casablanca"},
    "SA": {"locale": "ar-SA", "timezone_id": "Asia/Riyadh"},
    "AE": {"locale": "ar-AE", "timezone_id": "Asia/Dubai"},
    # ... بقية الإعدادات كما هي في كودك الأصلي
}
GEO = COUNTRY_CONFIGS.get(TARGET_COUNTRY, COUNTRY_CONFIGS["US"])

MGID_TARGETS = [url.strip() for url in [
    "https://pjmedia.com/vodkapundit/2026/03/23/are-you-ready-for-the-dems-2028-presidential-childhood-trauma-olympics-n4950953",
    "https://www.ibtimes.com/us-secured-secret-deal-cameroon-deport-migrants-using-aid-leverage-report-3800110",
    "https://herbeauty.co/ar/altarfih/maqati-video-raqs-zouk-lan-tastatia-at-tawaqquf-an-mushahadatiha-miraran-wa-takraran/",
    "https://buzzday.info/2026/02/13/what-happens-if-you-consume-ginger-every-day/",
    "https://zestradar.com/celebrities/the-worst-beckham-family-rumors-theyll-never-outrun/"
]]

async def save_to_supabase(ad):
    try:
        if not ad.get('title') or not ad.get('landing'): return
        # تنظيف الرابط من البارامترات الزائدة
        clean_url = ad['landing'].split('?')[0].split('#')[0]
        
        if not supabase: return

        res = supabase.table("ads").select("id, impressions").eq("landing", clean_url).execute()
        
        if res.data:
            new_imp = (res.data[0].get('impressions') or 1) + 1
            supabase.table("ads").update({"impressions": new_imp, "last_seen": "now()", "country_code": TARGET_COUNTRY}).eq("id", res.data[0]['id']).execute()
            print(f"[MGID] [{TARGET_COUNTRY}]: تحديث ({new_imp}): {ad['title'][:40]}...")
        else:
            ad.update({"landing": clean_url, "impressions": 1, "last_seen": "now()", "country_code": TARGET_COUNTRY})
            supabase.table("ads").insert(ad).execute()
            print(f"[MGID] [{TARGET_COUNTRY}]: صيد جديد ✅: {ad['title'][:40]}...")
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

    # حظر الموارد لتقليل استهلاك الداتا
    async def block_resources(route):
        if route.request.resource_type in ["image", "media", "font"]:
            await route.abort()
        else:
            await route.continue_()
    await page.route("**/*", block_resources)

    try:
        print(f"Scraping: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5) # انتظار تحميل الـ Widgets

        # ✅ الحل الرئيسي: استخراج الرابط الحقيقي من DOM مباشرة
        # نركز على mctitle a و mgline a كما في الصورة التي أرفقتها
        dom_ads = await page.evaluate("""
            () => {
                let ads = [];
                // استهداف الروابط داخل حاويات MGID المعروفة
                let selectors = '.mctitle a, .mgline a, .mgbox a, [class*="mgid"] a';
                document.querySelectorAll(selectors).forEach(a => {
                    let title = a.innerText.strip();
                    let href = a.getAttribute('href');
                    
                    // إذا كان الرابط لا يحتوي على clck.mgid.com فهو الرابط الحقيقي المطلوب
                    if (title.length > 5 && href && !href.includes('clck.mgid.com')) {
                        let img = a.closest('[class*="mgbox"], [class*="mgline"]').querySelector('img');
                        ads.push({
                            title: title,
                            landing: href,
                            image: img ? (img.src || img.dataset.src) : '',
                            network: "MGID"
                        });
                    }
                });
                return ads;
            }
        """)
        
        if dom_ads:
            print(f"✅ تم العثور على {len(dom_ads)} رابط حقيقي مباشرة من الـ HTML")
            mgid_ads.extend(dom_ads)

        # احتياطي: السكرول لتنشيط المزيد من الإعلانات
        await page.evaluate("window.scrollBy(0, 1000)")
        await asyncio.sleep(2)

        # معالجة وحفظ النتائج
        unique_ads = {}
        for ad in mgid_ads:
            key = ad['title'].lower()[:50] # مفتاح فريد بناءً على العنوان
            if key not in unique_ads:
                ad['source'] = url
                unique_ads[key] = ad
        
        for ad in unique_ads.values():
            await save_to_supabase(ad)

    except Exception as e:
        print(f"Error in {url}: {e}")
    finally:
        await page.close()
        await context.close()

async def run():
    async with async_playwright() as p:
        print(f"Starting Scraper for {TARGET_COUNTRY}...")
        browser = await p.chromium.launch(headless=True, proxy=PROXY_CONFIG)
        
        for target in MGID_TARGETS:
            await scrape_mgid(browser, target)
            await asyncio.sleep(random.uniform(2, 5))
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
