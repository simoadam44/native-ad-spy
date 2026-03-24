import asyncio
from playwright.async_api import async_playwright
from supabase import create_client
import os

# إعدادات Supabase من البيئة (GitHub Secrets)
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# المصادر "المرنة" التي لا تحجب GitHub وتحتوي على ناتيف بكثافة
SOURCES = [
    "https://joehoft.com/",
    "https://protrumpnews.com/",
    "https://gatewayhispanic.com/category/noticias/",
    "https://www.thegatewaypundit.com/",
    "https://www.breitbart.com/",
    "https://www.thewrap.com/celebrity-news/"
]

# قائمة سوداء لمنع المواقع التقنية وغير المفيدة
BLACKLIST = [
    'google', 'facebook', 'twitter', 'instagram', 'youtube', 'whatsapp', 
    'amazon', 'apple', 'microsoft', 'netflix', 'spotify', 'pinterest',
    'histats', 'tgpvideo', 'sellwild', 'worldstar', 'mailsubscriptions'
]

async def is_native_site(page, url):
    """التحقق من وجود بصمات شبكات الناتيف في كود الصفحة"""
    try:
        content = await page.content()
        indicators = ["taboola", "outbrain", "mgid", "revcontent", "zemanta"]
        return any(i in content.lower() for i in indicators)
    except:
        return False

async def find_new_targets():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        # استخدام User-Agent حديث للتمويه
        context = await browser.new_context(
            user_agent="Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"
        )
        
        print(f"🚀 بدء جولة البحث عن أهداف جديدة...")
        
        for source in SOURCES:
            page = await context.new_page()
            try:
                print(f"🌐 فحص المصدر: {source}")
                await page.goto(source, timeout=30000, wait_until="domcontentloaded")
                
                # استخراج الروابط الخارجية (المقالات)
                links = await page.evaluate('''() => {
                    return Array.from(document.querySelectorAll('a'))
                        .map(a => a.href)
                        .filter(href => href.startsWith('http'));
                }''')
                
                # نأخذ عينة من 8 روابط فقط لسرعة التنفيذ
                potential_links = [l for l in set(links) if not any(b in l.lower() for b in BLACKLIST)][:8]
                
                for link in potential_links:
                    test_page = await context.new_page()
                    try:
                        # مهلة 12 ثانية فقط للفحص
                        await test_page.goto(link, timeout=12000, wait_until="commit")
                        if await is_native_site(test_page, link):
                            # استخراج الدومين الرئيسي فقط
                            clean_url = "/".join(link.split("/")[:3]) + "/"
                            # حفظ في قاعدة البيانات
                            supabase.table("target_sites").insert({"url": clean_url}).execute()
                            print(f"✅ هدف جديد مكتشف: {clean_url}")
                    except:
                        pass
                    finally:
                        await test_page.close()
                        
            except Exception as e:
                print(f"⚠️ تجاوز المصدر {source} بسبب بطء الاستجابة")
            finally:
                await page.close()
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(find_new_targets())
