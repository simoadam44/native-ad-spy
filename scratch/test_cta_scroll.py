import asyncio
from playwright.async_api import async_playwright

async def main():
    urls = [
        "https://wellnessgaze.com/13592_dbt_t/?s=2673040405",
        "https://viewitquickly.online/video/?bemobdata=c%3D578da148-ed46-4928-93a5-29193ac24a5f"
    ]
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)
        for url in urls:
            print(f"\n--- Testing {url} ---")
            page = await browser.new_page()
            try:
                await page.goto(url, wait_until="domcontentloaded", timeout=30000)
                await asyncio.sleep(2)
                
                # Simulate realistic scroll to bottom
                for _ in range(5):
                    await page.mouse.wheel(0, 1000)
                    await asyncio.sleep(0.5)
                
                # Try finding highest scoring CTA
                keywords = ["click here", "watch", "video", "buy", "order", "get", "claim", "shop", "discount", "check", "haz clic", "obtener", "طلب", "klicken", "voir"]
                
                elements = await page.query_selector_all("a, button, [role='button'], input[type='button'], input[type='submit'], [class*='btn'], [class*='button'], [class*='cta']")
                
                best_el = None
                best_score = -1
                best_text = ""
                
                for el in elements:
                    try:
                        txt = (await el.inner_text() or "").strip()
                        href = (await el.get_attribute("href") or "").lower()
                        class_attr = (await el.get_attribute("class") or "").lower()
                        
                        score = 0
                        txt_lower = txt.lower()
                        
                        if not txt and not href:
                            continue
                            
                        if any(s in href for s in ["facebook.com", "twitter.com", "instagram.com", "pinterest.com", "linkedin.com"]):
                            score -= 50
                            
                        for k in keywords:
                            if k in txt_lower:
                                score += 10
                                
                        if "btn" in class_attr or "button" in class_attr or "cta" in class_attr:
                            score += 5
                            
                        if href and href not in ["", "#", "/"]:
                            score += 5
                            
                        # Favor larger text length (meaningful context like "Click here to watch the video") but not too large
                        if 5 < len(txt) < 50:
                            score += 2
                            
                        if score > best_score:
                            best_score = score
                            best_el = el
                            best_text = txt
                    except:
                        pass
                        
                print(f"Best CTA Found: '{best_text}' (Score: {best_score})")
            except Exception as e:
                print(e)
            finally:
                await page.close()
        
        await browser.close()

if __name__ == "__main__":
    asyncio.run(main())
