import asyncio

async def dismiss_popups(page) -> dict:
    """
    Attempts to dismiss various types of popups and overlays 
    to clear the path for CTA clicks and screenshots.
    """
    results = {
        "popups_found": [],
        "popups_dismissed": [],
        "dismissal_failed": [],
        "time_spent_ms": 0
    }
    start_time = asyncio.get_event_loop().time()
    
    # 1. Cookie Consent Banners
    cookie_selectors = [
        "button:has-text('Accept')", "button:has-text('Accept All')",
        "button:has-text('I Agree')", "button:has-text('OK')",
        "#cookie-accept", ".cookie-accept", "[id*='cookie'] button",
        ".cc-accept", "#CybotCookiebotDialogBodyLevelButtonLevelOptinAllowAll"
    ]
    
    for selector in cookie_selectors:
        try:
            btn = await page.wait_for_selector(selector, timeout=1000)
            if btn and await btn.is_visible():
                await btn.click()
                results["popups_found"].append("cookie")
                results["popups_dismissed"].append("cookie")
                await asyncio.sleep(0.5)
                break
        except:
            continue

    # 2. Wait for delayed subscription popups
    await asyncio.sleep(3.0)
    
    # 3. Close Selectors for Email/Subscription/Age Gates
    close_selectors = [
        "button:has-text('No thanks')", "button:has-text('No, thanks')",
        "button:has-text('Close')", "button:has-text('×')",
        ".popup-close", ".modal-close", "[class*='close']",
        "[class*='dismiss']", "[aria-label='Close']",
        "button:has-text('Skip')", "button:has-text('Maybe later')",
        "button:has-text('I am 18')", "button:has-text('Enter')",
        "button:has-text('Yes, I am of legal age')",
        "[class*='age'] button", "[class*='video-overlay']", "[class*='play-button']"
    ]

    # Trigger exit-intent popup by moving mouse to top
    try:
        await page.mouse.move(300, 0)
        await asyncio.sleep(1.0)
    except:
        pass

    for selector in close_selectors:
        try:
            # Check all matching elements since there might be multiple (like 'X' icons)
            btns = await page.query_selector_all(selector)
            for btn in btns:
                if await btn.is_visible():
                    await btn.click()
                    results["popups_found"].append(f"overlay_{selector[:15]}")
                    results["popups_dismissed"].append(f"overlay_{selector[:15]}")
                    await asyncio.sleep(0.5)
        except:
            continue

    results["time_spent_ms"] = int((asyncio.get_event_loop().time() - start_time) * 1000)
    return results

if __name__ == "__main__":
    # This needs a running playwright session to test
    print("Testing locally requires a live Playwright page.")
