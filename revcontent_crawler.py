import asyncio
from playwright.async_api import async_playwright
from bs4 import BeautifulSoup
from supabase import create_client
from urllib.parse import urljoin
import os
import re

# --- 1. الإعدادات والاتصال الآمن ---
SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://avxoumymzbioeabxfcca.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# محددات Revcontent المتطورة
REV_SELECTORS = [
    ".rc-item", ".rc-ad-container", 
    "[id*='rc-widget']", "div[data-rc-widget]", 
    ".revcontent-ad", ".rc-row"
]

async def save_or_update_ad(data):
    try:
        # تنظيف رابط الهبوط من الـ Tracking لضمان دقة الإحصائيات
        clean_landing = data['landing'].split('?')[0].split('#')[0]
        data["landing"] = clean_landing
        
        existing = supabase.table("ads").select("id, impressions").eq("landing", clean_landing).execute()
        
        if existing.data:
            new_count = (existing.data[0].get('impressions') or 1) + 1
            supabase.table("ads").update({
                "impressions": new_count,
                "last_seen": "now()"
            }).eq("id", existing.data[0]['id']).execute()
            print(f"📈 [REVCONTENT]: تحديث ({new_count}): {data['title'][:50]}...")
        else:
            data.update({"impressions": 1, "last_seen": "now()"})
            supabase.table("ads").insert(data).execute()
            print(f"✨ [REVCONTENT]: صيد جديد: {data['title'][:50]}...")
    except Exception as e:
        print(f"⚠️ خطأ Supabase: {str(e)[:50]}")

async def scrape_revcontent(browser, url, semaphore):
    async with semaphore:
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36"
        )
        page = await context.new_page()
        
        # ✅ السماح بالصور وحظر العناصر الثقيلة فقط (فيديو/خطوط)
        await page.route("**/*.{woff,woff2,ttf,mp4,webm}", lambda route: route.abort())
        
        try:
            print(f"🚀 [REVCONTENT]: فحص الهدف: {url}")
            await page.goto(url, timeout=45000, wait_until="domcontentloaded")
            
            # تمرير الصفحة للوصول لإعلانات Revcontent (غالباً في المنتصف أو النهاية)
            await page.evaluate("window.scrollTo(0, document.body.scrollHeight * 0.6)")
            await asyncio.sleep(5)
            
            content = await page.content()
            soup = BeautifulSoup(content, "html.parser")
            
            # البحث عن روابط Click المباشرة لـ Revcontent أولاً
            links = soup.select("a[href*='revcontent.com/click']")
            
            if not links:
                for selector in REV_SELECTORS:
                    for el in soup.select(selector):
                        a_tag = el.find("a", href=True)
                        if a_tag: links.append(a_tag)

            found_any = False
            for a in links:
                try:
                    # ✅ استخراج العنوان الحقيقي والنظيف بالكامل
                    title_el = (
                        a.find(class_=lambda c: c and 'title' in c.lower()) or 
                        a.find("h3") or a.find("h4") or a.find("span")
                    )
                    
                    title = title_el.get_text(strip=True) if title_el else a.get_text(strip=True)
                    
                    # محاولة إضافية إذا كان العنوان في حاوية الأب
                    if not title or len(title) < 10:
                        parent = a.find_parent()
                        if parent:
                            title_el2 = parent.select_one(".rc-title, .title, h3, h4")
                            if title_el2: title = title_el2.get_text(strip=True)
                    
                    title = " ".join(title.split())
                    if not title or len(title) < 10: continue

                    # استخراج الصورة
                    img = a.find("img") or a.find_next("img")
                    img_url = ""
                    if img:
                        img_url = img.get("src") or img.get("data-src") or ""

                    await save_or_update_ad({
                        "title": title, # ✅ الآن كامل بدون قطع
                        "image": urljoin(url, img_url) if img_url else "",
                        "landing": urljoin(url, a['href']),
                        "source": url,
                        "network": "Revcontent"
                    })
                    found_any = True
                except: continue
                
            if not found_any:
                print(f"ℹ️ [REVCONTENT]: لم يتم رصد إعلانات في {url}")
                
        except Exception as e:
            print(f"⚠️ تجاوز {url}: {str(e)[:50]}")
        finally:
            await page.close()
            await context.close()

async def run_spy():
    try:
        response = supabase.table("target_sites").select("url").execute()
        sites = [row['url'] for row in response.data] if response.data else []
    except:
        sites = []

    if not sites:
        print("ℹ️ قاعدة البيانات فارغة، بانتظار عمل Finder...")
        return

    semaphore = asyncio.Semaphore(2) # معالجة موقعين في نفس الوقت
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        await asyncio.gather(*[scrape_revcontent(browser, s, semaphore) for s in sites])
        await browser.close()

if __name__ == "__main__":
    asyncio.run(run_spy())
