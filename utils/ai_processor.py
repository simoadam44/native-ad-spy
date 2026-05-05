try:
    from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
    CRAWL4AI_AVAILABLE = True
except ImportError:
    CRAWL4AI_AVAILABLE = False

try:
    from cloakbrowser import binary_info
    CLOAK_AVAILABLE = True
except ImportError:
    CLOAK_AVAILABLE = False

async def fast_analyze_offer(url):
    if not CRAWL4AI_AVAILABLE:
        print("  [AI] ⚠️ Crawl4AI not installed. Skipping smart markdown extraction.")
        return None

    try:
        # 1. إعداد المحرك المحصن بـ CloakBrowser
        binary_path = None
        if CLOAK_AVAILABLE:
            try:
                binary_path = binary_info().get('binary_path')
            except: pass

        kwargs = {"headless": True}
        if binary_path:
            kwargs["executable_path"] = binary_path
            
        try:
            browser_cfg = BrowserConfig(**kwargs)
        except TypeError:
            # Fallback if executable_path is not supported or named differently (like browser_executable_path)
            if binary_path:
                kwargs.pop("executable_path", None)
                kwargs["browser_executable_path"] = binary_path
            try:
                browser_cfg = BrowserConfig(**kwargs)
            except TypeError:
                browser_cfg = BrowserConfig(headless=True)


        # 2. إعداد استراتيجية الاستخراج
        run_cfg = CrawlerRunConfig(
            word_count_threshold=5,
            exclude_external_links=False,
            process_iframes=True,
            cache_mode=CacheMode.BYPASS,
        )

        async with AsyncWebCrawler(config=browser_cfg) as crawler:
            result = await crawler.arun(url=url, config=run_cfg)
            
            if result.success:
                content = result.markdown.lower() if result.markdown else ""
                
                classification = "Unknown"
                if "sponsored links" in content or "recommended for you" in content:
                    classification = "Arbitrage"
                elif "buy now" in content or "add to cart" in content:
                    classification = "CPA/E-com"
                elif "enter your email" in content or "get a quote" in content:
                    classification = "Lead Gen"

                return {
                    "type": classification,
                    "summary": getattr(result, "summary", ""),
                    "final_url": result.url,
                    "clean_text": result.markdown
                }
    except Exception as e:
        print(f"  [AI] ❌ Crawl4AI Error: {e}")
    return None
