
try:
    from Wappalyzer import Wappalyzer, WebPage
    print("Wappalyzer imported successfully")
    w = Wappalyzer.latest(update=False)
    print("Wappalyzer initialized")
    wp = WebPage("https://google.com", "<html></html>")
    print("WebPage created")
    res = w.analyze(wp)
    print(f"Analyze success: {res}")
except Exception as e:
    import traceback
    print(f"Wappalyzer failed: {e}")
    traceback.print_exc()
