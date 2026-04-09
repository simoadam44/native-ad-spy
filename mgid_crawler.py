import asyncio, os, random, sys, httpx
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from supabase import create_client

# إعداد سوبابيز
try:
    supabase_url = os.environ.get("SUPABASE_URL")
    supabase_key = os.environ.get("SUPABASE_KEY")
    supabase = create_client(supabase_url, supabase_key) if (supabase_url and supabase_key) else None
except Exception:
    supabase = None

# إعداد الدولة والبروكسي
TARGET_COUNTRY = os.environ.get("TARGET_COUNTRY", "US")
PROXY_CONFIG = {
    "server": "http://gw.dataimpulse.com:823",
    "username": f"85ccde32f1cc6c7ad458__country-{TARGET_COUNTRY}",
    "password": "78c188c405598b8a"
}

MGID_TARGETS = [
    "https://pjmedia.com/vodkapundit/2026/03/23/are-you-ready-for-the-dems-2028-presidential-childhood-trauma-olympics-n4950953",
    "https://www.ibtimes.com/us-secured-secret-deal-cameroon-deport-migrants-using-aid-leverage-report-3800110",
    "https://herbeauty.co/ar/altarfih/maqati-video-raqs-zouk-lan-tastatia-at-tawaqquf-an-mushahadatiha-miraran-wa-takraran/",
    "https://buzzday.info/2026/02/13/what-happens-if-you-consume-ginger-every-day/",
    "https://zestradar.com/celebrities/the-worst-beckham-family-rumors-theyll-never-outrun/"
]

async def resolve_final_url(url):
    """تتبع روابط التحويل للوصول للرابط النهائي"""
    if 'clck.mgid.com' not in url and 'clck.adskeeper' not in url:
        return url
    try:
        headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
        async with httpx.AsyncClient(follow_redirects=True, headers=headers, timeout=12) as client:
            response = await client.get(url)
            return str(response.url)
    except Exception:
        return url

async def save_to_supabase(ad):
    if not supabase or not ad.get('title'): return
    try:
        # فك روابط التتبع قبل الحفظ
        landing_url = await resolve_final_url(ad['landing'])
        clean_url = landing_url.split('?')[0].split('#')[0]

        ad_data = {
            "title": ad['title'],
            "landing": clean_url,
            "image": ad.get('image', ''),
            "source": ad.get('source', ''),
            "network": "MGID",
            "country_code": TARGET_COUNTRY,
            "last_seen": "now()"
        }
        supabase.table("ads").upsert(ad_data, on_conflict="landing").execute()
        print(f"✨ [MGID] [{TARGET_COUNTRY}]: تم الحفظ: {ad['title'][:40]}...")
    except Exception as e:
        print(f"❌ [DB ERROR]: {e}")

async def scrape_mgid(browser, url):
    context = await browser.new_context(viewport={'width': 1280, 'height': 800})
    page = await context.new_page()
    await Stealth().apply_stealth_async(page)
    
    # توفير الداتا
    await page.route("**/*", lambda route: route.abort() if route.request.resource_type in ["image", "media", "font"] else route.continue_())

    try:
        print(f"🚀 [MGID]: فحص الهدف: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(7) # انتظار تحميل الويدجت

        ads = await page.evaluate("""
            () => {
                let found = [];
                let selectors = '.mctitle a, .mgline a, .mgbox a, [class*="mgid"] a, .mg-teaser a';
                document.querySelectorAll(selectors).forEach(a => {
                    let title = a.innerText.trim();
                    if (title.length > 5) {
                        let landing = a.dataset.url || a.dataset.landing || a.getAttribute('data-url') || a.href;
                        let imgEl = a.closest('div, ins, li')?.querySelector('img');
                        let imgSrc = imgEl ? (imgEl.src || imgEl.dataset.src) : '';
                        found.push({ title: title, landing: landing, image: imgSrc });
                    }
                });
                return found;
            }
        """)

        if ads:
            for ad in ads:
                ad['source'] = url
                await save_to_supabase(ad)
        else:
            print(f"ℹ️ [MGID]: لم يتم رصد إعلانات في {url}")

    except Exception as e:
        print(f"⚠️ [MGID ERROR]: {url} -> {e}")
    finally:
        await page.close()
        await context.close()

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, proxy=PROXY_CONFIG)
        for target in MGID_TARGETS:
            await scrape_mgid(browser, target)
            await asyncio.sleep(random.uniform(2, 4))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
