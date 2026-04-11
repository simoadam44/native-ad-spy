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

# ✅ تنظيف الروابط وتوسيع قائمة الأهداف لضمان نتائج أفضل
MGID_TARGETS = [url.strip() for url in [
    "https://pjmedia.com/vodkapundit/2026/03/23/are-you-ready-for-the-dems-2028-presidential-childhood-trauma-olympics-n4950953",
    "https://www.ibtimes.com/us-secured-secret-deal-cameroon-deport-migrants-using-aid-leverage-report-3800110",
    "https://brainberries.co/interesting/britney-spears-then-vs-now-her-changing-face-in-photos/",
    "https://herbeauty.co/ar/altarfih/maqati-video-raqs-zouk-lan-tastatia-at-tawaqquf-an-mushahadatiha-miraran-wa-takraran/",
    "https://buzzday.info/2026/02/13/what-happens-if-you-consume-ginger-every-day/?utm_id=57223822&utm_medium=cpc&utm_source=mgid.com&utm_campaign=buzzday_prt_en_mob&utm_term=57223822&utm_content=22902986",
    "https://zestradar.com/celebrities/the-worst-beckham-family-rumors-theyll-never-outrun/"
]]

async def save_to_supabase(ad):
    try:
        title_key = ad['title'].strip()[:80].lower()
        clean_url = ad['landing'].split('?')[0]
        
        # البحث عن إعلان بنفس العنوان (لأن روابط MGID تتغير باستمرار)
        # نستخدم عنوان مشابه بنسبة كبيرة
        res = supabase.table("ads").select("id, impressions, landing, title").ilike("title", title_key + "%").execute()
        
        if res.data:
            existing = res.data[0]
            new_imp = (existing.get('impressions') or 1) + 1
            update_data = {"impressions": new_imp, "last_seen": "now()"}
            
            # إذا كان الرابط القديم تتبع والجديد حقيقي، نحدث الرابط
            is_old_tracking = "mgid.com" in existing['landing'] or "adskeeper.com" in existing['landing']
            is_new_real = "mgid.com" not in clean_url and "adskeeper.com" not in clean_url and "ploynest" not in clean_url
            
            if is_old_tracking and is_new_real:
                update_data["landing"] = clean_url
                print(f"🔄 [MGID]: تم تحديث رابط تتبع برابط حقيقي للإعلان: {title_key[:30]}...")
            
            supabase.table("ads").update(update_data).eq("id", existing['id']).execute()
            print(f"[MGID] [{TARGET_COUNTRY}]: تحديث ({new_imp}): {ad['title'][:40]}...")
        else:
            ad.update({"landing": clean_url, "impressions": 1, "last_seen": "now()", "country_code": TARGET_COUNTRY})
            supabase.table("ads").insert(ad).execute()
            print(f"[MGID] [{TARGET_COUNTRY}]: صيد جديد: {ad['title'][:40]}...")
    except Exception as e:
        print(f"[DB ERROR]: {e}")

async def scrape_mgid(browser, url):
    mgid_ads = []
    # ✅ استخدام المتصفح الحقيقي للتهرب من الحظر (CDP)
    if browser.contexts:
        context = browser.contexts[0]
    else:
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            locale=GEO["locale"],
            timezone_id=GEO["timezone_id"],
            permissions=["geolocation"]
        )
    
    page = await context.new_page()
    
    # ✅ وظيفة لفك تشفير روابط التتبع مباشرة من Crawler
    async def resolve_mgid_link(tracking_url, referer):
        if not tracking_url or not ("mgid.com" in tracking_url or "adskeeper.com" in tracking_url):
            return tracking_url
        
        resolver_page = None
        try:
            resolver_page = await context.new_page()
            # تعيين referer ضروري لتجاوز "Bad Request"
            await resolver_page.set_extra_http_headers({"Referer": referer})
            
            # الانتقال للرابط وانتظار أول تحويل ناجح
            # print(f"DEBUG: Resolving tracking URL: {tracking_url}")
            await resolver_page.goto(tracking_url, wait_until="commit", timeout=15000)
            
            # ننتظر حتى يتغير العنوان عن نطاق MGID
            max_wait = 12
            wait_step = 1.0
            elapsed = 0
            while elapsed < max_wait:
                await asyncio.sleep(wait_step)
                elapsed += wait_step
                final_url = resolver_page.url
                
                # تخطي النطاقات الوهمية أو المروجة لـ MGID
                if any(x in final_url.lower() for x in ["mgid.com", "adskeeper.com", "ploynest.com", "bot-detected"]):
                    continue
                
                if final_url.startswith("http") and len(final_url) > 20:
                    return final_url
            
            return tracking_url # إذا فشلنا نعود للرابط الأصلي وليس ploynest
        except:
            return tracking_url
        finally:
            if resolver_page: await resolver_page.close()

    # 🚫 خطة الحظر العنيفة جداً (Zero-Trust) لتوفير الباندويث 
    async def block_resources(route):
        req = route.request
        res_type = req.resource_type
        r_url = req.url.lower()

        if res_type in ["image", "media", "font", "stylesheet", "websocket", "manifest", "other"]:
            await route.abort()
            return

        blocked_domains = [
            "google-analytics", "googletagmanager", "facebook", "twitter", "tiktok", "snapchat", "pinterest",
            "chartbeat", "btloader", "surveygizmo", "scorecardresearch", "hotjar",
            "criteo", "amazon", "rubicon", "openx", "pubmatic", "quantserve", "adroll",
            "mediavoice", "teads", "clarity", "doubleclick", "outbrain", "taboola", "revcontent"
        ]
        
        if any(kw in r_url for kw in blocked_domains) and "mgid.com" not in r_url and "adskeeper.com" not in r_url:
            await route.abort()
            return

        if res_type in ["script", "fetch", "xhr"]:
            if "mgid.com" in r_url or "adskeeper.com" in r_url:
                await route.continue_()
                return
            if any(sub in r_url for sub in ["static.", "assets.", "cdn.", "player.", "video.", "api."]):
                await route.abort()
                return

        await route.continue_()

    await page.route("**/*", block_resources)
    await Stealth().apply_stealth_async(page)

    # اعتراض استجابات الـ API - نستخرج الرابط الحقيقي مباشرة من JSON
    api_debug_done = False
    async def handle_response(response):
        nonlocal mgid_ads, api_debug_done
        url_lower = response.url.lower()
        if "mgid.com" in url_lower and response.status == 200:
            try:
                data = await response.json()
                if isinstance(data, dict):
                    items = data.get('items') or data.get('data') or data.get('ads') or data.get('content') or []
                elif isinstance(data, list):
                    items = data
                else:
                    items = []
                
                for item in items:
                    if not isinstance(item, dict): continue
                    if not (item.get('title') or item.get('text')): continue
                    
                    # الأولوية للروابط الحقيقية (بدون tracking)
                    real_url = (
                        item.get('articleUrl') or
                        item.get('targetUrl') or
                        item.get('destinationUrl') or
                        item.get('originalUrl') or
                        item.get('url') or
                        item.get('clickUrl') or
                        item.get('landing') or
                        item.get('link', '')
                    )
                    
                    mgid_ads.append({
                        "title": (item.get('title') or item.get('text', '')).strip(),
                        "landing": real_url,
                        "image": item.get('mainImage') or item.get('thumbnail') or item.get('image', ''),
                        "source": url,
                        "network": "MGID"
                    })
            except: pass

    page.on("response", handle_response)

    try:
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception as timeout_error:
            print(f"[MGID]: Timeout on page load, but continuing extraction... ({timeout_error})")
        
        await asyncio.sleep(8)
        for i in range(5):
            await page.evaluate(f"window.scrollBy(0, {800 + (i * 200)})")
            await asyncio.sleep(1)

        # ✅ استخراج من JS Objects
        try:
            js_ads = await page.evaluate("""
                () => {
                    let results = [];
                    try {
                        for (let key of Object.keys(window)) {
                            if (!key.toLowerCase().includes('mgid') && !key.toLowerCase().includes('widget')) continue;
                            let obj = window[key];
                            if (!obj || typeof obj !== 'object') continue;
                            let items = obj.items || obj.ads || obj.data || obj.content || [];
                            if (!Array.isArray(items)) continue;
                            for (let item of items) {
                                if (!item || !item.title) continue;
                                let realUrl = item.articleUrl || item.targetUrl || item.destinationUrl ||
                                              item.originalUrl || item.url || item.clickUrl || item.link || '';
                                results.push({
                                    title: item.title,
                                    landing: realUrl,
                                    image: item.mainImage || item.thumbnail || item.image || ''
                                });
                            }
                        }
                    } catch(e) {}
                    return results;
                }
            """)
            if js_ads:
                for ad in js_ads:
                    mgid_ads.append({**ad, "source": url, "network": "MGID"})
        except: pass

        # ✅ DOM Fallback
        if not mgid_ads:
            for frame in page.frames:
                try:
                    links = frame.locator('.mgline a, .mgbox a, [id^="mgid_"] a, .mgid-widget a, .mg-teaser a')
                    count = await links.count()
                    for i in range(count):
                        el = links.nth(i)
                        title = await el.inner_text()
                        href = await el.get_attribute("href")
                        if title and href:
                            title = title.strip()
                            if len(title) > 5 and href.startswith('http'):
                                real_href = await el.evaluate("""
                                    (a) => {
                                        let realUrl = a.dataset.url || a.dataset.href || a.dataset.link ||
                                                      a.dataset.articleUrl || a.dataset.targetUrl ||
                                                      a.getAttribute('data-url') || a.getAttribute('data-href') ||
                                                      a.getAttribute('data-link') || a.getAttribute('data-article-url') ||
                                                      a.getAttribute('data-original-url');
                                        if (realUrl && !realUrl.includes('clck.mgid.com') && !realUrl.includes('clck.adskeeper.com')) {
                                            return realUrl;
                                        }
                                        let parent = a.closest('[data-url],[data-href],[data-article-url]');
                                        if (parent) {
                                            let pUrl = parent.dataset.url || parent.dataset.href || parent.dataset.articleUrl;
                                            if (pUrl && !pUrl.includes('clck.mgid.com')) return pUrl;
                                        }
                                        return a.href;
                                    }
                                """)
                                landing = real_href or href
                                image_url = await el.evaluate("""
                                    (a) => {
                                        let img = a.querySelector('img');
                                        if (img && (img.src || img.dataset.src)) return img.src || img.dataset.src;
                                        let container = a.closest('.mgline, .mgbox, .mgid-widget, .mg-teaser, [id^="mgid_"]');
                                        if (!container) container = a.parentElement;
                                        let cImg = container.querySelector('img');
                                        if (cImg && (cImg.src || cImg.dataset.src)) return cImg.src || cImg.dataset.src;
                                        return '';
                                    }
                                """)
                                mgid_ads.append({"title": title, "landing": landing, "image": image_url or "", "source": url, "network": "MGID"})
                except: pass

        # --- معالجة وحفظ النتائج ---
        unique_ads = {}
        if mgid_ads:
            # 1. المرحلة الأولى: تصفية أولية حسب العنوان
            for ad in mgid_ads:
                title = (ad.get('title') or '').strip()
                landing = (ad.get('landing') or '').strip()
                if not title or not landing: continue
                
                title_key = title.lower()[:80]
                if title_key not in unique_ads:
                    unique_ads[title_key] = ad
                elif ad.get('image') and not unique_ads[title_key].get('image'):
                    unique_ads[title_key] = ad
                elif "clck.mgid.com" in unique_ads[title_key]['landing'] and "clck.mgid.com" not in landing:
                    unique_ads[title_key] = ad

            # 2. المرحلة الثانية: فك تشفير روابط التتبع
            print(f"🔍 [MGID]: تم رصد {len(unique_ads)} إعلان، جاري فك روابط التتبع...")
            resolved_count = 0
            for ad in unique_ads.values():
                if "clck.mgid.com" in ad['landing'] or "clck.adskeeper.com" in ad['landing']:
                    resolved_url = await resolve_mgid_link(ad['landing'], url)
                    if resolved_url != ad['landing']:
                        ad['landing'] = resolved_url
                        resolved_count += 1
            
            if resolved_count > 0:
                print(f"🔓 [MGID]: تم فك تشفير {resolved_count} رابط بنجاح!")

            # 3. الحفظ النهائي
            for ad in unique_ads.values():
                await save_to_supabase(ad)
            print(f"✅ [MGID]: اكتملت المعالجة لـ {len(unique_ads)} إعلان في {url}")
        else:
            print(f"ℹ️ [MGID]: لم يتم رصد إعلانات في {url}")

    except Exception as e:
        print(f"[MGID ERROR]: {e}")
    finally:
        await page.close()

async def run():
    async with async_playwright() as p:
        try:
            print(f"Launching independent Chrome browser with proxy for {TARGET_COUNTRY}...")
            browser = await p.chromium.launch(
                headless=True, 
                proxy=PROXY_CONFIG,
                args=[
                    "--blink-settings=imagesEnabled=false",
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-background-networking",
                    "--disable-dev-shm-usage",
                    "--no-sandbox"
                ]
            )
            
            # محاولة استخدام سياق واحد لتوفير الموارد
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                locale=GEO["locale"],
                timezone_id=GEO["timezone_id"],
                permissions=["geolocation"]
            )
            
            for target in MGID_TARGETS:
                print(f"Checking target: {target}")
                await scrape_mgid(browser, target)
                await asyncio.sleep(random.uniform(3, 7))
                
        except Exception as e:
            print(f"Error: {e}")
        finally:
            if 'browser' in locals():
                await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
