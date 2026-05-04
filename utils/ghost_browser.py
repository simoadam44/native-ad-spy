import random
import asyncio
from typing import Optional, Tuple

PROFILES = {
    "win_chrome_us": {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
        "locale": "en-US",
        "timezone": "America/New_York",
        "platform": "Win32",
        "device_type": "desktop",
        "accept_language": "en-US,en;q=0.9",
        "color_scheme": "light",
        "ch_ua": '"Google Chrome";v="124", "Chromium";v="124", "Not-A.Brand";v="99"',
        "ch_ua_mobile": "?0",
        "ch_ua_platform": '"Windows"',
    },
    "win_firefox_us": {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:125.0) Gecko/20100101 Firefox/125.0",
        "viewport": {"width": 1366, "height": 768},
        "locale": "en-US",
        "timezone": "America/Chicago",
        "platform": "Win32",
        "device_type": "desktop",
        "accept_language": "en-US,en;q=0.5",
        "color_scheme": "light",
        "ch_ua": None,
        "ch_ua_mobile": None,
        "ch_ua_platform": None,
    },
    "win_edge_us": {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
        "viewport": {"width": 1440, "height": 900},
        "locale": "en-US",
        "timezone": "America/Los_Angeles",
        "platform": "Win32",
        "device_type": "desktop",
        "accept_language": "en-US,en;q=0.9",
        "color_scheme": "light",
        "ch_ua": '"Microsoft Edge";v="124", "Chromium";v="124", "Not-A.Brand";v="99"',
        "ch_ua_mobile": "?0",
        "ch_ua_platform": '"Windows"',
    },
    "mac_chrome_us": {
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "viewport": {"width": 1440, "height": 900},
        "locale": "en-US",
        "timezone": "America/New_York",
        "platform": "MacIntel",
        "device_type": "desktop",
        "accept_language": "en-US,en;q=0.9",
        "color_scheme": "light",
        "ch_ua": '"Google Chrome";v="124", "Chromium";v="124", "Not-A.Brand";v="99"',
        "ch_ua_mobile": "?0",
        "ch_ua_platform": '"macOS"',
    },
    "mac_safari_us": {
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
        "viewport": {"width": 1280, "height": 800},
        "locale": "en-US",
        "timezone": "America/Los_Angeles",
        "platform": "MacIntel",
        "device_type": "desktop",
        "accept_language": "en-US,en;q=0.9",
        "color_scheme": "light",
        "ch_ua": None,
        "ch_ua_mobile": None,
        "ch_ua_platform": None,
    },
    "iphone_safari_us": {
        "user_agent": "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4_1 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Mobile/15E148 Safari/604.1",
        "viewport": {"width": 390, "height": 844},
        "locale": "en-US",
        "timezone": "America/New_York",
        "platform": "iPhone",
        "device_type": "mobile",
        "accept_language": "en-US,en;q=0.9",
        "color_scheme": "light",
        "ch_ua": None,
        "ch_ua_mobile": None,
        "ch_ua_platform": None,
        "is_mobile": True,
        "has_touch": True,
    },
    "android_chrome_us": {
        "user_agent": "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36",
        "viewport": {"width": 412, "height": 915},
        "locale": "en-US",
        "timezone": "America/Chicago",
        "platform": "Linux armv8l",
        "device_type": "mobile",
        "accept_language": "en-US,en;q=0.9",
        "color_scheme": "light",
        "ch_ua": '"Google Chrome";v="124", "Android WebView";v="124", "Not-A.Brand";v="99"',
        "ch_ua_mobile": "?1",
        "ch_ua_platform": '"Android"',
        "is_mobile": True,
        "has_touch": True,
    },
    "win_chrome_uk": {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
        "locale": "en-GB",
        "timezone": "Europe/London",
        "platform": "Win32",
        "device_type": "desktop",
        "accept_language": "en-GB,en;q=0.9,en-US;q=0.8",
        "color_scheme": "light",
        "ch_ua": '"Google Chrome";v="124", "Chromium";v="124", "Not-A.Brand";v="99"',
        "ch_ua_mobile": "?0",
        "ch_ua_platform": '"Windows"',
    },
    "win_chrome_de": {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
        "locale": "de-DE",
        "timezone": "Europe/Berlin",
        "platform": "Win32",
        "device_type": "desktop",
        "accept_language": "de-DE,de;q=0.9,en-US;q=0.8,en;q=0.7",
        "color_scheme": "light",
        "ch_ua": '"Google Chrome";v="124", "Chromium";v="124", "Not-A.Brand";v="99"',
        "ch_ua_mobile": "?0",
        "ch_ua_platform": '"Windows"',
    },
    "win_chrome_fr": {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
        "locale": "fr-FR",
        "timezone": "Europe/Paris",
        "platform": "Win32",
        "device_type": "desktop",
        "accept_language": "fr-FR,fr;q=0.9,en-US;q=0.8,en;q=0.7",
        "color_scheme": "light",
        "ch_ua": '"Google Chrome";v="124", "Chromium";v="124", "Not-A.Brand";v="99"',
        "ch_ua_mobile": "?0",
        "ch_ua_platform": '"Windows"',
    },
    "win_chrome_au": {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
        "locale": "en-AU",
        "timezone": "Australia/Sydney",
        "platform": "Win32",
        "device_type": "desktop",
        "accept_language": "en-AU,en;q=0.9,en-US;q=0.8",
        "color_scheme": "light",
        "ch_ua": '"Google Chrome";v="124", "Chromium";v="124", "Not-A.Brand";v="99"',
        "ch_ua_mobile": "?0",
        "ch_ua_platform": '"Windows"',
    },
    "win_chrome_ca": {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "viewport": {"width": 1920, "height": 1080},
        "locale": "en-CA",
        "timezone": "America/Toronto",
        "platform": "Win32",
        "device_type": "desktop",
        "accept_language": "en-CA,en;q=0.9,en-US;q=0.8,fr;q=0.7",
        "color_scheme": "light",
        "ch_ua": '"Google Chrome";v="124", "Chromium";v="124", "Not-A.Brand";v="99"',
        "ch_ua_mobile": "?0",
        "ch_ua_platform": '"Windows"',
    },
    "mac_chrome_jp": {
        "user_agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "viewport": {"width": 1440, "height": 900},
        "locale": "ja-JP",
        "timezone": "Asia/Tokyo",
        "platform": "MacIntel",
        "device_type": "desktop",
        "accept_language": "ja,en-US;q=0.9,en;q=0.8",
        "color_scheme": "light",
        "ch_ua": '"Google Chrome";v="124", "Chromium";v="124", "Not-A.Brand";v="99"',
        "ch_ua_mobile": "?0",
        "ch_ua_platform": '"macOS"',
    },
    "win_chrome_br": {
        "user_agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
        "viewport": {"width": 1366, "height": 768},
        "locale": "pt-BR",
        "timezone": "America/Sao_Paulo",
        "platform": "Win32",
        "device_type": "desktop",
        "accept_language": "pt-BR,pt;q=0.9,en-US;q=0.8,en;q=0.7",
        "color_scheme": "light",
        "ch_ua": '"Google Chrome";v="124", "Chromium";v="124", "Not-A.Brand";v="99"',
        "ch_ua_mobile": "?0",
        "ch_ua_platform": '"Windows"',
    },
}

REFERRERS = {
    "health": [
        "https://www.google.com/search?q=natural+remedies+for+joint+pain",
        "https://www.google.com/search?q=best+weight+loss+supplement+2024",
        "https://www.bing.com/search?q=blood+sugar+control+tips",
        "https://www.facebook.com/",
        "https://www.pinterest.com/search/pins/?q=healthy+living",
        "https://www.reddit.com/r/HealthyFood/",
    ],
    "finance": [
        "https://www.google.com/search?q=how+to+invest+money+safely",
        "https://www.bing.com/search?q=best+savings+account+2024",
        "https://www.reddit.com/r/personalfinance/",
        "https://www.facebook.com/",
        "https://finance.yahoo.com/",
    ],
    "general": [
        "https://www.google.com/",
        "https://www.facebook.com/",
        "https://www.bing.com/",
        "https://twitter.com/",
        "https://www.msn.com/",
        "direct",
        "direct",
    ],
    "entertainment": [
        "https://www.google.com/search?q=celebrity+news+today",
        "https://www.facebook.com/",
        "https://twitter.com/trending",
        "https://www.reddit.com/r/entertainment/",
        "https://www.youtube.com/",
    ],
}

def get_profile(
    profile_name: Optional[str] = None,
    device_type: Optional[str] = None,
    country: Optional[str] = None
) -> dict:
    """
    Get a browser profile.
    """
    if profile_name and profile_name in PROFILES:
        return PROFILES[profile_name].copy()
    
    candidates = list(PROFILES.values())
    
    if device_type:
        candidates = [p for p in candidates
                      if p.get("device_type") == device_type]
    
    if country:
        country_map = {
            "us": "en-US", "uk": "en-GB", "de": "de-DE",
            "fr": "fr-FR", "au": "en-AU", "ca": "en-CA",
            "jp": "ja-JP", "br": "pt-BR"
        }
        locale_prefix = country_map.get(country.lower(), "en-US")
        candidates = [p for p in candidates
                      if p.get("locale", "").startswith(locale_prefix[:2])]
    
    if not candidates:
        candidates = list(PROFILES.values())
    
    return random.choice(candidates).copy()


def get_referrer(vertical: str = "general") -> Optional[str]:
    """
    Get a smart referrer URL matching the ad vertical.
    Returns None for 'direct' visits.
    """
    pool = REFERRERS.get(vertical, REFERRERS["general"])
    choice = random.choice(pool)
    return None if choice == "direct" else choice


def should_rotate_identity() -> bool:
    """30% chance to rotate identity mid-session."""
    return random.random() < 0.30


async def apply_profile(
    playwright,
    profile: dict,
    proxy: Optional[dict] = None
) -> Tuple:
    """
    Launch browser and create context with full profile applied.
    Uses CloakBrowser binary for native C++ stealth.
    """
    is_mobile = profile.get("is_mobile", False)
    has_touch = profile.get("has_touch", False)
    
    from cloakbrowser._binary import get_binary_path
    binary_path = get_binary_path()
    
    launch_args = [
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-blink-features=AutomationControlled",
        "--disable-features=IsolateOrigins,site-per-process",
        "--disable-infobars",
        "--window-size={width},{height}".format(**profile["viewport"]),
        "--fingerprint-platform=windows"
    ]
    
    browser = await playwright.chromium.launch(
        executable_path=binary_path,
        headless=True,
        args=launch_args
    )
    
    context_options = {
        "user_agent": profile["user_agent"],
        "viewport": profile["viewport"],
        "locale": profile["locale"],
        "timezone_id": profile["timezone"],
        "color_scheme": profile.get("color_scheme", "light"),
        "accept_downloads": False,
        "java_script_enabled": True,
        "bypass_csp": False,
        "extra_http_headers": {
            "Accept-Language": profile["accept_language"],
        }
    }
    
    if profile.get("ch_ua"):
        context_options["extra_http_headers"].update({
            "Sec-CH-UA": profile["ch_ua"],
            "Sec-CH-UA-Mobile": profile["ch_ua_mobile"],
            "Sec-CH-UA-Platform": profile["ch_ua_platform"],
        })
    
    if is_mobile:
        context_options["is_mobile"] = True
        context_options["has_touch"] = True
    
    if proxy:
        context_options["proxy"] = proxy
    
    context = await browser.new_context(**context_options)
    
    # CloakBrowser patches stealth at C++ level, so no init scripts needed
    
    page = await context.new_page()
    
    return browser, context, page


async def navigate_with_identity(
    page,
    url: str,
    vertical: str = "general",
    simulate_human: bool = True
) -> bool:
    """
    Navigate to URL with smart referrer and optional human simulation.
    """
    referrer = get_referrer(vertical)
    
    try:
        nav_options = {
            "wait_until": "domcontentloaded",
            "timeout": 30000
        }
        
        if referrer:
            nav_options["referer"] = referrer
        
        await page.goto(url, **nav_options)
        
        if simulate_human:
            await asyncio.sleep(random.uniform(1.0, 3.0))
            
            scroll_steps = random.randint(2, 5)
            for _ in range(scroll_steps):
                scroll_amount = random.randint(150, 400)
                await page.mouse.wheel(0, scroll_amount)
                await asyncio.sleep(random.uniform(0.3, 1.2))
            
            if random.random() < 0.4:
                x = random.randint(200, 800)
                y = random.randint(200, 500)
                await page.mouse.move(x, y)
        
        return True
        
    except Exception as e:
        print(f"  Navigation failed: {e}")
        return False
