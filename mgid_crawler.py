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

async def resolve_mgid_redirect(url: str) -> str:
    """حل رابط التتبع من MGID - يتبع كل الـ redirects"""
    if not url or not isinstance(url, str):
        return url
    
    if 'clck.mgid.com' not in url and 'clck.adskeeper.com' not in url:
        return url
    
    # قائمة المواقع الإعلانية التي يجب تخطيها
    ad_domains = ['ploynest.com', 'adskeeper.com', 'mgid.com', 'doubleclick', 'googleadservices', 'clck.mgid.com']
    
    browser = None
    try:
        async with async_playwright() as p:
            browser = await p.chromium.launch(headless=True)
            page = await browser.new_page()
            
            await page.goto(url, wait_until="domcontentloaded", timeout=20000)
            
            # تابع الـ redirects حتى نصل لموقع غير إعلاني
            max_iterations = 15
            for i in range(max_iterations):
                await asyncio.sleep(2)
                current_url = page.url
                
                # تحقق إذا كان الموقع الحالي هو موقع إعلاني
                is_ad = any(ad in current_url.lower() for ad in ad_domains)
                
                if not is_ad:
                    # وصلنا لموقع حقيقي - توقف
                    break
                
                # إذا لا زلنا في موقع إعلاني، حاول التفاعل
                try:
                    # 1. انتظر وتحقق من redirect تلقائي
                    await asyncio.sleep(3)
                    
                    # 2. جرب النقر على أي رابط
                    links = await page.query_selector_all('a[href]')
                    for link in links:
                        href = await link.get_attribute('href')
                        if href and not any(ad in href.lower() for ad in ad_domains):
                            await link.click()
                            await asyncio.sleep(3)
                            break
                    
                    # 3. جرب meta refresh
                    meta_url = await page.evaluate('''() => {
                        const meta = document.querySelector('meta[http-equiv="refresh"]');
                        if (meta) {
                            const content = meta.getAttribute('content');
                            if (content && content.toLowerCase().includes('url=')) {
                                return content.split('url=')[1].split(';')[0].trim();
                            }
                        }
                        return null;
                    }''')
                    if meta_url:
                        if meta_url.startswith('http'):
                            await page.goto(meta_url, timeout=10000)
                        else:
                            await page.goto('https://' + meta_url, timeout=10000)
                        await asyncio.sleep(2)
                        
                    # 4. جرب JavaScript redirects
                    js_redirect = await page.evaluate('''() => {
                        if (window.location.href && window.location.href !== document.location.href) {
                            return window.location.href;
                        }
                        return null;
                    }''')
                    if js_redirect and 'ad' not in js_redirect.lower():
                        await page.goto(js_redirect, timeout=10000)
                        
                except: pass
            
            final_url = page.url
            print(f"    🔗 حل الرابط: {url[:40]}... → {final_url[:50]}...")
            await browser.close()
            return final_url
            
    except Exception as e:
        print(f"    ⚠️ فشل في حل الرابط: {url[:30]}... - {str(e)[:50]}")
    finally:
        if browser:
            await browser.close()
    
    return url

async def resolve_mgid_redirect_batch(urls: list) -> dict:
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
        
        # ✅ استخدام العنوان + الصورة كمعرف فريد بدلاً من الرابط فقط
        # هذا يمنع تكرار الإعلانات التي لها نفس الرابط النهائي
        title_key = (ad.get('title') or '').strip()[:80].lower()
        image_key = (ad.get('image') or '').strip()
        
        # البحث عن إعلان بنفس العنوان والصورة
        res = supabase.table("ads").select("id, impressions").eq("title", ad['title']).execute()
        
        if res.data:
            # تحقق إذا كانت الصورة مختلفة
            existing_ad = res.data[0]
            if existing_ad:
                new_imp = (existing_ad.get('impressions') or 1) + 1
                supabase.table("ads").update({
                    "impressions": new_imp, 
                    "last_seen": "now()", 
                    "country_code": TARGET_COUNTRY,
                    "landing": clean_url  # تحديث الرابط حتى لو نفس العنوان
                }).eq("id", existing_ad['id']).execute()
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
            
            # حذف التكرارات حسب العنوان (العنوان كمعرف فريد)
            unique_ads = {}
            for ad in mgid_ads:
                title_key = (ad.get('title') or '').strip()[:80].lower()
                if title_key and title_key not in unique_ads:
                    unique_ads[title_key] = ad
                # إذا نفس العنوان لكن صورة مختلفة، احتفظ بالإعلان الجديد
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