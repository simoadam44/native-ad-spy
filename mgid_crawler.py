import asyncio, os, random, sys, re
sys.stdout.reconfigure(encoding='utf-8')
import aiohttp
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

# إعداد الدولة والبروكسي (DataImpulse)
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

MGID_TARGETS = [
    "https://pjmedia.com/vodkapundit/2026/03/23/are-you-ready-for-the-dems-2028-presidential-childhood-trauma-olympics-n4950953",
    "https://www.ibtimes.com/us-secured-secret-deal-cameroon-deport-migrants-using-aid-leverage-report-3800110",
    "https://brainberries.co/interesting/britney-spears-then-vs-now-her-changing-face-in-photos/",
    "https://herbeauty.co/ar/altarfih/maqati-video-raqs-zouk-lan-tastatia-at-tawaqquf-an-mushahadatiha-miraran-wa-takraran/",
    "https://buzzday.info/2026/02/13/what-happens-if-you-consume-ginger-every-day/",
    "https://zestradar.com/celebrities/the-worst-beckham-family-rumors-theyll-never-outrun/"
]

# ✅ دالة جديدة لحل رابط التتبع والحصول على الرابط الحقيقي
async def resolve_mgid_redirect(url: str, session: aiohttp.ClientSession = None) -> str:
    """حل رابط التتبع من MGID للحصول على الرابط النهائي"""
    if not url or not isinstance(url, str):
        return url
    
    # إذا كان الرابط ليس من MGID跟踪-link، أعده كما هو
    if 'clck.mgid.com' not in url and 'clck.adskeeper.com' not in url:
        return url
    
    try:
        # استخدام aiohttp المتزامن لحل الـ redirect
        async with aiohttp.ClientSession() as client:
            async with client.head(url, allow_redirects=True, timeout=aiohttp.ClientTimeout(total=10)) as resp:
                final_url = str(resp.url)
                print(f"    🔗 تم حل الرابط: {url[:50]}... → {final_url[:50]}...")
                return final_url
    except Exception as e:
        print(f"    ⚠️ فشل في حل الرابط: {url[:30]}... - {str(e)[:50]}")
        return url

async def resolve_mgid_redirect_batch(urls: list) -> list:
    """حل مجموعة من روابط التتبع بشكل متوازي"""
    resolved = {}
    tasks = [resolve_mgid_redirect(url) for url in urls if url]
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
        
        # ✅ حل رابط التتبع قبل الحفظ
        landing = ad['landing']
        if 'clck.mgid.com' in landing or 'clck.adskeeper.com' in landing:
            landing = await resolve_mgid_redirect(landing)
        
        # تنظيف الرابط
        clean_url = landing.split('?')[0].split('#')[0]
        ad['landing'] = clean_url
        
        res = supabase.table("ads").select("id, impressions").eq("landing", clean_url).execute()
        
        if res.data:
            new_imp = (res.data[0].get('impressions') or 1) + 1
            supabase.table("ads").update({
                "impressions": new_imp, 
                "last_seen": "now()", 
                "country_code": TARGET_COUNTRY
            }).eq("id", res.data[0]['id']).execute()
            print(f"  📈 [MGID] [{TARGET_COUNTRY}]: تحديث ({new_imp}): {ad['title'][:40]}...")
        else:
            ad.update({"impressions": 1, "last_seen": "now()", "country_code": TARGET_COUNTRY})
            supabase.table("ads").insert(ad).execute()
            print(f"  ✨ [MGID] [{TARGET_COUNTRY}]: صيد جديد: {ad['title'][:40]}...")
    except Exception as e:
        print(f"  ⚠️ [DB ERROR]: {e}")

async def scrape_mgid(browser, url):
    mgid_ads = []
    context = None
    page = None
    
    try:
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            locale=GEO["locale"],
            timezone_id=GEO["timezone_id"],
        )
        page = await context.new_page()
        
        # 🚫 حظر الموارد غير الضرورية
        async def block_resources(route):
            req = route.request
            res_type = req.resource_type
            url_lower = req.url.lower()
            
            if res_type in ["image", "media", "font", "stylesheet"]:
                await route.abort()
                return
            
            blocked = ["google-analytics", "googletagmanager", "facebook", "twitter", "doubleclick"]
            if any(kw in url_lower for kw in blocked):
                await route.abort()
                return
            
            await route.continue_()
        
        await page.route("**/*", block_resources)
        await Stealth().apply_stealth_async(page)
        
        # اعتراض استجابات API
        async def handle_response(response):
            nonlocal mgid_ads
            url_lower = response.url.lower()
            if "mgid.com" in url_lower and response.status == 200:
                try:
                    data = await response.json()
                    items = data.get('items') or data.get('data') or []
                    for item in items:
                        if not isinstance(item, dict): continue
                        
                        title = item.get('title') or item.get('text', '')
                        if not title: continue
                        
                        # ✅ البحث عن الرابط الحقيقي في كل الحقول الممكنة
                        real_url = (
                            item.get('articleUrl') or
                            item.get('targetUrl') or
                            item.get('destinationUrl') or
                            item.get('originalUrl') or
                            item.get('url') or
                            item.get('clickUrl') or
                            item.get('link', '')
                        )
                        
                        if real_url:
                            mgid_ads.append({
                                "title": title.strip(),
                                "landing": real_url,
                                "image": item.get('mainImage') or item.get('thumbnail') or '',
                                "source": url,
                                "network": "MGID"
                            })
                except: pass
        
        page.on("response", handle_response)
        
        print(f"🚀 [MGID]: فحص {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        
        # تمرير الصفحة
        for i in range(5):
            await page.evaluate(f"window.scrollBy(0, {800 + i*200})")
            await asyncio.sleep(0.5)
        await asyncio.sleep(3)
        
        # استخراج من DOM إذا لم نجد إعلانات من API
        if not mgid_ads:
            try:
                js_data = await page.evaluate("""
                    () => {
                        let results = [];
                        // البحث في window objects
                        for (let key in window) {
                            try {
                                let val = window[key];
                                if (val && val.items && Array.isArray(val.items)) {
                                    for (let item of val.items) {
                                        if (item.title) {
                                            // البحث عن الرابط الحقيقي
                                            let realUrl = item.articleUrl || item.targetUrl || item.destinationUrl || 
                                                          item.originalUrl || item.url || item.clickUrl || item.link || '';
                                            results.push({
                                                title: item.title,
                                                landing: realUrl || '',
                                                image: item.mainImage || item.thumbnail || item.image || ''
                                            });
                                        }
                                    }
                                }
                            } catch(e) {}
                        }
                        return results;
                    }
                """)
                if js_data:
                    mgid_ads.extend(js_data)
            except: pass
        
        # استخراج من DOM مباشرة كـ fallback
        if not mgid_ads:
            try:
                links = await page.locator('a[href*="mgid.com"], a[href*="clck.mgid.com"]').all()
                for link in links:
                    try:
                        href = await link.get_attribute('href')
                        text = await link.inner_text()
                        if text and len(text.strip()) > 5:
                            # البحث في data attributes
                            data_url = await link.evaluate('''a => {
                                return a.dataset.url || a.dataset.articleUrl || a.dataset.targetUrl || a.dataset.href || a.href;
                            }''')
                            
                            # استخدام الرابط الحقيقي إذا وجد
                            final_url = data_url if data_url and 'clck.mgid.com' not in data_url else href
                            
                            mgid_ads.append({
                                "title": text.strip()[:200],
                                "landing": final_url or href,
                                "image": "",
                                "source": url,
                                "network": "MGID"
                            })
                    except: continue
            except: pass
        
        # معالجة النتائج - حل روابط التتبع
        if mgid_ads:
            print(f"  📊 تم استخراج {len(mgid_ads)} إعلان، جاري حل الروابط...")
            
            # استخراج الروابط التي تحتاج حل
            urls_to_resolve = {}
            for ad in mgid_ads:
                landing = ad.get('landing', '')
                if 'clck.mgid.com' in landing or 'clck.adskeeper.com' in landing:
                    urls_to_resolve[landing] = ad
            
            # حل الروابط بشكل متوازي
            if urls_to_resolve:
                resolved = await resolve_mgid_redirect_batch(list(urls_to_resolve.keys()))
                for old_url, ad in urls_to_resolve.items():
                    ad['landing'] = resolved.get(old_url, old_url)
            
            # حذف التكرارات حسب العنوان
            unique_ads = {}
            for ad in mgid_ads:
                title_key = (ad.get('title') or '').strip()[:80].lower()
                if title_key and title_key not in unique_ads:
                    unique_ads[title_key] = ad
                elif title_key in unique_ads and ad.get('image') and not unique_ads[title_key].get('image'):
                    unique_ads[title_key] = ad
            
            # حفظ كل إعلان
            for ad in unique_ads.values():
                await save_to_supabase(ad)
            
            print(f"  ✅ تم حفظ {len(unique_ads)} إعلان من {url}")
        else:
            print(f"  ℹ️ لم يتم رصد إعلانات في {url}")
            
    except Exception as e:
        print(f"  ⚠️ [MGID ERROR]: {e}")
    finally:
        if page: await page.close()
        if context: await context.close()

async def run():
    async with async_playwright() as p:
        try:
            print(f"🚀 تشغيل المتصفح مع البروكسي لـ {TARGET_COUNTRY}...")
            browser = await p.chromium.launch(
                headless=True, 
                proxy=PROXY_CONFIG,
                args=["--disable-blink-features=AutomationControlled", "--no-sandbox"]
            )
            
            for target in MGID_TARGETS:
                await scrape_mgid(browser, target)
                await asyncio.sleep(random.uniform(3, 7))
            
            await browser.close()
        except Exception as e:
            print(f"Error: {e}")

if __name__ == "__main__":
    asyncio.run(run())