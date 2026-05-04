import json
import requests
from Wappalyzer import Wappalyzer, WebPage
import re

class TechAnalyzer:
    def __init__(self):
        try:
            # نحاول تحميل أحدث القواعد
            self.wappalyzer = Wappalyzer.latest()
        except:
            # إذا فشل، نستخدم النسخة الافتراضية
            self.wappalyzer = Wappalyzer.latest(update=False)
            
        # إضافة بصمات مخصصة لأدوات الأفلييت (Tracking Tools) التي قد لا توجد في Wappalyzer
        self.custom_trackers = {
            "RedTrack": [r"rdtk\.io", r"redtrack\.io"],
            "Binom": [r"binom\.org", r"click\.php\?key="],
            "Voluum": [r"voluum\.com", r"vltrack\.net"],
            "BeMob": [r"bemob\.com", r"bemobtrck\.com"],
            "Keitaro": [r"keitaro\.io", r"kclick\.io"],
            "Affise": [r"affise\.com", r"affise\.js"],
            "Cake": [r"cakemarketing\.com", r"getcake\.com"],
            "AnyTrack": [r"anytrack\.io"],
            "Everflow": [r"everflow\.io"]
        }

    def analyze(self, url, html_content=None, headers=None):
        """
        تحليل شامل للتقنيات المستخدمة في الصفحة.
        """
        results = {
            "technologies": [],
            "tracking_software": [],
            "cms": None,
            "is_wordpress": False,
            "affiliate_platform": None
        }

        try:
            # 1. تحليل Wappalyzer
            if html_content:
                webpage = WebPage(url, html_content, headers or {})
            else:
                webpage = WebPage.new_from_url(url, timeout=10)
            
            tech_results = self.wappalyzer.analyze_with_categories(webpage)
            
            for tech, categories in tech_results.items():
                results["technologies"].append(tech)
                
                # تصنيف التقنيات المهمة لنا
                cat_list = [c.lower() for c in categories]
                if "cms" in cat_list:
                    results["cms"] = tech
                    if tech.lower() == "wordpress":
                        results["is_wordpress"] = True
                
                if "analytics" in cat_list or "tracking" in cat_list:
                    results["tracking_software"].append(tech)

            # 2. فحص يدوي للمقتنيات المخصصة (Custom Tracking Detection)
            content_to_check = html_content or ""
            if not content_to_check and not html_content:
                # إذا لم يتم توفير HTML، نحاول جلب أول 5000 حرف لتسريع الفحص
                try:
                    r = requests.get(url, timeout=5, headers={"User-Agent": "Mozilla/5.0"})
                    content_to_check = r.text
                except: pass

            for tracker, patterns in self.custom_trackers.items():
                if tracker in results["tracking_software"]: continue
                
                for pattern in patterns:
                    if re.search(pattern, content_to_check, re.IGNORECASE):
                        results["tracking_software"].append(tracker)
                        break

            # تنظيف النتائج
            results["tracking_software"] = list(set(results["tracking_software"]))
            results["technologies"] = list(set(results["technologies"]))

            return results
        except Exception as e:
            print(f"⚠️ [TechAnalyzer Error]: {e}")
            return results

# نسخة سريعة للاستخدام المباشر
def get_site_tech(url, html=None):
    analyzer = TechAnalyzer()
    return analyzer.analyze(url, html_content=html)
