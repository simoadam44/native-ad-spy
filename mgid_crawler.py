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
        if not ad.get('title') or not ad.get('landing'): return
        clean_url = ad['landing'].split('?')[0]
        res = supabase.table("ads").select("id, impressions").eq("landing", clean_url).execute()
        
        if res.data:
            new_imp = (res.data[0].get('impressions') or 1) + 1
            supabase.table("ads").update({"impressions": new_imp, "last_seen": "now()", "country_code": TARGET_COUNTRY}).eq("id", res.data[0]['id']).execute()
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
    
    # 🚫 خطة الحظر العنيفة جداً (Zero-Trust) لتوفير الباندويث 
    async def block_resources(route):
        req = route.request
        res_type = req.resource_type
        url = req.url.lower()

        if res_type in ["image", "media", "font", "stylesheet", "websocket", "manifest", "other"]:
            await route.abort()
            return

        blocked_domains = [
            "google", "facebook", "twitter", "tiktok", "snapchat", "pinterest",
            "chartbeat", "btloader", "surveygizmo", "scorecardresearch", "hotjar",
            "criteo", "amazon", "rubicon", "openx", "pubmatic", "quantserve", "adroll",
            "mediavoice", "teads", "clarity", "doubleclick",
            "outbrain", "taboola", "revcontent", "sharethis"
        ]
        
        # استثناء الشبكة وحليفتها
        if any(kw in url for kw in blocked_domains) and "mgid.com" not in url and "adskeeper.com" not in url:
            await route.abort()
            return

        if res_type in ["script", "fetch", "xhr"]:
            if "mgid.com" in url or "adskeeper.com" in url:
                await route.continue_()
                return
            if any(sub in url for sub in ["static.", "assets.", "cdn.", "player.", "video.", "api."]):
                await route.abort()
                return

        await route.continue_()

    await page.route("**/*", block_resources)

    # تطبيق التخفي (Stealth) كإجراء احترازي دائم
    from playwright_stealth import Stealth
    await Stealth().apply_stealth_async(page)

    # اعتراض استجابات الـ API بشكل أكثر مرونة
    async def handle_response(response):
        nonlocal mgid_ads
        url_lower = response.url.lower()
        if ("mgid.com" in url_lower or "servicerun" in url_lower) and response.status == 200:
            try:
                # محاولة فحص المحتوى إذا كان JSON
                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type or "text/javascript" in content_type:
                    data = await response.json()
                    # MGID API often uses 'items' or 'data' or directly an array
                    if isinstance(data, dict):
                        items = data.get('items') or data.get('data') or []
                    elif isinstance(data, list):
                        items = data
                    else:
                        items = []
                    
                    for item in items:
                        if isinstance(item, dict) and (item.get('title') or item.get('text')):
                            mgid_ads.append({
                                "title": (item.get('title') or item.get('text', '')).strip(),
                                "landing": item.get('clickUrl') or item.get('url') or item.get('link', ''),
                                "image": item.get('mainImage') or item.get('thumbnail') or item.get('image', ''),
                                "source": url,
                                "network": "MGID"
                            })
            except: pass

    page.on("response", handle_response)

    try:
        # استخدام domcontentloaded بدلاً من networkidle لتجنب التعليق
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        except Exception as timeout_error:
            print(f"[MGID]: Timeout on page load, but continuing extraction... ({timeout_error})")
        
        # انتظار يدوي سريع للحد من استهلاك الجلسة الطويلة
        await asyncio.sleep(8) # الانتظار فترة قصيرة بدلاً من 30 ثانية لتسريع الإغلاق
        for i in range(5): # تقليل محاولات السكرول
            await page.evaluate(f"window.scrollBy(0, {800 + (i * 200)})")
            await asyncio.sleep(1)

        # ✅ Fallback: محاولة قراءة الإعلانات من DOM في كل الفريمات (iframes)
        if not mgid_ads:
            for frame in page.frames:
                try:
                    # استخدام locator الذي يخترق Shadow DOM تلقائياً عكس querySelectorAll
                    # تشمل .mgline و .mgbox وأي ويدجت يبدأ بـ mgid_
                    links = frame.locator('.mgline a, .mgbox a, [id^="mgid_"] a, .mgid-widget a, .mg-teaser a')
                    count = await links.count()
                    for i in range(count):
                        el = links.nth(i)
                        title = await el.inner_text()
                        href = await el.get_attribute("href")
                        if title and href:
                            title = title.strip()
                            # التحقق من أن الرابط صالح ليكون إعلان
                            if len(title) > 5 and href.startswith('http'):
                                # محاولة استخراج الصورة بأمان دون كسر الحلقة
                                image_url = ""
                                try:
                                    image_url = await el.evaluate("""
                                        (a) => {
                                            // 1. البحث عن img داخل الرابط
                                            let img = a.querySelector('img');
                                            if (img && (img.src || img.dataset.src)) return img.src || img.dataset.src;
                                            
                                            // 2. البحث عن أقرب حاوية للإعلان
                                            let container = a.closest('.mgline, .mgbox, .mgid-widget, .mg-teaser, .image-with-text, [id^="mgid_"]');
                                            if (!container) container = a.parentElement;
                                            
                                            // 3. البحث عن img داخل الحاوية
                                            let cImg = container.querySelector('img');
                                            if (cImg && (cImg.src || cImg.dataset.src)) return cImg.src || cImg.dataset.src;
                                            
                                            // 4. البحث عن background-image في الحاوية أو أبنائها (مثل .mcimg)
                                            let searchEls = [container, ...container.querySelectorAll('div, span, a, i')];
                                            for (let el of searchEls) {
                                                let style = window.getComputedStyle(el);
                                                let bg = style.backgroundImage;
                                                if (bg && bg !== 'none' && (bg.includes('http') || bg.includes('//'))) {
                                                    // تنظيف الرابط من url() والرموز الزائدة
                                                    let clean = bg.replace(/^url\(["']?/, '').replace(/["']?\)$/, '');
                                                    if (clean.startsWith('//')) clean = 'https:' + clean;
                                                    return clean;
                                                }
                                            }
                                            return '';
                                        }
                                    """)
                                except:
                                    pass
                                
                                mgid_ads.append({"title": title, "landing": href, "image": image_url or "", "source": url, "network": "MGID"})
                except:
                    pass

        if mgid_ads:
            unique_ads = {}
            for ad in mgid_ads:
                landing = ad['landing']
                if not landing: continue
                
                # ✅ فك تشفير روابط MGID أو AdsKeeper (الشبكة الرديفة) التتبعية
                if "clck.mgid.com" in landing or "clck.adskeeper.com" in landing:
                    try:
                        res = await context.request.get(landing, headers={"Referer": ad['source']}, max_redirects=5)
                        text = await res.text()
                        
                        # التوجيه الصريح (HTTP Redirect)
                        if res.url and "clck.mgid.com" not in res.url and "clck.adskeeper.com" not in res.url:
                            landing = res.url
                        else:
                            # التوجيه المبطن بالجافا سكريبت (JS Redirect)
                            import re
                            js_match = re.search(r'window\.location\.replace\(["\'](htt[^"\']+)["\']', text)
                            if js_match:
                                landing = js_match.group(1)
                            else:
                                meta_match = re.search(r'url=(http[^"\'\s>]+)', text, re.IGNORECASE)
                                if meta_match: landing = meta_match.group(1).strip("'\"")
                                
                        ad['landing'] = landing
                    except:
                        pass
                
                # إذا لم يكن موجوداً، أضفه
                if landing not in unique_ads:
                    unique_ads[landing] = ad
                # إذا كان موجوداً ولكن الجديد لديه صورة والقديم لا، استبدله
                elif ad.get('image') and not unique_ads[landing].get('image'):
                    unique_ads[landing] = ad
                # إذا كان الجديد لديه عنوان أطول، استبدله (أحياناً العناوين تختلف قليلاً)
                elif len(ad.get('title', '')) > len(unique_ads[landing].get('title', '')):
                    # احتفظ بالصورة القديمة إذا كانت موجودة
                    if unique_ads[landing].get('image') and not ad.get('image'):
                        ad['image'] = unique_ads[landing]['image']
                    unique_ads[landing] = ad            
            for ad in unique_ads.values():
                await save_to_supabase(ad)
            print(f"[MGID]: صيد {len(unique_ads)} إعلان بنجاح في {url}")
        else:
            print(f"[MGID]: لم يتم رصد إعلانات في {url}")

    except Exception as e:
        print(f"[MGID ERROR]: {e}")
    finally:
        await page.close()
        await context.close()

async def run():
    async with async_playwright() as p:
        # تشغيل متصفح مستقل (Launch) بدلاً من الاتصال (Connect) بناءً على طلبك
        try:
            print(f"Launching independent Chrome browser with proxy for {TARGET_COUNTRY}...")
            browser = await p.chromium.launch(
                headless=True, 
                proxy=PROXY_CONFIG,
                args=[
                    "--blink-settings=imagesEnabled=false",           # حظر الصور من جذور المحرك
                    "--disable-features=IsolateOrigins,site-per-process",
                    "--disable-background-networking",
                    "--disable-dev-shm-usage",
                    "--disable-extensions",
                    "--disable-sync",
                    "--no-sandbox"
                ]
            )
            
            # إعداد السياق مع تقنيات التخفي
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                locale=GEO["locale"],
                timezone_id=GEO["timezone_id"],
                permissions=["geolocation"]
            )
            
            # تطبيق التخفي (Stealth) لتقليل رصد الأتمتة
            from playwright_stealth import Stealth
            page = await context.new_page()
            
            # 🚫 منع تحميل الصور للحد من استهلاك الـ 10GB DataImpulse bandwidth
            await page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff2,ttf}", lambda route: route.abort())
            
            await Stealth().apply_stealth_async(page)
            
            for target in MGID_TARGETS:
                print(f"Checking target: {target}")
                await scrape_mgid(browser, target) # سنقوم بتعديل scrape_mgid لاستقبال المتصفح أو الصفحة
                await asyncio.sleep(random.uniform(3, 7))
                
        except Exception as e:
            print(f"Error launching browser: {e}")
        finally:
            if 'browser' in locals():
                await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
