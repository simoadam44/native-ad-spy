import asyncio, os, random
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from supabase import create_client

# إعداد سوبابيز
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# ✅ تنظيف الروابط وتوسيع قائمة الأهداف لضمان نتائج أفضل
MGID_TARGETS = [url.strip() for url in [
    "https://www.newsweek.com/world",
    "https://www.standard.co.uk/news",
    "https://www.ibtimes.com/",
    "https://www.thegatewaypundit.com/",
    "https://www.mirror.co.uk/news/"
]]

async def save_to_supabase(ad):
    try:
        if not ad.get('title') or not ad.get('landing'): return
        clean_url = ad['landing'].split('?')[0]
        res = supabase.table("ads").select("id, impressions").eq("landing", clean_url).execute()
        
        if res.data:
            new_imp = (res.data[0].get('impressions') or 1) + 1
            supabase.table("ads").update({"impressions": new_imp, "last_seen": "now()"}).eq("id", res.data[0]['id']).execute()
            print(f"📈 [MGID]: تحديث ({new_imp}): {ad['title'][:40]}...")
        else:
            ad.update({"landing": clean_url, "impressions": 1, "last_seen": "now()"})
            supabase.table("ads").insert(ad).execute()
            print(f"✨ [MGID]: صيد جديد: {ad['title'][:40]}...")
    except Exception as e:
        print(f"⚠️ [DB ERROR]: {e}")

async def scrape_mgid(browser, url):
    mgid_ads = []
    # ✅ استخدام المتصفح الحقيقي للتهرب من الحظر (CDP)
    if browser.contexts:
        context = browser.contexts[0]
    else:
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
            locale="en-US",
            timezone_id="America/New_York",
            permissions=["geolocation"]
        )
    
    page = await context.new_page()
    
    # لا نحتاج Stealth إذا كنا نستخدم المتصفح الحقيقي، لكن نطبقه كإجراء احترازي إذا كان سياقاً جديداً
    if not browser.contexts:
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
        print(f"🚀 [MGID]: فحص الهدف: {url}")
        # ✅ استخدام domcontentloaded بدلاً من networkidle لتجنب التعليق
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        
        # انتظار يدوي لضمان تحميل الـ Widgets
        await asyncio.sleep(8)
        for i in range(5):
            await page.evaluate(f"window.scrollBy(0, {800 + (i * 100)})")
            await asyncio.sleep(2)

        # ✅ Fallback: محاولة قراءة الإعلانات من DOM في كل الفريمات (iframes)
        if not mgid_ads:
            for frame in page.frames:
                try:
                    dom_ads = await frame.evaluate("""
                        () => {
                            let found = [];
                            document.querySelectorAll('.mgline a, .mgbox a, [id^="mgid_"] a, .mgid-widget a').forEach(el => {
                                let title = el.innerText.trim();
                                let href = el.href;
                                if (title.length > 15 && href && href.startsWith('http')) {
                                    found.push({title, landing: href});
                                }
                            });
                            return found;
                        }
                    """)
                    for ad in dom_ads:
                        mgid_ads.append({**ad, "image": "", "source": url, "network": "MGID"})
                except:
                    pass

        if mgid_ads:
            unique_ads = {}
            for ad in mgid_ads:
                if ad['landing'] and ad['title'] and ad['landing'] not in unique_ads:
                    unique_ads[ad['landing']] = ad
            
            for ad in unique_ads.values():
                await save_to_supabase(ad)
            print(f"✅ [MGID]: صيد {len(unique_ads)} إعلان بنجاح في {url}")
        else:
            print(f"ℹ️ [MGID]: لم يتم رصد إعلانات في {url}")

    except Exception as e:
        print(f"⚠️ [MGID ERROR]: {e}")
    finally:
        await page.close()
        await context.close()

async def run():
    async with async_playwright() as p:
        # ✅ تقنية CDP: الاتصال بمتصفح جوجل كروم الحقيقي المفتوح حالياً على جهازك
        try:
            browser = await p.chromium.connect_over_cdp("http://localhost:9222")
        except Exception as e:
            print("❌ تعذر الاتصال بكروم. تأكد من إغلاق كروم بالكامل وفتحه بوضع الـ Debugging (راجع التعليمات).")
            return
            
        for target in MGID_TARGETS:
            try:
                await scrape_mgid(browser, target)
            except: pass
            await asyncio.sleep(random.uniform(3, 7))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
