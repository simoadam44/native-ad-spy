import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from bs4 import BeautifulSoup
from supabase import create_client
from urllib.parse import urljoin, unquote
import os
import re
import json
from langdetect import detect
from utils.url_resolver import resolve_url
from utils.advanced_detector import detect_from_chain

# إعدادات سوبابيز
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# إعداد الدولة والبروكسي المتطور
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

TABOOLA_ARTICLE_SITES = [
    "https://www.tips-and-tricks.co/do-it-yourself/shoestretch/", 
    "https://sabq.org/article/Ybvpfba",     
    "https://www.habittribe.com/wellness/water", 
    "https://www.independent.co.uk",
    "https://www.articlestone.com/social/rings",
    "https://www.dailysportx.com/news/vveins",
    "https://www.tips-and-tricks.co/online/sisterrevenge/2/"
]

async def save_or_update_ad(data):
    try:
        if not data.get('title') or not data.get('landing'): return
        # Resolve final URL for accurate detection (Affiliate/Tracker)
        print(f"🔍 [Taboola] Resolving: {data['landing'][:50]}...")
        final_url, redirect_chain = resolve_url(data['landing'])
        clean_landing = final_url.split('?')[0].split('#')[0]
        
        # منع تكرار الروابط في الذاكرة لتجنب استهلاك سوبابيز غير الضروري
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
            print(f"📈 [TABOOLA] [{TARGET_COUNTRY}] [{lang}]: تحديث ({new_count}): {data['title'][:30]}")
        else:
            data.update({
                "impressions": 1, 
                "last_seen": "now()", 
                "country_code": TARGET_COUNTRY, 
                "language": lang, 
                "affiliate_network": aff_net, 
                "tracking_tool": trk_tool
            })
            supabase.table("ads").insert(data).execute()
            print(f"[TABOOLA] [{TARGET_COUNTRY}] [{lang}]: صيد جديد: {data['title'][:30]}")
    except Exception as e:
        print(f"⚠️ [TABOOLA] DB Error: {e}")

async def smart_scroll_and_wait(page):
    print("🖱️ [TABOOLA]: جاري التمرير الذكي لتنشيط التحميل المتأخر (Lazy Load)...")
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
    await asyncio.sleep(10) # زيادة وقت الانتظار لضمان الرندرة

async def scrape_taboola(browser, url, semaphore):
    async with semaphore:
        context = None
        page = None
        taboola_ads = []
        try:
            context = await browser.new_context(
                proxy=PROXY_CONFIG,
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
                locale=GEO["locale"],
                timezone_id=GEO["timezone_id"],
                permissions=["geolocation"]
            )
            page = await context.new_page()
            await Stealth().apply_stealth_async(page)
            
            # خطة توفير البيانات: حظر الصور والميديا والخطوط
            async def block_resources(route):
                if route.request.resource_type in ["image", "media", "font", "manifest"]:
                    await route.abort()
                else:
                    await route.continue_()
            await page.route("**/*", block_resources)
            
            # اعتراض استجابة الشبكة (Network Interception)
            async def handle_response(response):
                nonlocal taboola_ads
                url_lower = response.url.lower()
                if "taboola.com" in url_lower and "v2/notifications" not in url_lower:
                    try:
                        if response.status == 200:
                            ct = response.headers.get("content-type", "")
                            if "json" in ct or "javascript" in ct:
                                text = await response.text()
                                if "list" in text or "items" in text:
                                    # محاولة استخراج كائنات تشبه الإعلانات من النص الخام إذا لم يكن JSON نقياً
                                    match = re.search(r'\[\{.*\}\]', text)
                                    data_list = []
                                    if match:
                                        try: data_list = json.loads(match.group(0))
                                        except: pass
                                    else:
                                        try:
                                            resp_json = await response.json()
                                            data_list = resp_json.get('list', [])
                                        except: pass
                                    
                                    for item in data_list:
                                        title = item.get('name') or item.get('content') or item.get('title')
                                        url = item.get('url') or item.get('clickUrl')
                                        img = item.get('thumbnail', [{}])[0].get('url') if isinstance(item.get('thumbnail'), list) else ""
                                        if title and url:
                                            taboola_ads.append({
                                                "title": str(title).strip(),
                                                "landing": url,
                                                "image": img,
                                                "source": response.url,
                                                "network": "Taboola"
                                            })
                    except: pass

            page.on("response", handle_response)
            
            async def block_resources(route):
                req = route.request
                res_type = req.resource_type
                url = req.url.lower()

                # حظر صارم لكل ما هو غير ضروري للسحب (بما في ذلك الـ CSS والخطوط)
                if res_type in ["image", "media", "font", "stylesheet", "websocket", "manifest", "other"]:
                    await route.abort()
                    return
                
                # قائمة المحظورات المعروفة (Trackers)
                blocked_domains = [
                    "google-analytics", "googletagmanager", "facebook.com", "twitter.com", "tiktok.com",
                    "doubleclick", "scorecardresearch", "hotjar", "chartbeat", "quantserve",
                    "mgid.com", "outbrain.com", "revcontent.com"
                ]
                if any(kw in url for kw in blocked_domains) and "taboola.com" not in url:
                    await route.abort()
                    return
                
                if res_type in ["script", "fetch", "xhr"]:
                    # السماح لـ Taboola فقط
                    if "taboola.com" in url:
                        await route.continue_()
                        return
                    # حظر سكريبتات المواقع والـ CDNs الخارجية لتوفير البيانات
                    if any(sub in url for sub in ["static.", "assets.", "cdn.", "player.", "video.", "api."]):
                        await route.abort()
                        return
                        
                await route.continue_()

            await page.route("**/*", block_resources)
            
            print(f"🚀 [TABOOLA]: فحص الهدف: {url}")
            await page.goto(url, timeout=60000, wait_until="domcontentloaded")
            await smart_scroll_and_wait(page)
            
            # --- الاستخراج من DOM (Main Page & Frames) ---
            async def extract_from_soup(soup_obj, base_url):
                found = []
                selectors = [".trc_spotlight_item", ".taboola-main-container", "[id*='taboola']", ".trc_item"]
                for selector in selectors:
                    for ad in soup_obj.select(selector):
                        try:
                            link_tag = ad.find("a")
                            if not link_tag or not link_tag.get("href"): continue
                            title_el = ad.find(class_=re.compile(r"video-title|trc_label|title"))
                            title = title_el.get_text(strip=True) if title_el else ad.get_text(strip=True)
                            landing = urljoin(base_url, link_tag.get("href"))
                            img_tag = ad.find("img")
                            image_raw = ""
                            if img_tag:
                                image_raw = img_tag.get("data-src") or img_tag.get("src") or img_tag.get("data-lazy-src") or img_tag.get("srcset") or ""
                            if not image_raw:
                                bg_el = ad.find(style=re.compile(r"background-image"))
                                if bg_el:
                                    match = re.search(r"url\(['\"]?(.*?)['\"]?\)", bg_el.get("style", ""))
                                    if match: image_raw = match.group(1)
                            
                            # تنظيف رابط الصورة
                            if "taboola.com" in image_raw:
                                if "/ui/?src=" in image_raw:
                                    match = re.search(r"/ui/\?src=(.*?)&", image_raw)
                                    if match: image_raw = unquote(match.group(1))
                                image_raw = image_raw.split('?')[0]
                            
                            image_url = urljoin(base_url, image_raw) if image_raw else ""
                            if image_url.startswith("//"): image_url = "https:" + image_url
                            
                            if title and len(title) > 10:
                                found.append({"title": title[:200], "image": image_url, "landing": landing, "source": base_url, "network": "Taboola"})
                        except: continue
                return found

            # الرئيسي
            content = await page.content()
            taboola_ads.extend(await extract_from_soup(BeautifulSoup(content, "html.parser"), url))
            
            # الإطارات (Frames)
            for frame in page.frames:
                try:
                    f_content = await frame.content()
                    taboola_ads.extend(await extract_from_soup(BeautifulSoup(f_content, "html.parser"), url))
                except: pass

            # معالجة النتائج الفريدة
            if taboola_ads:
                unique = {}
                for ad in taboola_ads:
                    if ad['landing'] not in unique: unique[ad['landing']] = ad
                for ad in unique.values():
                    await save_or_update_ad(ad)
                print(f"✅ [TABOOLA]: تم صيد {len(unique)} إعلان في {url}")
            else:
                print(f"ℹ️ [TABOOLA]: لم يتم رصد إعلانات في {url}")

        except Exception as e:
            print(f"⚠️ [TABOOLA] Error في {url}: {str(e)[:100]}")
        finally:
            if page: await page.close()
            if context: await context.close()

async def run_spy():
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
        await asyncio.gather(*[scrape_taboola(browser, s, semaphore) for s in TABOOLA_ARTICLE_SITES])
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_spy())
