
try:
    from crawl4ai import AsyncWebCrawler
    print("crawl4ai imported successfully")
except Exception as e:
    import traceback
    print(f"crawl4ai failed: {e}")
    traceback.print_exc()
