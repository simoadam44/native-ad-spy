from crawl4ai import AsyncWebCrawler, BrowserConfig, CrawlerRunConfig, CacheMode
from cloakbrowser._binary import get_binary_path

async def fast_analyze_offer(url):
    # 1. إعداد المحرك المحصن بـ CloakBrowser
    browser_cfg = BrowserConfig(
        executable_path=get_binary_path(),
        headless=True
    )

    # 2. إعداد استراتيجية الاستخراج (نركز على النص والروابط فقط)
    run_cfg = CrawlerRunConfig(
        word_count_threshold=5,
        exclude_external_links=False, # نحتاجها لتتبع مسار الأفلييت
        process_iframes=True,
        cache_mode=CacheMode.BYPASS, # نضمن دائماً جلب أحدث نسخة للعرض
    )

    async with AsyncWebCrawler(config=browser_cfg) as crawler:
        result = await crawler.arun(url=url, config=run_cfg)
        
        if result.success:
            # هنا السحر: تصنيف العرض بناءً على محتوى Markdown النظيف
            content = result.markdown.lower() if result.markdown else ""
            
            classification = "Unknown"
            if "sponsored links" in content or "recommended for you" in content:
                classification = "Arbitrage"
            elif "buy now" in content or "add to cart" in content:
                classification = "CPA/E-com"
            elif "enter your email" in content or "get a quote" in content:
                classification = "Lead Gen"

            # استخراج الملخص إذا كان متوفراً من Crawl4AI (اختياري، في بعض الإصدارات)
            summary = getattr(result, "summary", "")

            return {
                "type": classification,
                "summary": summary,
                "final_url": result.url,
                "clean_text": result.markdown
            }
    return None
