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
    "MA": {"locale": "ar-MA", "timezone_id": "Africa/Casablanca"},
    "SA": {"locale": "ar-SA", "timezone_id": "Asia/Riyadh"},
    "AE": {"locale": "ar-AE", "timezone_id": "Asia/Dubai"},
    # ... بقية الإعدادات كما هي في كودك الأصلي
}
GEO = COUNTRY_CONFIGS.get(TARGET_COUNTRY, COUNTRY_CONFIGS["US"])

MGID_TARGETS = [url.strip() for url in [
    "https://pjmedia.com/vodkapundit/2026/03/23/are-you-ready-for-the-dems-2028-presidential-childhood-trauma-olympics-n4950953",
    "https://www.ibtimes.com/us-secured-secret-deal-cameroon-deport-migrants-using-aid-leverage-report-3800110",
    "https://herbeauty.co/ar/altarfih/maqati-video-raqs-zouk-lan-tastatia-at-tawaqquf-an-mushahadatiha-miraran-wa-takraran/",
    "https://buzzday.info/2026/02/13/what-happens-if-you-consume-ginger-every-day/",
    "https://zestradar.com/celebrities/the-worst-beckham-family-rumors-theyll-never-outrun/"
]]

async def resolve_final_url(url):
    """Resolve the final URL by following redirects using httpx with GET request"""
    try:
        import httpx
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        async with httpx.AsyncClient(follow_redirects=True, headers=headers, timeout=15) as client:
            response = await client.get(url)
            final_url = str(response.url)
            if final_url != url:
                print(f"🔗 Resolved: {url[:50]}... -> {final_url[:50]}...")
            return final_url
    except Exception as e:
        print(f"❌ Failed to resolve {url[:50]}...: {e}")
        return None

async def save_to_supabase(ad):
    try:
        if not ad.get('title') or not ad.get('landing'): return
        
        # Resolve redirect URLs to get the real landing page
        landing_url = ad.get('landing', '')
        if 'clck.mgid.com' in landing_url or 'clck.adskeeper' in landing_url:
            resolved_url = await resolve_final_url(landing_url)
            if resolved_url:
                landing_url = resolved_url
        
        clean_url = landing_url.split('?')[0]
        
        res = supabase.table("ads").select("id, impressions").eq("landing", clean_url).execute()
        
        if res.data:
            new_imp = (res.data[0].get('impressions') or 1) + 1
            supabase.table("ads").update({"impressions": new_imp, "last_seen": "now()", "country_code": TARGET_COUNTRY}).eq("id", res.data[0]['id']).execute()
            print(f"[MGID] [{TARGET_COUNTRY}]: تحديث ({new_imp}): {ad['title'][:40]}...")
        else:
            # Use upsert for cleaner code
            ad_data = {
                "title": ad.get('title', ''),
                "landing": clean_url,
                "image": ad.get('image', ''),
                "source": ad.get('source', ''),
                "network": ad.get('network', 'MGID'),
                "impressions": 1,
                "last_seen": "now()",
                "country_code": TARGET_COUNTRY
            }
            supabase.table("ads").upsert(ad_data, on_conflict="landing").execute()
            print(f"[MGID] [{TARGET_COUNTRY}]: صيد جديد: {ad['title'][:40]}...")
>>>>>>> f53831774e7965d169131f5d04dc00ec8225f164
    except Exception as e:
        print(f"[DB ERROR]: {e}")

async def scrape_mgid(browser, url):
    mgid_ads = []
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
        locale=GEO["locale"],
        timezone_id=GEO["timezone_id"]
    )
    page = await context.new_page()
    await Stealth().apply_stealth_async(page)

    # حظر الموارد لتقليل استهلاك الداتا
    async def block_resources(route):
        if route.request.resource_type in ["image", "media", "font"]:
            await route.abort()
        else:
            await route.continue_()
    await page.route("**/*", block_resources)

    try:
        print(f"Scraping: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=60000)
        await asyncio.sleep(5) # انتظار تحميل الـ Widgets

        # ✅ الحل الرئيسي: استخراج الرابط الحقيقي من DOM مباشرة
        # نركز على mctitle a و mgline a كما في الصورة التي أرفقتها
        dom_ads = await page.evaluate("""
            () => {
                let ads = [];
                // استهداف الروابط داخل حاويات MGID المعروفة
                let selectors = '.mctitle a, .mgline a, .mgbox a, [class*="mgid"] a';
                document.querySelectorAll(selectors).forEach(a => {
                    let title = a.innerText.strip();
                    let href = a.getAttribute('href');
                    
                    // إذا كان الرابط لا يحتوي على clck.mgid.com فهو الرابط الحقيقي المطلوب
                    if (title.length > 5 && href && !href.includes('clck.mgid.com')) {
                        let img = a.closest('[class*="mgbox"], [class*="mgline"]').querySelector('img');
                        ads.push({
                            title: title,
                            landing: href,
                            image: img ? (img.src || img.dataset.src) : '',
                            network: "MGID"
                        });
                    }
                """)
                if js_ads:
                    print(f"✅ [MGID JS]: تم استخراج {len(js_ads)} إعلان من JavaScript!")
                    for ad in js_ads:
                        mgid_ads.append({**ad, "source": url, "network": "MGID"})
            except: pass

        # ✅ DOM Fallback: آخر محاولة - قراءة من الفريمات إذا لم ينجح API أو JS
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
                                # ✅ البحث أولاً عن الرابط الحقيقي في خصائص data-*
                                # وفك تشفير Base64 إذا كان موجوداً
                                real_href = await el.evaluate("""
                                    (a) => {
                                        // البحث عن data-url, data-href, data-link قبل ضرب رابط التتبع
                                        let realUrl = a.dataset.url || a.dataset.href || a.dataset.link ||
                                                      a.dataset.articleUrl || a.dataset.targetUrl ||
                                                      a.dataset.landing || a.dataset.dest ||
                                                      a.getAttribute('data-url') || a.getAttribute('data-href') ||
                                                      a.getAttribute('data-link') || a.getAttribute('data-article-url') ||
                                                      a.getAttribute('data-original-url') || a.getAttribute('data-landing');
                                        
                                        // فحص Base64 encoded URL (يبدأ بـ aHR0c...)
                                        if (realUrl && typeof realUrl === 'string') {
                                            if (realUrl.startsWith('aHR0c')) {
                                                try {
                                                    realUrl = atob(realUrl);
                                                } catch(e) {}
                                            }
                                            // تحقق أن الرابط الحقيقي وليس رابط تتبع
                                            if (realUrl.includes('clck.mgid.com') || realUrl.includes('clck.adskeeper')) {
                                                realUrl = null;
                                            }
                                        }
                                        
                                        if (realUrl && !realUrl.includes('clck.mgid.com') && !realUrl.includes('clck.adskeeper')) {
                                            return realUrl;
                                        }
                                        // فحص العنصر الأب والجدّ أيضاً
                                        let parent = a.closest('[data-url],[data-href],[data-article-url],[data-landing]');
                                        if (parent) {
                                            let pUrl = parent.dataset.url || parent.dataset.href || parent.dataset.articleUrl || parent.dataset.landing;
                                            if (pUrl && !pUrl.includes('clck.mgid.com')) return pUrl;
                                        }
                                        return a.href;  // الرابط كما هو (سيتم حل التحويلات لاحقاً في save_to_supabase)
                                    }
                                """)
                                landing = real_href or href
                                
                                image_url = ""
                                try:
                                    image_url = await el.evaluate("""
                                        (a) => {
                                            let img = a.querySelector('img');
                                            if (img && (img.src || img.dataset.src)) return img.src || img.dataset.src;
                                            let container = a.closest('.mgline, .mgbox, .mgid-widget, .mg-teaser, .image-with-text, [id^="mgid_"]');
                                            if (!container) container = a.parentElement;
                                            let cImg = container.querySelector('img');
                                            if (cImg && (cImg.src || cImg.dataset.src)) return cImg.src || cImg.dataset.src;
                                            let searchEls = [container, ...container.querySelectorAll('div, span, a, i')];
                                            for (let el of searchEls) {
                                                let style = window.getComputedStyle(el);
                                                let bg = style.backgroundImage;
                                                if (bg && bg !== 'none' && (bg.includes('http') || bg.includes('//'))) {
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
                                
                                mgid_ads.append({"title": title, "landing": landing, "image": image_url or "", "source": url, "network": "MGID"})
                except:
                    pass

        # --- معالجة وحفظ النتائج ---
        unique_ads = {}
=======
                });
                return ads;
            }
        """)
>>>>>>> f53831774e7965d169131f5d04dc00ec8225f164
        
        if dom_ads:
            print(f"✅ تم العثور على {len(dom_ads)} رابط حقيقي مباشرة من الـ HTML")
            mgid_ads.extend(dom_ads)

        # احتياطي: السكرول لتنشيط المزيد من الإعلانات
        await page.evaluate("window.scrollBy(0, 1000)")
        await asyncio.sleep(2)

        # معالجة وحفظ النتائج
        unique_ads = {}
        for ad in mgid_ads:
            key = ad['title'].lower()[:50] # مفتاح فريد بناءً على العنوان
            if key not in unique_ads:
                ad['source'] = url
                unique_ads[key] = ad
        
        for ad in unique_ads.values():
            await save_to_supabase(ad)

    except Exception as e:
        print(f"Error in {url}: {e}")
    finally:
        await page.close()
        await context.close()

async def run():
    async with async_playwright() as p:
        print(f"Starting Scraper for {TARGET_COUNTRY}...")
        browser = await p.chromium.launch(headless=True, proxy=PROXY_CONFIG)
        
        for target in MGID_TARGETS:
            await scrape_mgid(browser, target)
            await asyncio.sleep(random.uniform(2, 5))
            
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
