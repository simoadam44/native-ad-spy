import asyncio, os, random, sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from supabase import create_client
import json
import re

# إعداد سوبابيز
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# إعداد الدولة والبروكسي المتطور
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
    "https://www.standard.co.uk/news/world/search-missing-us-airman-downed-f15-fighter-jet-b1277661.html", 
    "https://sabq.org",         
    "https://edition.cnn.com/2026/04/02/europe/us-france-trump-macron-latam-intl",
    "https://www.standard.co.uk/news/world/search-missing-us-airman-downed-f15-fighter-jet-b1277661.html",
    "https://www.independent.co.uk/news/uk/crime/knife-crime-schools-attacks-harvey-willgoose-b2949295.html"
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
                let distance = 350;
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
    await asyncio.sleep(10)

async def scrape_outbrain(browser, url):
    outbrain_ads = []
    context = None
    page = None
    try:
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            locale=GEO["locale"],
            timezone_id=GEO["timezone_id"],
            permissions=["geolocation"]
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        # 🚫 خطة الحظر العنيفة جداً (Zero-Trust) لتوفير الباندويث 
        async def block_resources(route):
            req = route.request
            res_type = req.resource_type
            url_low = req.url.lower()

            # حظر صارم لكل ما هو غير ضروري للسحب (بما في ذلك الـ CSS والخطوط)
            if res_type in ["image", "media", "font", "stylesheet", "websocket", "manifest", "other"]:
                await route.abort()
                return
            
            # قائمة المحظورات المعروفة (Trackers)
            blocked_domains = [
                "google-analytics", "googletagmanager", "facebook.com", "twitter.com", "tiktok.com",
                "doubleclick", "scorecardresearch", "hotjar", "chartbeat", "quantserve",
                "mgid.com", "taboola.com", "revcontent.com"
            ]
            if any(kw in url_low for kw in blocked_domains) and "outbrain.com" not in url_low:
                await route.abort()
                return
                
            if res_type in ["script", "fetch", "xhr"]:
                # السماح لـ Outbrain فقط
                if "outbrain.com" in url_low:
                    await route.continue_()
                    return
                # حظر سكريبتات المواقع والـ CDNs الخارجية لتوفير البيانات
                if any(sub in url_low for sub in ["static.", "assets.", "cdn.", "player.", "video.", "api."]):
                    await route.abort()
                    return

            await route.continue_()

        await page.route("**/*", block_resources)

        async def handle_response(response):
            nonlocal outbrain_ads
            r_url = response.url.lower()
            if ("outbrain.com" in r_url or "odb.outbrain.com" in r_url) and response.status == 200:
                try:
                    ct = response.headers.get("content-type", "")
                    if "application/json" in ct or "text/javascript" in ct:
                        text = await response.text()
                        data = None
                        if text.strip().startswith('{') or text.strip().startswith('['):
                            data = json.loads(text)
                        else:
                            match = re.search(r'(\{.*\})|(\[.*\])', text)
                            if match: data = json.loads(match.group(0))
                        
                        if data:
                            listings = []
                            # Outbrain uses various formats like 'documents', 'doc', 'ads', 'items'
                            possible_keys = ['documents', 'items', 'cards', 'ads', 'listings']
                            if isinstance(data, dict):
                                for key in possible_keys:
                                    if key in data:
                                        listings.extend(data[key])
                                if 'doc' in data and isinstance(data['doc'], dict):
                                    for key in possible_keys:
                                        if key in data['doc']:
                                            listings.extend(data['doc'][key])
                            elif isinstance(data, list):
                                listings = data
                            
                            for item in listings:
                                t = item.get('content') or item.get('title') or item.get('text') or item.get('name')
                                l = item.get('url') or item.get('clickUrl') or item.get('link') or item.get('href')
                                if t and l:
                                    # Normalize image extraction
                                    img = ""
                                    if isinstance(item.get('image'), dict):
                                        img = item['image'].get('url') or ""
                                    elif isinstance(item.get('thumbnail'), dict):
                                        img = item['thumbnail'].get('url') or ""
                                    elif isinstance(item.get('thumbnail'), list) and len(item['thumbnail']) > 0:
                                        img = item['thumbnail'][0].get('url') or ""
                                    else:
                                        img = item.get('image') or item.get('thumbnail') or ""
                                    
                                    outbrain_ads.append({
                                        "title": str(t).strip(), 
                                        "landing": l, 
                                        "image": img, 
                                        "source": url, 
                                        "network": "OUTBRAIN"
                                    })
                except: pass

        page.on("response", handle_response)
        
        print(f"🚀 [OUTBRAIN]: فحص الهدف: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await smart_scroll_and_wait(page)
        
        # استخراج من DOM لجميع الإطارات (بإستخدام محددات أكثر شمولاً)
        for frame in page.frames:
            try:
                dom_ads = await frame.evaluate("""
                    () => {
                        let found = [];
                        let selectors = [
                            'a[data-ob-url]', 
                            '.ob-dynamic-rec-container a', 
                            '.ob-widget-items-container a', 
                            '.OUTBRAIN a', 
                            '[id*="outbrain"] a',
                            '.ob-rec-text-view',
                            '.ob-unit a',
                            '.ob-widget-item a'
                        ];
                        
                        document.querySelectorAll(selectors.join(',')).forEach(el => {
                            let link = el.tagName === 'A' ? el : el.closest('a');
                            if (!link) return;
                            
                            let title_el = el.querySelector('.ob-rec-text') || el.querySelector('.ob-rec-title') || el;
                            let title = title_el.innerText.trim();
                            let href = link.getAttribute('data-ob-url') || link.href;
                            
                            let img_el = link.querySelector('img') || link.parentElement.querySelector('img');
                            let src = img_el ? (img_el.dataset.src || img_el.getAttribute('data-src') || img_el.src) : '';
                            
                            if (title.length > 10 && href && href.startsWith('http')) {
                                found.push({title, landing: href, image: src});
                            }
                        });
                        return found;
                    }
                """)
                for ad in dom_ads: 
                    if ad['title'] and ad['landing']:
                        outbrain_ads.append({**ad, "source": url, "network": "OUTBRAIN"})
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
        if page: await page.close()
        if context: await context.close()

async def run():
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
        for target in OUTBRAIN_TARGETS:
            try: await scrape_outbrain(browser, target)
            except: pass
            await asyncio.sleep(random.uniform(3, 7))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
