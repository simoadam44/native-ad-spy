import asyncio, os, random, sys, re, json
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup
from supabase import create_client
from urllib.parse import urljoin
from langdetect import detect
from utils.url_resolver import resolve_url
from utils.advanced_detector import detect_from_chain
from utils.site_pool import get_rotation_config, get_random_ua, get_random_referrer

# --- 1. الإعدادات والاتصال الآمن ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# إعداد الدولة والبروكسي المتطور (DataImpulse)
TARGET_COUNTRY = os.environ.get("TARGET_COUNTRY", "US")

# إعداد الدولة والبروكسي المتطور (DataImpulse Datacenter HTTP)
PROXY_CONFIG = {
    "server": "http://gw.dataimpulse.com:823",
    "username": "7dce367ee7442e94dcd3",
    "password": "30243fe81b50b2de"
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

# ══════════════════════════════════════
# DYNAMIC SITE ROTATION — NO MORE LOOP TRAP
# Picks 5-8 random sites from the 200+ pool every run
# ══════════════════════════════════════
def get_session_config():
    config = get_rotation_config(geo=TARGET_COUNTRY)
    print(f"🎲 [REVCONTENT] Session config:")
    print(f"   User-Agent : {config['user_agent'][:80]}")
    print(f"   Referrer   : {config['referrer'] or '(direct)'}")
    print(f"   Sites ({len(config['sites'])}) :")
    for s in config["sites"]:
        print(f"     - {s}")
    return config


# محددات Revcontent المتطورة
REV_SELECTORS = [
    ".rc-item", ".rc-ad-container", ".sbn-item-anchor", 
    "[id*='rc-widget']", "div[data-rc-widget]", 
    ".revcontent-ad", ".rc-row", ".rc-cta"
]

async def save_or_update_ad(data):
    try:
        if not data.get('title') or not data.get('landing'): return
        
        # تصحيح رابط الصورة إذا كان يبدأ بـ //
        if data.get('image') and data['image'].startswith('//'):
            data['image'] = 'https:' + data['image']
            
        # Resolve final URL for accurate detection (Affiliate/Tracker)
        print(f"🔍 [Revcontent] Resolving: {data['landing'][:50]}...")
        final_url, redirect_chain = resolve_url(data['landing'])
        clean_landing = final_url.split('?')[0].split('#')[0]
        
        existing = supabase.table("ads").select("id, impressions").eq("landing", clean_landing).execute()
        
        # كشف اللغة بشكل متقدم (خاصة للغة العربية)
        def detect_lang(t):
            if re.search(r'[\u0600-\u06FF]', t):
                return 'ar'
            try:
                return detect(t)
            except:
                return 'en'

        lang = detect_lang(data['title'])
            
        # Detect from chain
        tracking_info = detect_from_chain(redirect_chain)
        aff_net = tracking_info["affiliate_network"]
        trk_tool = tracking_info["tracking_tool"]

        if existing.data:
            new_count = (existing.data[0].get('impressions') or 1) + 1
            supabase.table("ads").update({
                "impressions": new_count,
                "last_seen": "now()",
                "country_code": TARGET_COUNTRY,
                "language": lang,
                "affiliate_network": aff_net,
                "tracking_tool": trk_tool
            }).eq("id", existing.data[0]['id']).execute()
            print(f"📈 [REVCONTENT] [{TARGET_COUNTRY}] [{lang}]: تحديث ({new_count}): {data['title'][:50]}...")
        else:
            data.update({
                "landing": final_url,
                "impressions": 1, 
                "last_seen": "now()", 
                "country_code": TARGET_COUNTRY, 
                "language": lang, 
                "affiliate_network": aff_net, 
                "tracking_tool": trk_tool
            })
            supabase.table("ads").insert(data).execute()
            print(f"[REVCONTENT] [{TARGET_COUNTRY}] [{lang}]: صيد جديد: {data['title'][:50]}...")
    except Exception as e:
        print(f"⚠️ [DB ERROR]: {str(e)[:50]}")

async def scrape_revcontent(browser, url, semaphore, session_ua: str = None, session_referrer: str = None):
    async with semaphore:
        context = None
        page = None
        rev_ads = []
        ua = session_ua or get_random_ua()
        referrer = session_referrer if session_referrer is not None else get_random_referrer()
        try:
            context = await browser.new_context(
                proxy=PROXY_CONFIG,
                user_agent=ua,
                locale=GEO["locale"],
                timezone_id=GEO["timezone_id"],
                permissions=["geolocation"],
                extra_http_headers={
                    "Referer": referrer,
                    "Accept-Language": GEO["locale"].replace("_", "-") + ",en;q=0.8",
                } if referrer else {}
            )
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)
            
            # اعتراض استجابة الشبكة (Network Interception)
            async def handle_response(response):
                nonlocal rev_ads
                try:
                    r_url = response.url.lower()
                    if "revcontent.com" in r_url and "api" in r_url and response.status == 200:
                        ct = response.headers.get("content-type", "")
                        if "json" in ct or "javascript" in ct:
                            text = await response.text()
                            data = None
                            if text.strip().startswith('{') or text.strip().startswith('['):
                                data = json.loads(text)
                            else:
                                match = re.search(r'(\{.*\})|(\[.*\])', text)
                                if match: data = json.loads(match.group(0))
                            
                            if data and "content" in data:
                                for item in data["content"]:
                                    title = item.get('headline') or item.get('title')
                                    l_url = item.get('url')
                                    img = item.get('image')
                                    if title and l_url:
                                        rev_ads.append({
                                            "title": str(title).strip(),
                                            "landing": l_url,
                                            "image": img,
                                            "source": response.url,
                                            "network": "Revcontent"
                                        })
                except: pass

            page.on("response", handle_response)
            
            async def block_resources(route):
                req = route.request
                res_type = req.resource_type
                r_url = req.url.lower()

                # حظر صارم لكل ما هو غير ضروري للسحب (بما في ذلك الـ CSS والخطوط)
                if res_type in ["image", "media", "font", "stylesheet", "websocket", "manifest", "other"]:
                    await route.abort()
                    return

                blocked_domains = [
                    "google-analytics", "googletagmanager", "facebook", "twitter", "tiktok", "snapchat", "pinterest",
                    "chartbeat", "btloader", "surveygizmo", "scorecardresearch", "hotjar",
                    "criteo", "amazon", "rubicon", "openx", "pubmatic", "quantserve", "adroll",
                    "mediavoice", "teads", "clarity", "doubleclick",
                    "mgid.com", "outbrain.com", "taboola.com"
                ]
                
                if any(kw in r_url for kw in blocked_domains) and "revcontent.com" not in r_url:
                    await route.abort()
                    return

                if res_type in ["script", "fetch", "xhr"]:
                    # السماح لـ Revcontent فقط
                    if "revcontent.com" in r_url:
                        await route.continue_()
                        return
                    # حظر سكريبتات المواقع والـ CDNs الخارجية لتوفير البيانات
                    if any(sub in r_url for sub in ["static.", "assets.", "cdn.", "player.", "video.", "api."]):
                        await route.abort()
                        return

                await route.continue_()

            await page.route("**/*", block_resources)
            
            print(f"🚀 [REVCONTENT]: فحص الهدف: {url}")
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            
            # تمرير Progressive لتنشيط الـ Widgets
            for _ in range(5):
                await page.evaluate("window.scrollBy(0, 800)")
                await asyncio.sleep(1)
            await asyncio.sleep(5)
            
            # --- الاستخراج من DOM كخيار احتياطي ---
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            links = soup.select("a[href*='revcontent.com/click']")
            for selector in REV_SELECTORS:
                for el in soup.select(selector):
                    a_tag = el if el.name == 'a' else el.find("a", href=True)
                    if a_tag and a_tag not in links: links.append(a_tag)

            for a in links:
                try:
                    title_el = a.find(class_=lambda c: c and 'title' in c.lower()) or a.find("h3") or a.find("h4")
                    title = title_el.get_text(strip=True) if title_el else a.get_text(strip=True)
                    if not title or len(title) < 10:
                        parent = a.find_parent()
                        if parent:
                            t_el = parent.select_one(".rc-title, .title, h3, h4")
                            if t_el: title = t_el.get_text(strip=True)
                    
                    if not title or len(title) < 10: continue

                    img = a.find("img") or (a.find_parent() and a.find_parent().find("img"))
                    img_url = ""
                    if img:
                        img_url = img.get("data-src") or img.get("src") or img.get("data-lazy-src") or ""
                    
                    if not img_url:
                        # البحث في الستايل الخاص بالخلفية
                        style = a.get('style', '') or (a.find_parent() and a.find_parent().get('style', ''))
                        match = re.search(r"url\(['\"]?(.*?)['\"]?\)", style or "")
                        if match: img_url = match.group(1)

                    rev_ads.append({
                        "title": title.strip(),
                        "image": img_url,
                        "landing": urljoin(url, a['href']),
                        "source": url,
                        "network": "Revcontent"
                    })
                except: continue

            # تنظيف النتائج وحفظها
            if rev_ads:
                unique = {}
                for ad in rev_ads:
                    if ad['landing'] not in unique: unique[ad['landing']] = ad
                for ad in unique.values():
                    await save_or_update_ad(ad)
                print(f"✅ [REVCONTENT]: تم صيد {len(unique)} إعلان من {url}")
            else:
                print(f"ℹ️ [REVCONTENT]: لم يتم رصد إعلانات في {url}")
                
        except Exception as e:
            print(f"⚠️ تجاوز {url}: {str(e)[:100]}")
        finally:
            if page: await page.close()
            if context: await context.close()

async def run_spy():
    # Get fresh random session config
    session = get_session_config()
    sites = session["sites"]
    ua = session["user_agent"]
    referrer = session["referrer"]

    semaphore = asyncio.Semaphore(1)
    async with async_playwright() as p:
        print(f"Launching independent Chrome browser with proxy for {TARGET_COUNTRY}...")
        browser = await p.chromium.launch(
            headless=True, 
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
        for site in sites:
            await scrape_revcontent(browser, site, semaphore, session_ua=ua, session_referrer=referrer)
            delay = random.uniform(3, 10)
            print(f"⏳ [REVCONTENT] Waiting {delay:.1f}s before next site...")
            await asyncio.sleep(delay)
            # 30% chance of rotating UA mid-session
            if random.random() < 0.3:
                ua = get_random_ua()
                referrer = get_random_referrer()
                print(f"🔄 [REVCONTENT] Mid-session UA rotation")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_spy())
