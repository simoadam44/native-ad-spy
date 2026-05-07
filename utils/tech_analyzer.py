import json
import requests
try:
    from Wappalyzer import Wappalyzer, WebPage
    WAPPALYZER_AVAILABLE = True
except ImportError:
    WAPPALYZER_AVAILABLE = False
import re

class TechAnalyzer:
    def __init__(self):
        self.wappalyzer = None
        if WAPPALYZER_AVAILABLE:
            try:
                # نحاول تحميل أحدث القواعد
                self.wappalyzer = Wappalyzer.latest()
            except:
                # إذا فشل، نستخدم النسخة الافتراضية
                try:
                    self.wappalyzer = Wappalyzer.latest(update=False)
                except:
                    self.wappalyzer = None
            
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
            # 1. تحليل Wappalyzer (البرمجي)
            if self.wappalyzer and WAPPALYZER_AVAILABLE:
                try:
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
                except Exception as e:
                    print(f"⚠️ [Wappalyzer Runtime Error]: {e}")
            else:
                # 🚀 Fallback to CLI if Python library is missing or failed
                results = self._analyze_with_cli(url, results)

            # 2. فحص يدوي للمقتنيات المخصصة (Custom Tracking Detection)
            content_to_check = html_content or ""
            if not content_to_check:
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

    def _analyze_with_cli(self, url, results):
        """استخدام Wappalyzer CLI (Node.js) كبديل"""
        import subprocess
        try:
            # نحاول تشغيل الأمر ونتوقع مخرجات JSON
            # npm install -g wappalyzer-cli
            process = subprocess.run(
                ["wappalyzer", url],
                capture_output=True,
                text=True,
                timeout=20
            )
            if process.returncode == 0:
                try:
                    data = json.loads(process.stdout)
                    # Wappalyzer CLI returns a list of apps or a structure
                    apps = data.get("applications", []) or data.get("technologies", [])
                    for app in apps:
                        name = app.get("name")
                        results["technologies"].append(name)
                        
                        cats = [c.get("name", "").lower() for c in app.get("categories", [])]
                        if "cms" in cats:
                            results["cms"] = name
                            if name.lower() == "wordpress":
                                results["is_wordpress"] = True
                        if "analytics" in cats or "tracking" in cats:
                            results["tracking_software"].append(name)
                except: pass
            else:
                if not WAPPALYZER_AVAILABLE:
                    # Print once if both fail
                    pass 
        except FileNotFoundError:
            if not WAPPALYZER_AVAILABLE:
                print("  [Tech] ⚠️ Wappalyzer (Python & CLI) not found. Skipping deep scan.")
        except Exception:
            pass
        return results

# نسخة سريعة للاستخدام المباشر
def get_site_tech(url, html=None):
    analyzer = TechAnalyzer()
    return analyzer.analyze(url, html_content=html)
