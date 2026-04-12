import asyncio, os, random, sys, re, json
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup
from supabase import create_client
from urllib.parse import urljoin
from langdetect import detect
import sys as _sys
import os as _os
_sys.path.insert(0, _os.path.dirname(__file__))
from utils.affiliate_detector import detect_affiliate_network
from utils.tracker_detector import detect_tracking_tool

# --- 1. الإعدادات والاتصال الآمن ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

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

REVCONTENT_TARGETS = [
    "https://joehoft.com/doj-leadership-quietly-dismantles-weaponization-working-group-despite/",
    "https://wltreport.com/2026/04/03/watch-president-trump-delivers-easter-message-be-great/",
    "https://wltreport.com/2026/04/03/update-one-pilot-rescued-another-still-missing-after/?utm_source=PTN&utm_medium=mixed&utm_campaign=PTN",
    "https://gatewayhispanic.com/2026/04/trump-emite-un-comunicado-sobre-el-despido-de/",
    "https://100percentfedup.com/lets-talk-about-artemis-ii-moon-launch-part/"
]

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
            
        clean_landing = data['landing'].split('?')[0].split('#')[0]
        data["landing"] = clean_landing
        
        existing = supabase.table("ads").select("id, impressions").eq("landing", clean_landing).execute()
        
        # كشف اللغة
        try:
            lang = detect(data['title'])
        except:
            lang = 'en'
            
        if existing.data:
            new_count = (existing.data[0].get('impressions') or 1) + 1
            supabase.table("ads").update({
                "impressions": new_count,
                "last_seen": "now()",
                "country_code": TARGET_COUNTRY,
                "language": lang
            }).eq("id", existing.data[0]['id']).execute()
            print(f"📈 [REVCONTENT] [{TARGET_COUNTRY}] [{lang}]: تحديث ({new_count}): {data['title'][:50]}...")
        else:
            try:
                aff = detect_affiliate_network(clean_landing)
            except:
                aff = {'network': 'Direct / Unknown'}
            try:
                trk = detect_tracking_tool(clean_landing)
            except:
                trk = {'tracker': 'No Tracking'}
            data.update({"impressions": 1, "last_seen": "now()", "country_code": TARGET_COUNTRY, "language": lang, "affiliate_network": aff['network'], "tracking_tool": trk['tracker']})
            supabase.table("ads").insert(data).execute()
            print(f"[REVCONTENT] [{TARGET_COUNTRY}] [{lang}]: صيد جديد: {data['title'][:50]}...")
    except Exception as e:
        print(f"⚠️ [DB ERROR]: {str(e)[:50]}")

async def scrape_revcontent(browser, url, semaphore):
    async with semaphore:
        context = None
        page = None
        rev_ads = []
        try:
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
                locale=GEO["locale"],
                timezone_id=GEO["timezone_id"],
                permissions=["geolocation"]
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
    sites = []
    try:
        response = supabase.table("target_sites").select("url").execute()
        if response.data:
            sites = [row['url'] for row in response.data][:10] # تحديد العدد للاختبار
    except: pass

    if not sites: sites = REVCONTENT_TARGETS

    semaphore = asyncio.Semaphore(2)
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
        await asyncio.gather(*[scrape_revcontent(browser, s, semaphore) for s in sites])
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_spy())
