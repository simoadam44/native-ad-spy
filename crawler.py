from urllib.parse import urljoin
from utils.url_resolver import resolve_url
from utils.advanced_detector import detect_from_chain

SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# تعريف بصمات الشبكات (روابط وحاويات)
NETWORKS = {
    "Taboola": {"pattern": r"taboola|trc\.taboola", "selector": "[id*='taboola'], .trc_spotlight_item"},
    "MGID": {"pattern": r"mgid\.com|servenobid", "selector": ".mg-item, [id*='mgid']"},
    "Outbrain": {"pattern": r"outbrain\.com", "selector": ".ob-widget-items-container"},
    "Revcontent": {"pattern": r"revcontent\.com", "selector": ".rc-item, [id*='rc-widget']"}
}

async def save_ad(data):
    try:
        # Resolve final URL for accurate detection (Affiliate/Tracker)
        final_url, redirect_chain = resolve_url(data['landing'])
        clean_landing = final_url.split('?')[0]
        
        check = supabase.table("ads").select("id").eq("landing", clean_landing).execute()
        if not check.data:
            # Detect intelligence from chain
            tracking_info = detect_from_chain(redirect_chain)
            
            data.update({
                "landing": clean_landing,
                "affiliate_network": tracking_info["affiliate_network"],
                "tracking_tool": tracking_info["tracking_tool"],
                "last_seen": "now()",
                "impressions": 1
            })
            
            supabase.table("ads").insert(data).execute()
            print(f"✅ [{data['network']}] [{tracking_info['affiliate_network']}]: {data['title'][:30]}")
    except Exception as e:
        print(f"⚠️ [Save Error]: {e}")

async def scrape_site(browser, url):
    page = await browser.new_page()
    try:
        # ⚡ تحديث: سنسمح بالـ JS ونحظر الصور والـ CSS فقط لتسريع التحميل دون كسر Taboola
        await page.route("**/*.{png,jpg,jpeg,gif,svg,css,woff2,ttf}", lambda route: route.abort())
        
        print(f"🚀 فحص عميق لـ: {url}")
        # ننتظر حتى domcontentloaded لضمان وجود الهيكل الأساسي
        await page.goto(url, timeout=50000, wait_until="domcontentloaded")
        
        # التمرير لأسفل الصفحة حيث تختبئ Taboola عادةً
        await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.5)")
        
        # ⏱️ سحر النجاح: الانتظار حتى تظهر أي حاوية إعلانية (حتى 10 ثوانٍ)
        try:
            combined_selectors = ",".join([v['selector'] for v in NETWORKS.values()])
            await page.wait_for_selector(combined_selectors, timeout=10000)
        except:
            print(f"⏳ لم تظهر حاويات الإعلانات بسرعة في {url}، سنحاول الصيد يدوياً...")

        content = await page.content()
        soup = BeautifulSoup(content, "html.parser")
        
        found = 0
        for a in soup.find_all("a", href=True):
            href = a['href'].lower()
            for net_name, config in NETWORKS.items():
                if re.search(config['pattern'], href):
                    img = a.find("img") or a.find_next("img")
                    title = a.get_text(strip=True) or (a.find_next("div").get_text(strip=True) if a.find_next("div") else "")
                    
                    if len(title) > 15:
                        img_url = img.get("src") or img.get("data-src") or img.get("data-lazy-src") or ""
                        await save_ad({
                            "title": title[:180],
                            "image": urljoin(url, img_url),
                            "landing": href,
                            "source": url,
                            "network": net_name
                        })
                        found += 1
                        break
        if found == 0: print(f"ℹ️ {url} لا يحتوي على ناتيف حالياً.")
    except: pass
    finally: await page.close()

async def main():
    res = supabase.table("target_sites").select("url").execute()
    sites = [r['url'] for r in res.data] if res.data else []
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # فحص المواقع بالتسلسل لضمان عدم تجاوز الـ Timeout بسبب ضغط الشبكة
        for site in sites:
            await scrape_site(browser, site)
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
