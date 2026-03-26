import asyncio
from playwright.async_api import async_playwright
from playwright_stealth import Stealth

async def debug_mgid():
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        await Stealth().apply_stealth_async(page)
        
        target = "https://herbeauty.co/ar/altarfih/maqati-video-raqs-zouk-lan-tastatia-at-tawaqquf-an-mushahadatiha-miraran-wa-takraran/"
        print(f"Navigating to {target}...")
        
        try:
            await page.goto(target, wait_until="networkidle", timeout=60000)
        except:
            print("Timeout, but continuing...")
            
        await asyncio.sleep(10)
        
        # Scroll to load ads
        for i in range(5):
            await page.evaluate("window.scrollBy(0, 800)")
            await asyncio.sleep(2)
            
        print("Starting extraction debug...")
        
        for frame in page.frames:
            links = frame.locator('.mgline a, .mgbox a, [id^="mgid_"] a, .mgid-widget a, .mg-teaser a')
            count = await links.count()
            if count > 0:
                print(f"Found {count} links in target frame.")
                for i in range(min(count, 10)):
                    el = links.nth(i)
                    title = await el.inner_text()
                    href = await el.get_attribute("href")
                    
                    if title and len(title.strip()) > 5:
                        print(f"Ad found: {title.strip()[:30]}...")
                        
                        image_url = await el.evaluate("""
                            (a) => {
                                console.log('Checking ad:', a.innerText);
                                // 1. Check img inside link
                                let img = a.querySelector('img');
                                if (img && (img.src || img.dataset.src)) return 'IMG_INSIDE: ' + (img.src || img.dataset.src);
                                
                                // 2. Find container
                                let container = a.closest('.mgline, .mgbox, .mgid-widget, .mg-teaser, .image-with-text, [id^="mgid_"]');
                                if (!container) container = a.parentElement;
                                console.log('Container found:', container.className);
                                
                                // 3. Check img inside container
                                let cImg = container.querySelector('img');
                                if (cImg && (cImg.src || cImg.dataset.src)) return 'IMG_IN_CONTAINER: ' + (cImg.src || cImg.dataset.src);
                                
                                // 4. Check background-image
                                let searchEls = [container, ...container.querySelectorAll('div, span, a')];
                                for (let el of searchEls) {
                                    let style = window.getComputedStyle(el);
                                    let bg = style.backgroundImage;
                                    if (bg && bg !== 'none' && bg.includes('http')) {
                                        return 'BG_IMAGE: ' + bg.replace(/url\\(['"]?(.*?)['"]?\\)/, '$1');
                                    }
                                }
                                return 'NOT_FOUND';
                            }
                        """)
                        print(f"   Result: {image_url}")
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_mgid())
