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

def extract_real_url(url):
    if not url: return None
    # فك التشفير العميق لروابط MGID
    if "mgid.com" in url:
        try:
            params = parse_qs(urlparse(url).query)
            for p in ['url', 'target', 'u', 'mu', 'd']:
                if p in params:
                    potential = unquote(params[p][0])
                    if "http" in potential and "mgid.com" not in potential:
                        return potential
        except: pass
    return url if "mgid.com" not in url else None

async def scrape_mgid(browser, target_url):
    # استخدام User-Agent أكثر حداثة لمحاكاة مستخدم حقيقي
    context = await browser.new_context(
        user_agent="Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        viewport={'width': 1920, 'height': 1080}
    )
    page = await context.new_page()
    await Stealth().apply_stealth_async(page)
    
    ads = []

    # مراقبة الـ API (الطريقة الأسرع)
    page.on("response", lambda res: asyncio.create_task(handle_api_response(res, ads, target_url)))

    try:
        print(f"🚀 Investigating: {target_url} ({TARGET_COUNTRY})")
        # تقليل وقت الانتظار لـ 45 ثانية لتجنب تعليق الدورة بالكامل
        await page.goto(target_url, wait_until="domcontentloaded", timeout=45000)
        
        # سكرول "إنساني" متقطع
        for _ in range(6):
            await page.mouse.wheel(0, 800)
            await asyncio.sleep(1.5)

        # استخراج نهائي من الـ DOM (إصلاح شامل للـ JS)
        dom_ads = await page.evaluate("""() => {
            let found = [];
            // البحث في كل الروابط التي تحتوي على تتبع MGID أو كلاسات مشبوهة
            document.querySelectorAll('a[href*="mgid.com"], .mgid-ad, [id*="mgid"]').forEach(el => {
                let link = el.href || '';
                let title = el.innerText.trim() || el.getAttribute('title') || '';
                if (link.includes('mgid.com') && title.length > 5) {
                    found.push({title: title, landing: link});
                }
            });
            return found;
        }""")

        for ad in dom_ads:
            real = extract_real_url(ad['landing'])
            if real: ads.append({**ad, "landing": real, "network": "MGID", "source": target_url})

        # حفظ النتائج
        if ads:
            unique = {a['landing']: a for a in ads}.values()
            for a in unique:
                await save_to_db(a)
        else:
            print(f"∅ No ads on {target_url}")

    except Exception as e:
        print(f"⚠️ Skip {target_url} due to connection issues.")
    finally:
        await page.close()
        await context.close()

async def handle_api_response(res, ads_list, source):
    if "mgid.com" in res.url and res.status == 200:
        try:
            data = await res.json()
            items = data.get('items') or data.get('ads') or []
            for i in items:
                link = extract_real_url(i.get('url') or i.get('articleUrl'))
                if link:
                    ads_list.append({"title": i.get('title', ''), "landing": link, "network": "MGID", "source": source})
        except: pass

async def save_to_db(ad):
    if not supabase: return
    try:
        clean = ad['landing'].split('?')[0].rstrip('/')
        res = supabase.table("ads").select("id").eq("landing", clean).execute()
        if not res.data:
            ad.update({"landing": clean, "country_code": TARGET_COUNTRY, "last_seen": "now()"})
            supabase.table("ads").insert(ad).execute()
            print(f"🎯 SAVED: {ad['title'][:40]}")
    except: pass

async def run():
    async with async_playwright() as p:
        # تشغيل المتصفح مع تجاهل أخطاء البروكسي والشهادات
        browser = await p.chromium.launch(headless=True, proxy=PROXY_CONFIG, args=["--disable-web-security"])
        for url in TARGET_URLS:
            await scrape_mgid(browser, url)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
