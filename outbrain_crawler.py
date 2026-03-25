import asyncio, os, random, sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from supabase import create_client

# إعداد سوبابيز
supabase = create_client(os.environ.get("SUPABASE_URL"), os.environ.get("SUPABASE_KEY"))

# ✅ تنظيف الروابط وتوسيع قائمة الأهداف لضمان نتائج أفضل
OUTBRAIN_TARGETS = [url.strip() for url in [
    "https://www.dailymail.co.uk/news/index.html",
    "https://www.9news.com.au/",
    "https://www.skynewsarabia.com/technology",
    "https://www.foxnews.com/world",
    "https://edition.cnn.com/world"
]]

async def save_to_supabase(ad):
    try:
        if not ad.get('title') or not ad.get('landing'): return
        # تنظيف رابط Outbrain من معاملات التتبع المتغيرة لتقليل التكرار
        clean_url = ad['landing'].split('&dicbo=')[0] if '&dicbo=' in ad['landing'] else ad['landing']
        res = supabase.table("ads").select("id, impressions").eq("landing", clean_url).execute()
        
        if res.data:
            new_imp = (res.data[0].get('impressions') or 1) + 1
            supabase.table("ads").update({"impressions": new_imp, "last_seen": "now()"}).eq("id", res.data[0]['id']).execute()
            print(f"📈 [OUTBRAIN]: تحديث ({new_imp}): {ad['title'][:40]}...")
        else:
            ad.update({"landing": clean_url, "impressions": 1, "last_seen": "now()"})
            supabase.table("ads").insert(ad).execute()
            print(f"✨ [OUTBRAIN]: صيد جديد: {ad['title'][:40]}...")
    except Exception as e:
        print(f"⚠️ [DB ERROR]: {e}")

async def scrape_outbrain(browser, url):
    outbrain_ads = []
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
    
    # تطبيق التخفي (Stealth) كإجراء احترازي دائم
    from playwright_stealth import stealth_async
    await stealth_async(page)

    # اعتراض استجابات API بشكل موسع
    async def handle_response(response):
        nonlocal outbrain_ads
        url_lower = response.url.lower()
        if "outbrain.com" in url_lower and response.status == 200:
            try:
                content_type = response.headers.get("content-type", "")
                if "application/json" in content_type or "text/javascript" in content_type:
                    data = await response.json()
                    # Outbrain often uses 'documents' or 'doc.ads' or 'cards'
                    if isinstance(data, dict):
                        listings = (
                            data.get('documents') or 
                            data.get('doc', {}).get('ads', []) or 
                            data.get('cards', []) or 
                            data.get('items', [])
                        )
                    elif isinstance(data, list):
                        listings = data
                    else:
                        listings = []
                    
                    for item in listings:
                        title = item.get('content') or item.get('title') or item.get('text')
                        link = item.get('url') or item.get('clickUrl') or item.get('link')
                        if title and link:
                            outbrain_ads.append({
                                "title": str(title).strip(),
                                "landing": link,
                                "image": (item.get('image', {}) if isinstance(item.get('image'), dict) else {}).get('url') or item.get('thumbnail', ''),
                                "source": url,
                                "network": "OUTBRAIN"
                            })
            except: pass

    page.on("response", handle_response)

    try:
        print(f"🚀 [OUTBRAIN]: فحص الهدف: {url}")
        # استخدام domcontentloaded بدلاً من networkidle
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        
        # انتظار يدوي
        await asyncio.sleep(8)
        try:
            await page.wait_for_selector('[data-ob-widget], .OUTBRAIN, #outbrain', timeout=15000)
        except: pass

        # تمرير الصفحة ببطء للسماح بتحميل الإعلانات
        await asyncio.sleep(30)
        for i in range(8):
            await page.evaluate(f"window.scrollBy(0, {800 + (i * 200)})")
            await asyncio.sleep(2)

        # ✅ Fallback المطور من الكود ومتقاطع مع الإطارات (iframes)
        if not outbrain_ads:
            for frame in page.frames:
                try:
                    dom_ads = await frame.evaluate("""
                        () => {
                            let found = [];
                            document.querySelectorAll('a[data-ob-url], .ob-dynamic-rec-container a, .ob-widget-items-container a, .OUTBRAIN a').forEach(el => {
                                let title = el.innerText.trim();
                                let href = el.getAttribute('data-ob-url') || el.href;
                                let src = el.querySelector('img') ? el.querySelector('img').src : '';
                                if (title.length > 15 && href && href.startsWith('http')) {
                                    found.push({title, landing: href, image: src});
                                }
                            });
                            return found;
                        }
                    """)
                    for ad in dom_ads:
                        outbrain_ads.append({**ad, "source": url, "network": "OUTBRAIN"})
                except:
                    pass

        if outbrain_ads:
            unique_ads = {}
            for ad in outbrain_ads:
                if ad['landing'] and ad['title'] and ad['landing'] not in unique_ads:
                    unique_ads[ad['landing']] = ad
            
            for ad in unique_ads.values():
                await save_to_supabase(ad)
            print(f"✅ [OUTBRAIN]: تم صيد {len(unique_ads)} إعلان في {url}")
        else:
            print(f"ℹ️ [OUTBRAIN]: لم يتم رصد إعلانات في {url}")

    except Exception as e:
        print(f"⚠️ [OUTBRAIN ERROR]: {e}")
    finally:
        await page.close()
        await context.close()

async def run():
    async with async_playwright() as p:
        # تشغيل متصفح مستقل (Launch) بدلاً من الاتصال (Connect) بناءً على طلبك
        try:
            print("Launching independent Chrome browser...")
            browser = await p.chromium.launch(headless=True)
            
            # إعداد السياق مع تقنيات التخفي
            context = await browser.new_context(
                user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
            )
            
            # تطبيق التخفي (Stealth)
            from playwright_stealth import stealth_async
            page = await context.new_page()
            await stealth_async(page)
            
            for target in OUTBRAIN_TARGETS:
                print(f"Checking target: {target}")
                try:
                    await scrape_outbrain(browser, target)
                except: pass
                await asyncio.sleep(random.uniform(3, 7))
                
        except Exception as e:
            print(f"Error launching browser: {e}")
        finally:
            if 'browser' in locals():
                await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
