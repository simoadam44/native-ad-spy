import asyncio, os, random, sys, re
from urllib.parse import urlparse, parse_qs, unquote
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from supabase import create_client

# --- إعدادات سوبابيز ---
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None

# --- إعدادات الدولة والبروكسي ---
TARGET_COUNTRY = os.environ.get("TARGET_COUNTRY", "US")
PROXY_CONFIG = {
    "server": "http://gw.dataimpulse.com:823",
    "username": f"85ccde32f1cc6c7ad458__country-{TARGET_COUNTRY}",
    "password": "78c188c405598b8a"
}

# روابط المواقع المستهدفة
TARGET_URLS = [
    "https://pjmedia.com/vodkapundit/2026/03/23/are-you-ready-for-the-dems-2028-presidential-childhood-trauma-olympics-n4950953",
    "https://www.ibtimes.com/us-secured-secret-deal-cameroon-deport-migrants-using-aid-leverage-report-3800110",
    "https://brainberries.co/interesting/britney-spears-then-vs-now-her-changing-face-in-photos/",
    "https://herbeauty.co/ar/altarfih/maqati-video-raqs-zouk-lan-tastatia-at-tawaqquf-an-mushahadatiha-miraran-wa-takraran/",
    "https://buzzday.info/2026/02/13/what-happens-if-you-consume-ginger-every-day/?utm_id=57223822&utm_medium=cpc&utm_source=mgid.com&utm_campaign=buzzday_prt_en_mob&utm_term=57223822&utm_content=22902986",
    "https://zestradar.com/celebrities/the-worst-beckham-family-rumors-theyll-never-outrun/"
]

def decode_mgid_link(url):
    """فك تشفير روابط MGID لاستخراج الرابط الحقيقي للمعلن"""
    if not url or "mgid.com" not in url:
        return url
    try:
        parsed = urlparse(url)
        params = parse_qs(parsed.query)
        # mu و url و target هي البارامترات التي تحمل الرابط الحقيقي عادةً
        for p in ['mu', 'url', 'target', 'u', 'destination']:
            if p in params:
                decoded = unquote(params[p][0])
                if decoded.startswith('http'):
                    return decoded.split('?')[0].rstrip('/')
        
        # محاولة البحث عن رابط مشفر داخل النص إذا فشل parse_qs
        match = re.search(r'https%3A%2F%2F([^&]+)', url)
        if match:
            return unquote(match.group(0)).split('?')[0].rstrip('/')
    except: pass
    return url

async def save_to_db(ad):
    """حفظ الإعلان في سوبابيز مع تجنب التكرار"""
    if not supabase or not ad.get('landing'): return
    try:
        # تنظيف الرابط النهائي للتأكد من عدم التكرار
        clean_url = ad['landing'].split('?')[0].rstrip('/')
        res = supabase.table("ads").select("id").eq("landing", clean_url).execute()
        
        if not res.data:
            ad.update({
                "landing": clean_url,
                "country_code": TARGET_COUNTRY,
                "last_seen": "now()",
                "network": "MGID"
            })
            supabase.table("ads").insert(ad).execute()
            print(f"🎯 [NEW AD]: {ad['title'][:50]}...")
        else:
            # تحديث وقت المشاهدة فقط إذا كان موجوداً
            supabase.table("ads").update({"last_seen": "now()"}).eq("id", res.data[0]['id']).execute()
            print(f"🔄 [UPDATED]: {ad['title'][:50]}")
    except Exception as e:
        print(f"❌ DB Error: {e}")

async def scrape_site(browser, target_url):
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={'width': 1920, 'height': 1080}
    )
    page = await context.new_page()
    await Stealth().apply_stealth_async(page)
    
    ads_collected = []

    # 1. اعتراض الـ API (المنطق القديم الناجح)
    async def intercept_response(response):
        if "mgid.com" in response.url and response.status == 200:
            try:
                content = await response.json()
                items = content.get('items') or content.get('ads') or []
                for item in items:
                    raw_url = item.get('url') or item.get('articleUrl') or item.get('clickUrl')
                    title = item.get('title') or item.get('text')
                    if title and raw_url:
                        ads_collected.append({
                            "title": title.strip(),
                            "landing": decode_mgid_link(raw_url),
                            "source": target_url
                        })
            except: pass

    page.on("response", intercept_response)

    # حظر الصور والملفات الثقيلة لتسريع العمل وتوفير البيانات
    await page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff2}", lambda route: route.abort())

    try:
        print(f"🚀 Scanning: {target_url} ({TARGET_COUNTRY})")
        await page.goto(target_url, wait_until="domcontentloaded", timeout=60000)
        
        # سكرول لتنشيط ظهور الإعلانات
        for _ in range(3):
            await page.mouse.wheel(0, 1000)
            await asyncio.sleep(2)

        # 2. استخراج من الـ JavaScript (المنطق القديم الناجح)
        js_results = await page.evaluate("""() => {
            let found = [];
            for (let key of Object.keys(window)) {
                if (key.toLowerCase().includes('mgid')) {
                    let obj = window[key];
                    let items = obj.items || obj.ads || obj.data || [];
                    if (Array.isArray(items)) {
                        items.forEach(i => {
                            if (i.title) found.push({title: i.title, url: i.url || i.articleUrl || i.clickUrl});
                        });
                    }
                }
            }
            return found;
        }""")

        for ad in js_results:
            ads_collected.append({
                "title": ad['title'],
                "landing": decode_mgid_link(ad['url']),
                "source": target_url
            })

        # فلترة النتائج وحفظها
        if ads_collected:
            # إزالة التكرار داخل الدورة الواحدة
            unique_session = {a['title']: a for a in ads_collected}.values()
            for entry in unique_session:
                await save_to_db(entry)
        else:
            print(f"∅ No MGID ads found on: {target_url}")

    except Exception as e:
        print(f"⚠️ Skip {target_url} due to timeout/proxy issues.")
    finally:
        await page.close()
        await context.close()

async def main():
    async with async_playwright() as p:
        print(f"🛠️ Starting MGID Scraper for {TARGET_COUNTRY}...")
        browser = await p.chromium.launch(
            headless=True,
            proxy=PROXY_CONFIG,
            args=["--disable-web-security", "--no-sandbox"]
        )
        
        for url in TARGET_URLS:
            await scrape_site(browser, url)
            await asyncio.sleep(random.uniform(2, 5))
            
        await browser.close()
        print(f"✅ Finished scanning {TARGET_COUNTRY}")

if __name__ == "__main__":
    asyncio.run(main())
