import asyncio, os, random, sys, re, json
from urllib.parse import urlparse, parse_qs, unquote
sys.stdout.reconfigure(encoding='utf-8')
from playwright.async_api import async_playwright
from playwright_stealth import Stealth
from supabase import create_client

# --- إعدادات سوبابيز ---
supabase_url = os.environ.get("SUPABASE_URL")
supabase_key = os.environ.get("SUPABASE_KEY")
supabase = create_client(supabase_url, supabase_key) if supabase_url and supabase_key else None

# --- إعدادات البروكسي والدولة ---
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
    """ استخراج الرابط الحقيقي من داخل روابط تتبع MGID """
    if not url: return None
    if "clck.mgid.com" in url or "mgid.com/mghits" in url:
        try:
            parsed = urlparse(url)
            params = parse_qs(parsed.query)
            # البحث عن بارامتر url أو target في الرابط المشفر
            potential_params = ['url', 'target', 'u', 'destination', 'mu']
            for p in potential_params:
                if p in params:
                    decoded = unquote(params[p][0])
                    if "http" in decoded: return decoded
        except: pass
    return url

async def save_to_supabase(ad):
    if not supabase or not ad.get('landing'): return
    try:
        # تنظيف الرابط للحفاظ على فرادة البيانات
        clean_url = ad['landing'].split('?')[0].rstrip('/')
        
        res = supabase.table("ads").select("id, impressions").eq("landing", clean_url).execute()
        if res.data:
            new_imp = (res.data[0].get('impressions') or 1) + 1
            supabase.table("ads").update({"impressions": new_imp, "last_seen": "now()"}).eq("id", res.data[0]['id']).execute()
            print(f"[MGID] 📈 Updated: {ad['title'][:40]}...")
        else:
            ad.update({"landing": clean_url, "impressions": 1, "last_seen": "now()", "country_code": TARGET_COUNTRY})
            supabase.table("ads").insert(ad).execute()
            print(f"[MGID] ✨ New Ad Captured: {ad['title'][:40]}...")
    except Exception as e:
        print(f"[DB ERROR]: {e}")

async def scrape_mgid(browser, target_url):
    context = await browser.new_context(
        viewport={'width': 1280, 'height': 1000},
        user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    )
    page = await context.new_page()
    await Stealth().apply_stealth_async(page)

    captured_ads = []

    # --- اعتراض الـ API اللحظي ---
    async def handle_response(response):
        if "mgid.com" in response.url.lower() and response.status == 200:
            try:
                data = await response.json()
                items = data.get('items') or data.get('ads') or data.get('data', [])
                for item in items:
                    raw_link = item.get('articleUrl') or item.get('targetUrl') or item.get('url')
                    real_link = extract_real_url(raw_link)
                    if real_link and "mgid.com" not in real_link:
                        captured_ads.append({
                            "title": item.get('title', 'No Title').strip(),
                            "landing": real_link,
                            "network": "MGID",
                            "source": target_url
                        })
            except: pass

    page.on("response", handle_response)

    try:
        print(f"🔍 Checking: {target_url}")
        # زيادة الـ Timeout وتغيير حالة الانتظار لضمان استقرار البروكسي
        await page.goto(target_url, wait_until="load", timeout=90000)
        
        # سكرول متكرر لضمان ظهور الـ Widgets أسفل المقال
        for _ in range(5):
            await page.evaluate("window.scrollBy(0, 1000)")
            await asyncio.sleep(2)

        # --- الحل الاحتياطي (DOM Scanning) - تم إصلاح الخطأ التقني هنا ---
        print(f"📡 Scanning DOM for extra MGID leads...")
        dom_results = await page.evaluate("""() => {
            let results = [];
            document.querySelectorAll('a[href*="mgid.com"]').forEach(el => {
                let title = el.innerText.trim();
                if (title.length > 8) { 
                    results.push({title: title, landing: el.href}); // تم تغيير append إلى push
                }
            });
            return results;
        }""")
        
        for item in dom_results:
            real = extract_real_url(item['landing'])
            if real and "mgid.com" not in real:
                captured_ads.append({**item, "landing": real, "network": "MGID", "source": target_url})

        # فلترة النتائج المتكررة وحفظها
        if captured_ads:
            unique_ads = {ad['landing']: ad for ad in captured_ads}.values()
            for ad in unique_ads:
                await save_to_supabase(ad)
        else:
            print(f"⚠️ No MGID ads found on this page (Country: {TARGET_COUNTRY})")

    except Exception as e:
        print(f"❌ Critical Error on {target_url}: {e}")
    finally:
        await page.close()
        await context.close()

async def run():
    async with async_playwright() as p:
        # إضافة خيار تجاوز أخطاء الشهادات لزيادة استقرار البروكسي
        browser = await p.chromium.launch(headless=True, proxy=PROXY_CONFIG, args=["--ignore-certificate-errors"])
        for target in TARGET_URLS:
            await scrape_mgid(browser, target)
            await asyncio.sleep(random.uniform(3, 7))
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run())
