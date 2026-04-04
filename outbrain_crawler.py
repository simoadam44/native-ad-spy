import asyncio, os, random, sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from supabase import create_client

# إعداد سوبابيز
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# إعداد الدولة والبروكسي المتطور
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

OUTBRAIN_TARGETS = [url.strip() for url in [
    "https://www.hespress.com",
    "https://sabq.org",
    "https://edition.cnn.com/2026/04/02/europe/us-france-trump-macron-latam-intl",
    "https://www.skynewsarabia.com",
    "https://www.independent.co.uk"
]]

async def save_to_supabase(ad):
    try:
        if not ad.get('title') or not ad.get('landing'): return
        clean_url = ad['landing'].split('&dicbo=')[0] if '&dicbo=' in ad['landing'] else ad['landing']
        res = supabase.table("ads").select("id, impressions").eq("landing", clean_url).execute()
        if res.data:
            new_imp = (res.data[0].get('impressions') or 1) + 1
            supabase.table("ads").update({"impressions": new_imp, "last_seen": "now()", "country_code": TARGET_COUNTRY}).eq("id", res.data[0]['id']).execute()
            print(f"📈 [OUTBRAIN] [{TARGET_COUNTRY}]: تحديث ({new_imp}): {ad['title'][:40]}...")
        else:
            ad.update({"landing": clean_url, "impressions": 1, "last_seen": "now()", "country_code": TARGET_COUNTRY})
            supabase.table("ads").insert(ad).execute()
            print(f"✨ [OUTBRAIN] [{TARGET_COUNTRY}]: صيد جديد: {ad['title'][:40]}...")
    except Exception as e:
        print(f"⚠️ [DB ERROR]: {e}")

async def smart_scroll_and_wait(page):
    print("🖱️ [OUTBRAIN]: جاري التمرير الذكي لتفعيل إعلانات Outbrain...")
    await page.evaluate("""
        async () => {
            await new Promise((resolve) => {
                let totalHeight = 0;
                let distance = 300;
                let timer = setInterval(() => {
                    let scrollHeight = document.body.scrollHeight;
                    window.scrollBy(0, distance);
                    totalHeight += distance;
                    if(totalHeight >= scrollHeight || totalHeight > 10000){
                        clearInterval(timer);
                        resolve();
                    }
                }, 150);
            });
        }
    """)
    await asyncio.sleep(5)

async def scrape_outbrain(browser, url):
    outbrain_ads = []
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        locale=GEO["locale"],
        timezone_id=GEO["timezone_id"],
        permissions=["geolocation"]
    )
    page = await context.new_page()
    await Stealth().apply_stealth_async(page)
    
    async def block_resources(route):
        req = route.request
        if req.resource_type in ["image", "media", "font", "stylesheet", "websocket", "manifest", "other"]:
            await route.abort()
            return
        blocked_domains = ["google", "facebook", "twitter", "tiktok", "snapchat", "pinterest", "chartbeat", "btloader", "surveygizmo", "scorecardresearch", "hotjar", "criteo", "amazon", "rubicon", "openx", "pubmatic", "quantserve", "adroll", "mediavoice", "teads", "outbrainimg.com", "clarity", "doubleclick", "mgid", "taboola", "revcontent", "sharethis"]
        if any(kw in req.url.lower() for kw in blocked_domains) and "outbrain.com" not in req.url.lower():
            await route.abort()
            return
        if req.resource_type in ["script", "fetch", "xhr"]:
            if "outbrain.com" in req.url.lower():
                await route.continue_()
                return
            if any(sub in req.url.lower() for sub in ["player.", "video."]):
                await route.abort()
                return
        await route.continue_()

    await page.route("**/*", block_resources)

    async def handle_response(response):
        nonlocal outbrain_ads
        if "outbrain.com" in response.url.lower() and response.status == 200:
            try:
                ct = response.headers.get("content-type", "")
                if "application/json" in ct or "text/javascript" in ct:
                    data = await response.json()
                    listings = []
                    if isinstance(data, dict):
                        listings = data.get('documents') or data.get('doc', {}).get('ads', []) or data.get('cards', []) or data.get('items', [])
                    elif isinstance(data, list): listings = data
                    for item in listings:
                        t = item.get('content') or item.get('title') or item.get('text')
                        l = item.get('url') or item.get('clickUrl') or item.get('link')
                        if t and l:
                            outbrain_ads.append({"title": str(t).strip(), "landing": l, "image": (item.get('image', {}) if isinstance(item.get('image'), dict) else {}).get('url') or item.get('thumbnail', ''), "source": url, "network": "OUTBRAIN"})
            except: pass

    page.on("response", handle_response)

    try:
        print(f"🚀 [OUTBRAIN]: فحص الهدف: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await smart_scroll_and_wait(page)
        
        if not outbrain_ads:
            for frame in page.frames:
                try:
                    dom_ads = await frame.evaluate("""
                        () => {
                            let found = [];
                            document.querySelectorAll('a[data-ob-url], .ob-dynamic-rec-container a, .ob-widget-items-container a, .OUTBRAIN a').forEach(el => {
                                let title = el.innerText.trim();
                                let href = el.getAttribute('data-ob-url') || el.href;
                                let src = el.querySelector('img') ? el.querySelector('img').src : '';
                                if (title.length > 15 && href && href.startsWith('http')) {
                                    found.push({title, landing: href, image: src});
                                }
                            });
                            return found;
                        }
                    """)
                    for ad in dom_ads: outbrain_ads.append({**ad, "source": url, "network": "OUTBRAIN"})
                except: pass

        if outbrain_ads:
            unique_ads = {}
            for ad in outbrain_ads:
                if ad['landing'] and ad['title'] and ad['landing'] not in unique_ads: unique_ads[ad['landing']] = ad
            for ad in unique_ads.values(): await save_to_supabase(ad)
            print(f"✅ [OUTBRAIN]: تم صيد {len(unique_ads)} إعلان في {url}")
        else:
            print(f"ℹ️ [OUTBRAIN]: لم يتم رصد إعلانات في {url}")
    except Exception as e:
        print(f"⚠️ [OUTBRAIN ERROR]: {e}")
    finally:
        await page.close()
        await context.close()

async def run():
    async with async_playwright() as p:
        print(f"Launching independent Chrome browser with proxy for {TARGET_COUNTRY}...")
        browser = await p.chromium.launch(
            headless=True, proxy=PROXY_CONFIG,
            args=["--blink-settings=imagesEnabled=false", "--disable-features=IsolateOrigins,site-per-process", "--disable-background-networking", "--disable-dev-shm-usage", "--disable-extensions", "--disable-sync", "--no-sandbox"]
        )
        for target in OUTBRAIN_TARGETS:
            print(f"Checking target: {target}")
            try: await scrape_outbrain(browser, target)
            except: pass
            await asyncio.sleep(random.uniform(3, 7))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
