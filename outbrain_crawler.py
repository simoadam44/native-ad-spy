import asyncio, os, random, sys
sys.stdout.reconfigure(encoding='utf-8')
import aiohttp
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from supabase import create_client
import json
import re

# إعداد سوبابيز
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# إعداد الدولة والبروكسي
TARGET_COUNTRY = os.environ.get("TARGET_COUNTRY", "US")

PROXY_CONFIG = {
    "server": "http://gw.dataimpulse.com:823",
    "username": f"85ccde32f1cc6c7ad458__country-{TARGET_COUNTRY}",
    "password": "78c188c405598b8a"
}

COUNTRY_CONFIGS = {
    "US": {"locale": "en-US", "timezone_id": "America/New_York"},
    "GB": {"locale": "en-GB", "timezone_id": "Europe/London"},
    "SA": {"locale": "ar-SA", "timezone_id": "Asia/Riyadh"},
    "AE": {"locale": "ar-AE", "timezone_id": "Asia/Dubai"},
    "EG": {"locale": "ar-EG", "timezone_id": "Africa/Cairo"},
}
GEO = COUNTRY_CONFIGS.get(TARGET_COUNTRY, COUNTRY_CONFIGS["US"])

OUTBRAIN_TARGETS = [
    "https://www.standard.co.uk/news/world/search-missing-us-airman-downed-f15-fighter-jet-b1277661.html", 
    "https://sabq.org",         
    "https://edition.cnn.com/2026/04/02/europe/us-france-trump-macron-latam-intl",
    "https://www.independent.co.uk/news/uk/crime/knife-crime-schools-attacks-harvey-willgoose-b2949295.html"
]

# ✅ دالة حل روابط التتبع
async def resolve_outbrain_redirect(url: str) -> str:
    """حل روابط التتبع من Outbrain"""
    if not url or not isinstance(url, str):
        return url
    
    if 'outbrain.com' not in url.lower() and '&dicbo=' not in url:
        return url
    
    try:
        async with aiohttp.ClientSession() as client:
            async with client.head(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                final_url = str(resp.url)
                print(f"    🔗 حل رابط Outbrain: {url[:40]}... → {final_url[:40]}...")
                return final_url
    except Exception as e:
        return url

async def resolve_outbrain_batch(urls: list) -> dict:
    """حل مجموعة من روابط Outbrain"""
    resolved = {}
    tasks = [resolve_outbrain_redirect(url) for url in urls if url]
    results = await asyncio.gather(*tasks, return_exceptions=True)
    
    for url, result in zip(urls, results):
        if isinstance(result, Exception):
            resolved[url] = url
        else:
            resolved[url] = result
    
    return resolved

async def save_to_supabase(ad):
    try:
        if not ad.get('title') or not ad.get('landing'): return
        
        landing = ad['landing']
        
        # ✅ حل رابط التتبع (Outbrain uses &dicbo= parameter)
        if 'outbrain.com' in landing.lower() or '&dicbo=' in landing:
            landing = await resolve_outbrain_redirect(landing)
        
        # تنظيف الرابط من parameters التتبع
        clean_url = landing.split('&dicbo=')[0] if '&dicbo=' in landing else landing.split('?')[0]
        clean_url = clean_url.split('#')[0]
        
        ad['landing'] = clean_url
        
        res = supabase.table("ads").select("id, impressions").eq("landing", clean_url).execute()
        
        if res.data:
            new_imp = (res.data[0].get('impressions') or 1) + 1
            supabase.table("ads").update({
                "impressions": new_imp, 
                "last_seen": "now()", 
                "country_code": TARGET_COUNTRY
            }).eq("id", res.data[0]['id']).execute()
            print(f"  📈 [OUTBRAIN] [{TARGET_COUNTRY}]: تحديث ({new_imp}): {ad['title'][:40]}...")
        else:
            ad.update({"impressions": 1, "last_seen": "now()", "country_code": TARGET_COUNTRY})
            supabase.table("ads").insert(ad).execute()
            print(f"  ✨ [OUTBRAIN] [{TARGET_COUNTRY}]: صيد جديد: {ad['title'][:40]}...")
    except Exception as e:
        print(f"  ⚠️ [DB ERROR]: {e}")

async def scrape_outbrain(browser, url):
    outbrain_ads = []
    context = None
    page = None
    try:
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            locale=GEO["locale"],
            timezone_id=GEO["timezone_id"],
        )
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        async def block_resources(route):
            req = route.request
            res_type = req.resource_type
            url_low = req.url.lower()
            
            if res_type in ["image", "media", "font", "stylesheet"]:
                await route.abort()
                return
            
            blocked = ["google-analytics", "googletagmanager", "facebook", "twitter", "doubleclick", "mgid.com", "taboola.com", "revcontent.com"]
            if any(kw in url_low for kw in blocked):
                await route.abort()
                return
            
            await route.continue_()
        
        await page.route("**/*", block_resources)
        
        # اعتراض الاستجابات
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
                                    img = ""
                                    if isinstance(item.get('image'), dict):
                                        img = item['image'].get('url') or ""
                                    elif isinstance(item.get('thumbnail'), dict):
                                        img = item['thumbnail'].get('url') or ""
                                    elif isinstance(item.get('thumbnail'), list) and len(item['thumbnail']) > 0:
                                        img = item['thumbnail'][0].get('url') or ""
                                    
                                    outbrain_ads.append({
                                        "title": str(t).strip(), 
                                        "landing": l, 
                                        "image": img, 
                                        "source": url, 
                                        "network": "OUTBRAIN"
                                    })
                except: pass
        
        page.on("response", handle_response)
        
        print(f"🚀 [OUTBRAIN]: فحص {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        
        # تمرير
        await page.evaluate("window.scrollBy(0, document.body.scrollHeight)")
        await asyncio.sleep(10)
        
        # استخراج من DOM
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
                            
                            let title_el = link.querySelector('.ob-rec-text') || link.querySelector('.ob-rec-title') || link;
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
        
        # معالجة النتائج
        if outbrain_ads:
            print(f"  📊 تم استخراج {len(outbrain_ads)} إعلان")
            
            # حل الروابط
            urls_to_resolve = {ad['landing']: ad for ad in outbrain_ads 
                             if 'outbrain.com' in ad.get('landing', '').lower() or '&dicbo=' in ad.get('landing', '')}
            
            if urls_to_resolve:
                resolved = await resolve_outbrain_batch(list(urls_to_resolve.keys()))
                for old_url, ad in urls_to_resolve.items():
                    ad['landing'] = resolved.get(old_url, old_url)
            
            # حذف التكرارات
            unique_ads = {}
            for ad in outbrain_ads:
                key = (ad.get('title') or '').strip()[:80].lower()
                if key and key not in unique_ads:
                    unique_ads[key] = ad
            
            for ad in unique_ads.values():
                await save_to_supabase(ad)
            
            print(f"  ✅ تم حفظ {len(unique_ads)} إعلان من {url}")
        else:
            print(f"  ℹ️ لم يتم رصد إعلانات في {url}")
            
    except Exception as e:
        print(f"  ⚠️ [OUTBRAIN ERROR]: {e}")
    finally:
        if page: await page.close()
        if context: await context.close()

async def run():
    async with async_playwright() as p:
        print(f"🚀 تشغيل Outbrain Crawler لـ {TARGET_COUNTRY}...")
        browser = await p.chromium.launch(
            headless=True, 
            proxy=PROXY_CONFIG,
            args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
        )
        for target in OUTBRAIN_TARGETS:
            try:
                await scrape_outbrain(browser, target)
            except: pass
            await asyncio.sleep(random.uniform(3, 7))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())