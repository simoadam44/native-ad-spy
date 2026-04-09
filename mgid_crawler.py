import asyncio, os, random, sys
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from supabase import create_client

# --- إعدادات سوبابيز ---
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None

TARGET_COUNTRY = os.environ.get("TARGET_COUNTRY", "US")
PROXY_CONFIG = {
    "server": "http://gw.dataimpulse.com:823",
    "username": f"85ccde32f1cc6c7ad458__country-{TARGET_COUNTRY}",
    "password": "78c188c405598b8a"
}

TARGET_URLS = [
    "https://pjmedia.com/vodkapundit/2026/03/23/are-you-ready-for-the-dems-2028-presidential-childhood-trauma-olympics-n4950953",
    "https://www.ibtimes.com/us-secured-secret-deal-cameroon-deport-migrants-using-aid-leverage-report-3800110",
    "https://brainberries.co/interesting/britney-spears-then-vs-now-her-changing-face-in-photos/",
    "https://herbeauty.co/ar/altarfih/maqati-video-raqs-zouk-lan-tastatia-at-tawaqquf-an-mushahadatiha-miraran-wa-takraran/",
    "https://buzzday.info/2026/02/13/what-happens-if-you-consume-ginger-every-day/?utm_id=57223822&utm_medium=cpc&utm_source=mgid.com&utm_campaign=buzzday_prt_en_mob&utm_term=57223822&utm_content=22902986",
    "https://zestradar.com/celebrities/the-worst-beckham-family-rumors-theyll-never-outrun/"
]

async def save_to_supabase(ad):
    if not supabase: return
    try:
        # تنظيف الرابط من أي Tracking ID بسيط لإيجاد الأصل
        clean_url = ad['landing'].split('?')[0] if '?' in ad['landing'] else ad['landing']
        
        res = supabase.table("ads").select("id, impressions").eq("landing", clean_url).execute()
        if res.data:
            new_imp = (res.data[0].get('impressions') or 1) + 1
            supabase.table("ads").update({"impressions": new_imp, "last_seen": "now()"}).eq("id", res.data[0]['id']).execute()
            print(f"[MGID] Updated: {ad['title'][:40]}...")
        else:
            ad.update({"landing": clean_url, "impressions": 1, "last_seen": "now()", "country_code": TARGET_COUNTRY})
            supabase.table("ads").insert(ad).execute()
            print(f"[MGID] New Capture: {ad['title'][:40]}...")
    except Exception as e:
        print(f"[DB ERROR]: {e}")

async def scrape_mgid_real_links(browser, url):
    context = await browser.new_context(viewport={'width': 1280, 'height': 800})
    page = await context.new_page()
    await Stealth().apply_stealth_async(page)

    captured_ads = []

    # اعتراض الشبكة لاستخراج الروابط قبل التشفير أو التتبع
    async def handle_response(response):
        if "mgid.com" in response.url and response.status == 200:
            try:
                data = await response.json()
                # MGID تضع البيانات عادة في قائمة 'items'
                items = data.get('items') or data.get('ads') or []
                
                for item in items:
                    # الروابط الحقيقية في MGID تظهر في هذه الحقول داخل الـ JSON
                    real_url = (
                        item.get('articleUrl') or   # الرابط الأصلي للمقال (الأكثر دقة)
                        item.get('targetUrl') or    # الرابط المستهدف
                        item.get('originalUrl') or 
                        item.get('url')             # إذا كان JSON سكرابينج خام
                    )
                    
                    if real_url and not "clck.mgid.com" in real_url:
                        ad_data = {
                            "title": item.get('title', '').strip(),
                            "landing": real_url,
                            "image": item.get('mainImage') or item.get('thumbnail', ''),
                            "network": "MGID",
                            "source": url
                        }
                        if ad_data["title"] and ad_data["landing"]:
                            captured_ads.append(ad_data)
            except:
                pass

    page.on("response", handle_response)

    # حظر الصور والموارد لتسريع العملية وتوفير البيانات
    await page.route("**/*.{png,jpg,jpeg,gif,css,woff2}", lambda route: route.abort())

    try:
        print(f"Checking: {url}")
        await page.goto(url, wait_until="domcontentloaded", timeout=45000)
        
        # سكرول لأسفل لتفعيل لود الـ Widgets
        for _ in range(3):
            await page.evaluate("window.scrollBy(0, 1000)")
            await asyncio.sleep(2)

        # فلترة النتائج المتكررة وحفظها
        unique_ads = {ad['title']: ad for ad in captured_ads}.values()
        for ad in unique_ads:
            await save_to_supabase(ad)
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        await page.close()
        await context.close()

async def run():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True, proxy=PROXY_CONFIG)
        for target in TARGET_URLS:
            await scrape_mgid_real_links(browser, target)
            await asyncio.sleep(random.uniform(3, 6))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
