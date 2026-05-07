try:
    from Wappalyzer import Wappalyzer, WebPage
    print("Success: Wappalyzer imported")
except ImportError as e:
    print(f"ImportError: {e}")
except Exception as e:
    print(f"Other Error: {e}")
