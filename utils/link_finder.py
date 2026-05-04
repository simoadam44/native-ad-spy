import re
import requests
import asyncio
from urllib.parse import urljoin, urlparse

# المستخلص الرئيسي للروابط (LinkFinder Regex)
LINK_REGEX = r"""
  (?:"|')                               # بداية علامة الاقتباس
  (
    ((?:[a-zA-Z]{1,10}://|//)           # بروتوكول كامل أو //
    [^"'/]{1,}\.[a-zA-Z]{2,}[^"']{0,})  # الدومين والمسار
    |
    ((?:/|\.\./|\./)                    # مسارات نسبية
    [^"'><,;| *()(%$\^! \t\r\n]
    [^"'><,;|()(%$\^! \t\r\n]{0,})
    |
    ([a-zA-Z0-9_\-/]{1,}/               # مسارات برمجية مع امتدادات
    [a-zA-Z0-9_\-/]{1,}\.(?:[a-zA-Z]{1,4}|action)
    (?:[\?|#][^"']{0,}|))
    |
    ([a-zA-Z0-9_\-/]{1,}/               # مسارات برمجية طويلة
    [a-zA-Z0-9_\-/]{3,}
    (?:[\?|#][^"']{0,}|))
    |
    ([a-zA-Z0-9_\-]{1,}\.               # ملفات حساسة
    (?:php|asp|aspx|jsp|json|action|html|js|txt|xml)
    (?:[\?|#][^"']{0,}|))
  )
  (?:"|')                               # نهاية علامة الاقتباس
"""

class LinkFinder:
    def __init__(self):
        self.regex = re.compile(LINK_REGEX, re.VERBOSE)

    def extract_from_text(self, text, base_url=None):
        """يستخرج جميع الروابط من نص (غالباً ملف JS أو HTML)"""
        if not text: return []
        
        links = []
        matches = self.regex.finditer(text)
        for match in matches:
            link = match.group(1)
            if base_url:
                # تحويل الروابط النسبية إلى كاملة
                full_link = urljoin(base_url, link)
                links.append(full_link)
            else:
                links.append(link)
        
        return list(set(links))

    async def analyze_page_scripts(self, page, base_url):
        """يقوم بتحميل وفحص جميع ملفات الـ JS المرتبطة بالصفحة"""
        print(f"  [LinkFinder] Extracting hidden links from JS files...", flush=True)
        
        # 1. الحصول على جميع روابط السكربتات في الصفحة
        script_urls = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('script[src]')).map(s => s.src);
        }""")
        
        # 2. إضافة السكربتات المضمنة (Inline Scripts)
        inline_scripts = await page.evaluate("""() => {
            return Array.from(document.querySelectorAll('script:not([src])')).map(s => s.textContent);
        }""")
        
        found_links = []
        
        # فحص السكربتات المضمنة أولاً
        for script in inline_scripts:
            found_links.extend(self.extract_from_text(script, base_url))
            
        # فحص الملفات الخارجية (بحد أقصى 10 ملفات لتجنب البطء)
        import aiohttp
        async with aiohttp.ClientSession() as session:
            tasks = []
            for url in script_urls[:10]:
                if not url.startswith('http'): continue
                tasks.append(self._fetch_and_extract(session, url))
            
            if tasks:
                results = await asyncio.gather(*tasks)
                for res in results:
                    found_links.extend(res)
                    
        return list(set(found_links))

    async def _fetch_and_extract(self, session, url):
        try:
            async with session.get(url, timeout=5) as response:
                if response.status == 200:
                    text = await response.text()
                    return self.extract_from_text(text, url)
        except:
            pass
        return []

# دالة مساعدة لاكتشاف العروض المخفية
def filter_potential_offers(links):
    """يفلتر الروابط المستخرجة للبحث عن روابط عروض (Affiliate Offers)"""
    OFFER_KEYWORDS = [
        'click', 'track', 'offer', 'go.php', 'out', 'redirect', 
        'aff', 'checkout', 'buy', 'order', 'cart', 'product'
    ]
    
    potential = []
    for link in links:
        link_lower = link.lower()
        if any(key in link_lower for key in OFFER_KEYWORDS):
            potential.append(link)
            
    return potential
