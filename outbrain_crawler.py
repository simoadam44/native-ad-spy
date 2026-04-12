import asyncio, os, random, sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from supabase import create_client
import json
import re
from langdetect import detect

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
    "https://www.foxnews.com/politics/carney-casts-himself-nato-defender-amid-trump-beef-despite-canada-missing-key-benchmark-decades",
    "https://www.foxnews.com/world",
    "https://www.foxnews.com/us/ex-biden-staffer-claims-accidental-shot-killed-girlfriend-dad-blasts-toxic-abusive-relationship-report",
    "https://www.dailymail.co.uk/news/article-15726397/Woman-raped-outside-church-surrey-police.html",
    "https://www.lemonde.fr/en/european-union/article/2024/05/21/the-eu-s-artificial-intelligence-act-is-finally-adopted_6672074_156.html",
    "https://www.9news.com.au/world/us-israel-iran-war-donald-trump-says-us-will-block-ships-crossing-strait-of-hormuz/2d285cc7-18a9-4061-971e-d0cc6a681169",
    "https://www.marca.com/en/football/real-madrid/2024/05/21/664c8d5046163f91598b4594.html",
    "https://www.lequipe.fr/Football/Article/Toni-kroos-real-madrid-la-legende-s-en-va/1470404"
]]



async def save_to_supabase(ad):
    try:
        if not ad.get('title') or not ad.get('landing'): return
        
        # كشف اللغة تلقائياً
        try:
            ad['language'] = detect(ad['title'])
        except:
            ad['language'] = 'en'
            
        clean_url = ad['landing'].split('&dicbo=')[0] if '&dicbo=' in ad['landing'] else ad['landing']
        res = supabase.table("ads").select("id, impressions").eq("landing", clean_url).execute()
        
        if res.data:
            new_imp = (res.data[0].get('impressions') or 1) + 1
            supabase.table("ads").update({
                "impressions": new_imp, 
                "last_seen": "now()", 
                "country_code": TARGET_COUNTRY,
                "language": ad['language']
            }).eq("id", res.data[0]['id']).execute()
            print(f"📈 [OUTBRAIN] [{TARGET_COUNTRY}] [{ad['language']}]: تحديث ({new_imp}): {ad['title'][:40]}...")
        else:
            ad.update({"landing": clean_url, "impressions": 1, "last_seen": "now()", "country_code": TARGET_COUNTRY})
            supabase.table("ads").insert(ad).execute()
            print(f"✨ [OUTBRAIN] [{TARGET_COUNTRY}] [{ad['language']}]: صيد جديد: {ad['title'][:40]}...")
    except Exception as e:
        print(f"⚠️ [DB ERROR]: {e}")

async def smart_scroll_and_wait(page):
    print("🖱️ [OUTBRAIN]: جاري التمرير الذكي لتفعيل إعلانات Outbrain...")
    await page.evaluate("""
        async () => {
            await new Promise((resolve) => {
                let totalHeight = 0;
                let distance = 500;
                let patience = 0;

                let timer = setInterval(() => {
                    let scrollHeight = document.body.scrollHeight;
                    window.scrollBy(0, distance);
                    totalHeight += distance;

                    if (totalHeight >= scrollHeight) {
                        patience++;
                        if (patience > 4) { 
                            clearInterval(timer);
                            resolve();
                        }
                    } else {
                        patience = 0;
                    }
                    
                    if(totalHeight > 30000){
                        clearInterval(timer);
                        resolve();
                    }
                }, 400);
            });
        }
    """)
    await asyncio.sleep(12)

async def scrape_outbrain(browser, url):
    outbrain_ads = []
    context = None
    page = None
    try:
        # 🕵️ تعزيز التخفي: تنويع بصمة المتصفح
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
            "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Safari/605.1.15"
        ]
        viewports = [
            {"width": 1920, "height": 1080},
            {"width": 1440, "height": 900},
            {"width": 1366, "height": 768},
            {"width": 1536, "height": 864}
        ]
        
        # إضافة Referer عشوائي لإيهام الموقع بأن الزيارة طبيعية من بحث جوجل أو موقع شهير
        referers = ["https://www.google.com/", "https://www.bing.com/", "https://news.google.com/"]
        
        context = await browser.new_context(
            user_agent=random.choice(user_agents),
            viewport=random.choice(viewports),
            extra_http_headers={"Referer": random.choice(referers)},
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

            # حظر الميديا الثقيلة فقط، مع السماح للفروع الأخرى التي قد يستخدمها Outbrain للتحقق من الرؤية
            if res_type in ["image", "media", "font", "manifest"]:
                await route.abort()
                return
            
            # قائمة المحظورات المعروفة (Trackers)
            blocked_domains = [
                "google-analytics", "googletagmanager", "facebook.com", "twitter.com", "tiktok.com",
                "doubleclick", "scorecardresearch", "hotjar", "chartbeat", "quantserve",
                "mgid.com", "taboola.com", "revcontent.com", "doubleclick.net"
            ]
            
            # السماح المطلق لنطاقات Outbrain
            outbrain_domains = ["outbrain.com", "outbrainimg.com", "widgets.outbrain.com", "log.outbrain.com"]
            if any(kw in url_low for kw in outbrain_domains):
                await route.continue_()
                return

            if any(kw in url_low for kw in blocked_domains):
                await route.abort()
                return
                
            if res_type in ["script", "fetch", "xhr"]:
                # السماح لـ Outbrain فقط ونطاقات المقالات المهمة
                if "outbrain.com" in url_low:
                    await route.continue_()
                    return

            await route.continue_()

        await page.route("**/*", block_resources)

        async def handle_response(response):
            nonlocal outbrain_ads
            r_url = response.url.lower()
            
            # Outbrain responses can be JSON or JS callbacks (e.g. OB_REC_CALLBACK)
            if "outbrain.com" in r_url and response.status == 200:
                try:
                    ct = response.headers.get("content-type", "").lower()
                    if "application/json" in ct or "text/javascript" in ct or "application/javascript" in ct:
                        text = await response.text()
                        
                        # Debug logic for development
                        if "listings" in text.lower() or "documents" in text.lower():
                            print(f"📡 [OUTBRAIN API]: Captured potential data from {r_url[:60]}...")

                        data = None
                        # Extract JSON from potential JSONP / Callback
                        if text.strip().startswith('{') or text.strip().startswith('['):
                            try:
                                data = json.loads(text)
                            except: pass
                        
                        if not data:
                            # Try to find JSON inside a callback function wrapper (must use re.DOTALL for multiline responses)
                            match = re.search(r'\((\{.*?\})\)', text, re.DOTALL) or re.search(r'(\{.*?\})', text, re.DOTALL)
                            if match:
                                try:
                                    data = json.loads(match.group(1) if match.group(1) else match.group(0))
                                except: pass
                        
                        if data:
                            listings = []
                            # Drill down into common Outbrain nested structures
                            def extract_recursive(obj):
                                if isinstance(obj, list):
                                    for item in obj:
                                        if isinstance(item, dict) and ('title' in item or 'content' in item):
                                            listings.append(item)
                                elif isinstance(obj, dict):
                                    for k, v in obj.items():
                                        if k in ['documents', 'items', 'ads', 'listings', 'doc'] and isinstance(v, (list, dict)):
                                            if isinstance(v, list): listings.extend(v)
                                            else: extract_recursive(v)
                                        elif isinstance(v, (dict, list)):
                                            extract_recursive(v)

                            extract_recursive(data)
                            
                            for item in listings:
                                t = item.get('content') or item.get('title') or item.get('text')
                                l = item.get('url') or item.get('clickUrl') or item.get('link')
                                if t and l:
                                    # Image extraction
                                    img = ""
                                    thumbnail = item.get('image') or item.get('thumbnail')
                                    if isinstance(thumbnail, dict):
                                        img = thumbnail.get('url') or thumbnail.get('src') or ""
                                    elif isinstance(thumbnail, list) and len(thumbnail) > 0:
                                        img = thumbnail[0].get('url') if isinstance(thumbnail[0], dict) else thumbnail[0]
                                    else:
                                        img = str(thumbnail or "")

                                    if img.startswith('//'): img = 'https:' + img
                                    
                                    outbrain_ads.append({
                                        "title": str(t).strip(), 
                                        "landing": l, 
                                        "image": img, 
                                        "source": url, 
                                        "network": "OUTBRAIN"
                                    })
                except Exception as e:
                    pass

        page.on("response", handle_response)
        print(f"🚀 [OUTBRAIN]: فحص الهدف: {url}")
        
        try:
            await page.goto(url, wait_until="domcontentloaded", timeout=35000)
            
            # 🧠 منطق الذكاء الاصطناعي المتطور: 
            # 1. إذا كان الرابط طويلاً ويحتوي على "-" أو تاريخ، فهو مقال بالفعل. لا نغيره.
            # 2. إذا كان الرابط قصيراً (صفحة رئيسية أو تصنيف)، نبحث عن مقال عميق.
            is_article = (len(url) > 65 and "-" in url) or any(yr in url for yr in ["-2024", "-2025", "-2026"])
            
            if not is_article or url.endswith("/") or url.endswith("/world") or url.endswith("/news"):
                print(f"🔄 [OUTBRAIN]: استكشاف أقسام الموقع للبحث عن مقال حقيقي...")
                article_url = await page.evaluate("""
                    () => {
                        let links = Array.from(document.querySelectorAll('a[href]'));
                        // نركز على الروابط الطويلة والمقالات الحقيقية ونتجنب التصنيفات والأخبار المباشرة
                        let valid = links.filter(a => {
                            let h = a.href.toLowerCase();
                            return h.startsWith('http') && 
                                   h.length > 70 && 
                                   (h.includes('-') || h.includes('/202')) &&
                                   !h.includes('/video/') &&
                                   !h.includes('/category/') &&
                                   !h.includes('/author/') &&
                                   !h.includes('/about/') &&
                                   !h.includes('/live-news/') &&
                                   !h.includes('facebook.com') && 
                                   !h.includes('twitter.com');
                        });
                        return valid.length > 0 ? valid[0].href : null;
                    }
                """)
                if article_url and article_url != url:
                    print(f"📄 [OUTBRAIN]: تم القنص! تحويل المسار فرعي إلى مقال عميق: {article_url[:80]}...")
                    url = article_url
                    await page.goto(url, wait_until="domcontentloaded", timeout=60000)
                    
        except Exception as e:
            print(f"⚠️ [OUTBRAIN WARNING]: Timeout reached, continuing with what loaded... ({e})")
            
        # الموافقة التلقائية المتقدمة على ملفات تعريف الارتباط لتفعيل Outbrain
        try:
            print("🍪 [OUTBRAIN]: جاري التعامل مع جدران الموافقة (Consent Walls)...")
            await page.evaluate("""
                () => {
                    const selectors = [
                        '#onetrust-accept-btn-handler', // OneTrust
                        '.sp-manager-button-accept', // Sourcepoint
                        '#didomi-notice-agree-button', // Didomi
                        '.cmp-button_accept', // CMP
                        '.ok-button', '.allow-button', '.accept-all'
                    ];
                    
                    // البحث عن الأزرار باستخدام النص إذا لم تنجح المحددات
                    let buttons = Array.from(document.querySelectorAll('button, a'));
                    let acceptBtn = buttons.find(b => {
                        let txt = b.innerText.toLowerCase();
                        return txt.includes('accept all') || txt.includes('accept and continue') || 
                               txt.includes('alles akzeptieren') || txt.includes('accepter tout') ||
                               txt.includes('zustimmen') || txt.includes('agree');
                    });
                    
                    if (acceptBtn) {
                        acceptBtn.click();
                        return "Clicked via Text Search";
                    }
                    
                    for (let s of selectors) {
                        let el = document.querySelector(s);
                        if (el) { el.click(); return "Clicked: " + s; }
                    }
                }
            """)
            await asyncio.sleep(3) # انتظر قليلاً لتحميل الإعلانات بعد الموافقة
        except: pass
        
        await asyncio.sleep(2)
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
                            
                            if (title.length > 5 && href && href.startsWith('http')) {
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

    except Exception as e:
        err_msg = str(e)
        if "Execution context was destroyed" in err_msg:
            print("⚠️ [OUTBRAIN WARNING]: اكتشاف إعادة تحميل للصفحة (بسبب الكوكيز غالباً). جاري الانتظار لالتقاط إعلانات Outbrain...")
            await asyncio.sleep(12)
        else:
            print(f"⚠️ [OUTBRAIN ERROR]: {err_msg}")
            
        # 2. فك تشفير روابط Outbrain (Resolution Engine)
        # سنستخدم إطار عمل مخفي للوصول للروابط الحقيقية بصمت
        resolved_map = {}
        current_target = None
        
        async def catch_ob_req(request):
            nonlocal resolved_map, current_target
            r_url = request.url
            if request.resource_type in ["document", "xhr", "fetch"]:
                # تجاهل الروابط التقنية
                if not any(x in r_url.lower() for x in ["outbrain.com", "doubleclick", "googletag", "cookie", "bot-"]):
                    if len(r_url) > 20 and r_url.startswith("http") and current_target:
                        resolved_map[current_target] = r_url

        page.on("request", catch_ob_req)
        
        print(f"🕵️ [OUTBRAIN]: جاري فك تشفير {len(outbrain_ads)} رابط لضمان النقاء...")
        for ad in outbrain_ads:
            t_url = ad['landing']
            if "outbrain.com" in t_url:
                current_target = t_url
                try:
                    await page.evaluate(f"""
                        (url) => {{
                            let ifr = document.getElementById('ob_resolver_ifr');
                            if (!ifr) {{
                                ifr = document.createElement('iframe');
                                ifr.id = 'ob_resolver_ifr';
                                ifr.style.display = 'none';
                                document.body.appendChild(ifr);
                            }}
                            ifr.src = url;
                        }}
                    """, t_url)
                    for _ in range(7): # ننتظر 7 ثواني للتحويل
                        if current_target in resolved_map:
                            ad['landing'] = resolved_map[current_target]
                            break
                        await asyncio.sleep(1)
                except: pass
        
        page.remove_listener("request", catch_ob_req)
        try: await page.evaluate("document.getElementById('ob_resolver_ifr')?.remove()")
        except: pass

    # معالجة النتائج سواء تمت بنجاح تام أو بعد التوقف بسبب إعادة التحميل
        if outbrain_ads:
            unique_ads = {}
            for ad in outbrain_ads:
                # تصفية صارمة: لا نحفظ روابط Outbrain الأصلية أو روابط القياس
                final_url = ad['landing']
                is_bogus = any(x in final_url.lower() for x in ["outbrain.com", "googleadservices", "sodar", "activeview"])
                if is_bogus: continue
                
                if ad['landing'] and ad['title'] and ad['landing'] not in unique_ads: 
                    unique_ads[ad['landing']] = ad
            
            for ad in unique_ads.values(): await save_to_supabase(ad)
            print(f"✅ [OUTBRAIN]: تم صيد {len(unique_ads)} إعلان نقي في {url}")
            return True
        else:
            print(f"ℹ️ [OUTBRAIN]: لم يتم رصد إعلانات في {url}")
            return False

    except Exception as e:
        err_msg = str(e)
        if "Execution context was destroyed" in err_msg:
            print("⚠️ [OUTBRAIN WARNING]: اكتشاف إعادة تحميل للصفحة. جاري المحاولة النهائية...")
            await asyncio.sleep(5)
        else:
            print(f"⚠️ [OUTBRAIN ERROR]: {err_msg}")
        return False
    finally:
        try:
            if page: await page.close()
            if context: await context.close()
        except: pass

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
            success = False
            for attempt in range(2): # محاولة ثانية في حال الفشل (Retry Logic)
                if attempt > 0:
                    print(f"🔄 [OUTBRAIN]: إعادة المحاولة ({attempt + 1}/2) للهدف: {target}")
                    await asyncio.sleep(10)
                
                try: 
                    success = await scrape_outbrain(browser, target)
                    if success: break
                except Exception as e:
                    print(f"⚠️ [RETRY WARNING]: {e}")
            
            await asyncio.sleep(random.uniform(3, 7))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
