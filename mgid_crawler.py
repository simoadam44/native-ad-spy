import asyncio, os, random, sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from supabase import create_client
from langdetect import detect
import sys as _sys
import os as _os
_sys.path.insert(0, _os.path.dirname(__file__))
from utils.affiliate_detector import detect_affiliate_network

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
        
        # كلمات مفتاحية لعناوين غير مفيدة (أسماء مواقع أو أقسام)
        useless_titles = ["brainberries.co", "pop culture", "herbeauty.co", "easy moves", "trending", "sponsored", "advertisement"]
        if any(ut in title_key for ut in useless_titles) and len(title_key) < 20:
            return

        # البحث عن إعلان بنفس العنوان
        res = supabase.table("ads").select("id, impressions, landing, title").ilike("title", title_key + "%").execute()
        
        if res.data:
            existing = res.data[0]
            new_imp = (existing.get('impressions') or 1) + 1
            
            # كشف اللغة
            try:
                lang = detect(ad['title'])
            except:
                lang = 'en'
                
            update_data = {"impressions": new_imp, "last_seen": "now()", "language": lang}
            
            # إذا كان الرابط القديم تتبع والجديد حقيقي، نحدث الرابط
            is_old_tracking = "mgid.com" in existing['landing'] or "adskeeper.com" in existing['landing'] or "clck." in existing['landing']
            is_new_real = "mgid.com" not in clean_url and "adskeeper.com" not in clean_url and "ploynest" not in clean_url and "clck." not in clean_url
            
            if is_old_tracking and is_new_real and len(clean_url) > 25:
                update_data["landing"] = clean_url
                print(f"🔄 [MGID]: تم تحديث رابط تتبع برابط حقيقي للإعلان: {title_key[:30]}...")
            
            supabase.table("ads").update(update_data).eq("id", existing['id']).execute()
            print(f"[MGID] [{TARGET_COUNTRY}] [{lang}]: تحديث ({new_imp}): {ad['title'][:40]}...")
        else:
            # كشف اللغة للجديد
            try:
                lang = detect(ad['title'])
            except:
                lang = 'en'
            try:
                aff = detect_affiliate_network(clean_url)
            except:
                aff = {'network': 'Direct / Unknown'}
            ad.update({"landing": clean_url, "impressions": 1, "last_seen": "now()", "country_code": TARGET_COUNTRY, "language": lang, "affiliate_network": aff['network']})
            supabase.table("ads").insert(ad).execute()
            print(f"[MGID] [{TARGET_COUNTRY}] [{lang}]: صيد جديد: {ad['title'][:40]}...")
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
    
    # ✅ وظيفة متطورة لفك تشفير روابط التتبع
    async def resolve_mgid_link(tracking_url, referer):
        if not tracking_url or not ("mgid.com" in tracking_url or "adskeeper.com" in tracking_url):
            return tracking_url
        
        resolver_page = None
        try:
            # استخدام إعدادات موبايل للتخفي (أقل عرضة للحظر)
            resolver_page = await context.new_page()
            await resolver_page.set_viewport_size({"width": 390, "height": 844})
            await resolver_page.set_extra_http_headers({
                "Referer": referer,
                "Accept-Language": "en-US,en;q=0.9"
            })
            
            # متغير لحفظ الرابط النهائي من الشبكة
            network_resolved_url = None
            
            # اعتراض طلبات الشبكة للقبض على الرابط الحقيقي
            async def catch_final_url(request):
                nonlocal network_resolved_url
                r_url = request.url
                # نتجاهل روابط التتبع ونطاقات الحماية والمؤشرات التقنية
                is_tracking = any(x in r_url.lower() for x in [
                    "mgid.com", "adskeeper.com", "ploynest.com", "clck.", "ghits/", 
                    "onetrust.com", "cookieconsent", "cookielaw.org", "bot-detected",
                    "adtrafficquality.google", "googleadservices.com", "activeview", "sodar"
                ])
                is_resource = any(x in r_url.lower() for x in [".png", ".jpg", ".jpeg", ".gif", ".css", ".js", ".woff2"])
                
                if request.resource_type in ["document", "xhr", "fetch"] and not is_tracking and not is_resource:
                    if len(r_url) > 25 and r_url.startswith("http"):
                        # التأكد من أن الرابط ليس مجرد اسم وهمي بل يحتوي على نطاق صحيح
                        from urllib.parse import urlparse
                        try:
                            parsed = urlparse(r_url)
                            if parsed.netloc and "." in parsed.netloc:
                                network_resolved_url = r_url
                        except: pass

            resolver_page.on("request", catch_final_url)
            
            # الانتقال والانتظار - سنستخدم domcontentloaded لضمان تحميل السكريبتات الأولية
            try:
                await resolver_page.goto(tracking_url, wait_until="domcontentloaded", timeout=12000)
            except:
                pass # في حال حدوث timeout، قد نكون وصنا بالفعل للرابط
            
            # الانتظار حتى يتغير العنوان أو تدرك الشبكة الرابط
            # سنقوم بالتحقق لمدة 10 ثوانٍ (ثانية بثانية)
            for _ in range(10):
                if network_resolved_url: 
                    # التحقق أن الرابط ليس مجرد جزء من رابط تتبع آخر
                    if "mgid.com" not in network_resolved_url:
                        return network_resolved_url
                
                curr_url = resolver_page.url
                if curr_url and "mgid.com" not in curr_url and "adskeeper.com" not in curr_url and \
                   "ploynest.com" not in curr_url and "bot-detected" not in curr_url and \
                   "cookielaw.org" not in curr_url and "onetrust.com" not in curr_url and len(curr_url) > 25:
                    from urllib.parse import urlparse
                    try:
                        p = urlparse(curr_url)
                        if p.netloc and "." in p.netloc:
                            return curr_url
                    except: pass
                
                await asyncio.sleep(1)
            
            return tracking_url
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
                                // البحث باستخدام الـ hash (نادر ولكنه موجود في الصور)
                                let hash = item.hash || item.i || '';
                                let realUrl = item.articleUrl || item.targetUrl || item.destinationUrl ||
                                              item.originalUrl || item.url || item.clickUrl || item.link || '';
                                
                                // التحقق من صحة الرابط المجرد من الكائنات
                                if (realUrl && !realUrl.includes('clck.mgid.com')) {
                                    try {
                                        let u = new URL(realUrl, window.location.origin);
                                        if (!u.hostname.includes('.')) realUrl = '';
                                        else realUrl = u.href;
                                    } catch(e) { realUrl = ''; }
                                }

                                results.push({
                                    title: item.title,
                                    landing: realUrl,
                                    image: item.mainImage || item.thumbnail || item.image || '',
                                    hash: hash
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
        for frame in page.frames:
            try:
                links = frame.locator('.mgline a, .mgbox a, [id^="mgid_"] a, .mgid-widget a, .mg-teaser a')
                count = await links.count()
                for i in range(count):
                    el = links.nth(i)
                    title = await el.inner_text()
                    href = await el.get_attribute("href")
                    
                    # استخراج الـ hash من الخصائص
                    ad_hash = await el.evaluate("(a) => a.dataset.hash || a.dataset.i || a.getAttribute('data-hash') || a.getAttribute('data-i') || ''")
                    
                    if title and href:
                        title = title.strip()
                        if len(title) > 5 and href.startswith('http'):
                            # محاولة العثور على الرابط باستخدام الـ hash في كائنات الصفحة
                            real_href = None
                            if ad_hash:
                                # البحث في قائمة mgid_ads التي استخرجناها للتو من API أو JS
                                for api_ad in mgid_ads:
                                    if api_ad.get('hash') == ad_hash and api_ad.get('landing') and "mgid.com" not in api_ad['landing']:
                                        real_href = api_ad['landing']
                                        break
                            
                            if not real_href:
                                real_href = await el.evaluate("""
                                    (a) => {
                                        function isValid(url) {
                                            try {
                                                let u = new URL(url, window.location.origin);
                                                return u.hostname.includes('.') && 
                                                       !u.href.includes('clck.mgid.com') && 
                                                       !u.href.includes('clck.adskeeper.com');
                                            } catch(e) { return false; }
                                        }
                                        
                                        let realUrl = a.dataset.url || a.dataset.href || a.dataset.link ||
                                                      a.dataset.articleUrl || a.dataset.targetUrl ||
                                                      a.getAttribute('data-url') || a.getAttribute('data-href') ||
                                                      a.getAttribute('data-link') || a.getAttribute('data-article-url') ||
                                                      a.getAttribute('data-original-url');
                                        
                                        if (realUrl && isValid(realUrl)) {
                                            return new URL(realUrl, window.location.origin).href;
                                        }
                                        let parent = a.closest('[data-url],[data-href],[data-article-url]');
                                        if (parent) {
                                            let pUrl = parent.dataset.url || parent.dataset.href || parent.dataset.articleUrl;
                                            if (pUrl && isValid(pUrl)) {
                                                return new URL(pUrl, window.location.origin).href;
                                            }
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

            # 2. المرحلة الثانية: فك تشفير روابط التتبع السري (AdPlexity Method)
            print(f"🔍 [MGID]: تم رصد {len(unique_ads)} إعلان، جاري فك روابط التتبع بالحقن العميق...")
            
            resolved_map = {}
            current_target = None
            
            async def catch_iframe_req(req):
                nonlocal current_target, resolved_map
                u = req.url
                if req.resource_type in ["document", "sub_document"]:
                    is_tracking = any(x in u.lower() for x in [
                        "mgid.com", "adskeeper.com", "ploynest.com", "clck.", "ghits/", 
                        "onetrust.com", "cookieconsent", "cookielaw.org", "bot-detected",
                        "adtrafficquality.google", "googleadservices.com", "activeview", "sodar"
                    ])
                    if not is_tracking and len(u) > 25:
                        from urllib.parse import urlparse
                        try:
                            if "." in urlparse(u).netloc:
                                if current_target and current_target not in resolved_map:
                                    resolved_map[current_target] = u
                        except: pass

            page.on("request", catch_iframe_req)
            
            resolved_count = 0
            for ad in unique_ads.values():
                t_url = ad['landing']
                if "clck.mgid.com" in t_url or "clck.adskeeper.com" in t_url:
                    current_target = t_url
                    try:
                        await page.evaluate(f"""
                            (url) => {{
                                let iframe = document.getElementById('mgid_resolver_iframe');
                                if (!iframe) {{
                                    iframe = document.createElement('iframe');
                                    iframe.id = 'mgid_resolver_iframe';
                                    iframe.style.display = 'none';
                                    document.body.appendChild(iframe);
                                }}
                                iframe.src = url;
                            }}
                        """, t_url)
                        
                        # نراقب لمدة 8 ثواني
                        for _ in range(8):
                            if current_target in resolved_map:
                                ad['landing'] = resolved_map[current_target]
                                resolved_count += 1
                                break
                            await asyncio.sleep(1)
                    except: pass
                    current_target = None
            
            # تنظيف
            try:
                page.remove_listener("request", catch_iframe_req)
                await page.evaluate("document.getElementById('mgid_resolver_iframe')?.remove();")
            except: pass
            
            if resolved_count > 0:
                print(f"🔓 [MGID]: تم فك تشفير {resolved_count} رابط بشكل سري!")

            # 3. الحفظ النهائي والتصفية الصارمة (Dropping Unresolved/Malformed)
            saved_count = 0
            for ad in unique_ads.values():
                t_url = ad.get('landing', '').strip()
                
                # تخطي الروابط التي لم تنجح عملية فك التشفير لها
                if "clck.mgid.com" in t_url or "clck.adskeeper.com" in t_url:
                    continue
                
                # تخطي الروابط الخاطئة التي لا تملك اسم نطاق (TLD) صالح
                from urllib.parse import urlparse
                try:
                    p = urlparse(t_url)
                    if not p.netloc or "." not in p.netloc:
                        continue
                except: continue
                
                await save_to_supabase(ad)
                saved_count += 1
                
            print(f"✅ [MGID]: تم حفظ {saved_count} إعلانات نقية و 100% حقيقية من أصل {len(unique_ads)} في {url}")
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
