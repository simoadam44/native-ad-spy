"""
utils/site_pool.py
==================
A dynamic pool of 200+ publisher sites organized by niche and geo.
Crawlers sample randomly from this pool every run to avoid the "Loop Trap".
"""
import random

# ══════════════════════════════════════════════════════
# MASTER SITE POOL — 200+ sites across niches & geos
# ══════════════════════════════════════════════════════

SITE_POOL = {

    # ── HEALTH & WELLNESS (highest affiliate ad density) ──
    "health": [
        "https://www.healthline.com/nutrition/benefits-of-ginger",
        "https://www.webmd.com/diet/features/the-truth-about-belly-fat",
        "https://www.everydayhealth.com/diet-nutrition/diet/",
        "https://www.medicalnewstoday.com/articles/foods-to-boost-the-immune-system",
        "https://www.mindbodygreen.com/articles/signs-your-gut-is-unhealthy",
        "https://www.rd.com/health/wellness/",
        "https://www.prevention.com/health/a20507046/signs-you-have-a-leaky-gut/",
        "https://www.health.com/condition/digestive-health/",
        "https://www.menshealth.com/health/a19534961/best-supplements-for-men/",
        "https://www.womenshealthmag.com/health/a19986631/best-supplements/",
        "https://wellnessmama.com/nutrition/apple-cider-vinegar/",
        "https://draxe.com/nutrition/top-10-vitamin-d-rich-foods/",
        "https://www.verywellhealth.com/best-supplements-for-weight-loss-5092231",
        "https://authoritynutrition.com/10-proven-benefits-of-turmeric/",
        "https://www.healthdigest.com/",
        "https://thehealthsite.com/",
        "https://www.naturalnews.com/",
        "https://www.livestrong.com/",
        "https://www.shape.com/lifestyle/mind-and-body/",
        "https://www.self.com/story/supplements-actually-worth-taking",
        "https://herbeauty.co/en/health/",
        "https://www.healthdigest.com/1114261/surprising-ways-reverse-aging/",
        "https://healthierlivingtips.org/",
        "https://wellnessgaze.com/",
    ],

    # ── FINANCE & MONEY ──
    "finance": [
        "https://www.investopedia.com/articles/personal-finance/",
        "https://www.fool.com/the-ascent/personal-finance/",
        "https://www.creditkarma.com/advice/",
        "https://www.nerdwallet.com/article/investing/",
        "https://www.thebalancemoney.com/best-budgeting-tips-1289589",
        "https://moneywise.com/a/simple-investments-that-can-make-you-money",
        "https://www.gobankingrates.com/money/economy/",
        "https://smartasset.com/retirement/retirement-calculator",
        "https://financebuzz.com/ways-to-make-extra-money",
        "https://www.bankrate.com/finance/savings/",
        "https://www.doughroller.net/personal-finance/",
        "https://millennialmoney.com/passive-income-ideas/",
        "https://www.moneycrashers.com/passive-income-ideas/",
        "https://makingsenseofcents.com/2013/07/ways-to-make-extra-money.html",
        "https://www.wealthsimple.com/en-us/learn/",
        "https://pjmedia.com/vodkapundit/",
    ],

    # ── CELEBRITY / ENTERTAINMENT ──
    "entertainment": [
        "https://www.brainberries.co/",
        "https://zestradar.com/celebrities/",
        "https://herbeauty.co/en/entertainment/",
        "https://www.mensjournal.com/entertainment/",
        "https://www.buzzfeed.com/celebrity",
        "https://haberion.com/en/",
        "https://www.womansworld.com/celebrity",
        "https://www.fandom.com/articles/",
        "https://www.ew.com/celebrity/",
        "https://www.eonline.com/news/",
        "https://www.radaronline.com/",
        "https://www.thethings.com/celebrity/",
        "https://www.looper.com/",
        "https://www.ranker.com/list/",
        "https://www.grunge.com/",
        "https://www.mashed.com/",
        "https://www.nicki swift.com/",
        "https://pjmedia.com/",
        "https://rankupwards.com/trending/",
        "https://buzzday.info/",
    ],

    # ── NEWS & POLITICS ──
    "news": [
        "https://www.ibtimes.com/",
        "https://www.thedailybeast.com/",
        "https://www.newsweek.com/",
        "https://thehill.com/",
        "https://townhall.com/",
        "https://www.breitbart.com/",
        "https://pjmedia.com/",
        "https://www.washingtonexaminer.com/",
        "https://www.americanthinker.com/",
        "https://www.frontpagemag.com/",
        "https://www.wnd.com/",
        "https://www.theblaze.com/",
        "https://www.realclearpolitics.com/",
        "https://dailycaller.com/",
        "https://www.independent.co.uk/news/world/americas/",
        "https://www.dailymail.co.uk/news/",
        "https://nypost.com/news/",
    ],

    # ── DIY / HOME ──
    "diy_home": [
        "https://www.tips-and-tricks.co/do-it-yourself/",
        "https://www.familyhandyman.com/list/",
        "https://www.thisoldhouse.com/home-improvement/",
        "https://www.bobvila.com/articles/",
        "https://www.hgtv.com/lifestyle/",
        "https://www.homedepot.com/c/how_to/",
        "https://www.goodhousekeeping.com/home/",
        "https://www.realsimple.com/home-organizing/",
        "https://www.artofmanliness.com/skills/home-repair/",
        "https://lifehacker.com/home/",
    ],

    # ── FOOD & RECIPES ──
    "food": [
        "https://www.allrecipes.com/recipes/87/everyday-cooking/",
        "https://www.foodnetwork.com/healthy/articles/",
        "https://www.delish.com/",
        "https://www.epicurious.com/",
        "https://www.bonappetit.com/",
        "https://www.tasteofhome.com/",
        "https://www.seriouseats.com/",
        "https://www.cookinglight.com/",
        "https://www.eatingwell.com/",
        "https://www.thekitchn.com/",
    ],

    # ── SPORTS & FITNESS ──
    "sports": [
        "https://www.bleacherreport.com/",
        "https://www.si.com/nfl/",
        "https://www.espn.com/espn/story/",
        "https://www.cbssports.com/",
        "https://www.nbcsports.com/",
        "https://www.yardbarker.com/",
        "https://www.sportingnews.com/",
        "https://www.dailysportx.com/",
        "https://ladbible.com/sport/",
    ],

    # ── TECH & GADGETS ──
    "tech": [
        "https://www.techradar.com/best/",
        "https://www.tomsguide.com/best-picks/",
        "https://www.cnet.com/tech/",
        "https://www.pcmag.com/reviews/",
        "https://www.digitaltrends.com/",
        "https://lifehacker.com/tech/",
        "https://www.zdnet.com/article/",
        "https://www.makeuseof.com/",
        "https://www.howtogeek.com/",
    ],

    # ── ARABIC / MENA ──
    "arabic": [
        "https://sabq.org/",
        "https://www.aljazeera.net/news/",
        "https://www.bbc.com/arabic/",
        "https://arabic.cnn.com/",
        "https://www.youm7.com/",
        "https://herbeauty.co/ar/",
        "https://brainberries.co/ar/",
        "https://zahra.net/",
        "https://www.annaharkw.com/",
        "https://www.masrawy.com/",
        "https://www.arabi21.com/",
        "https://www.alhurra.com/",
        "https://elaph.com/",
        "https://www.raialyoum.com/",
    ],

    # ── FRENCH ──
    "french": [
        "https://www.lefigaro.fr/",
        "https://www.leparisien.fr/",
        "https://www.bfmtv.com/",
        "https://www.lepoint.fr/",
        "https://www.lexpress.fr/",
        "https://www.marieclaire.fr/",
    ],

    # ── GERMAN ──
    "german": [
        "https://www.spiegel.de/",
        "https://www.focus.de/",
        "https://www.bild.de/",
        "https://www.stern.de/",
        "https://www.sueddeutsche.de/",
    ],

    # ── SPANISH ──
    "spanish": [
        "https://www.elconfidencial.com/",
        "https://www.elmundo.es/",
        "https://www.marca.com/",
        "https://es.euronews.com/",
        "https://www.lavanguardia.com/",
    ],

    # ── SLIDESHOW / ARBITRAGE (high Taboola/Revcontent density) ──
    "slideshow": [
        "https://www.articlestone.com/",
        "https://www.habittribe.com/",
        "https://www.tips-and-tricks.co/online/",
        "https://zestradar.com/",
        "https://brainberries.co/",
        "https://www.thegamer.com/",
        "https://www.therichest.com/",
        "https://www.thesportster.com/",
        "https://www.babygaga.com/",
        "https://www.screenrant.com/",
        "https://www.cbr.com/",
        "https://www.movieweb.com/",
        "https://www.thedelite.com/",
        "https://www.goalcast.com/",
        "https://www.lifehack.org/",
        "https://www.LifeAdvancer.com/",
        "https://www.awarenessact.com/",
        "https://www.providr.com/",
        "https://www.womenworking.com/",
        "https://ladbible.com/",
    ],
}


# ══════════════════════════════════════════════════════
# USER-AGENT POOL — Rotated per request
# ══════════════════════════════════════════════════════
USER_AGENTS = [
    # Chrome Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    # Chrome Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_4) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Safari/537.36",
    # Safari Mac
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 14_4_1) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4.1 Safari/605.1.15",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_3) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.4 Safari/605.1.15",
    # Firefox Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:124.0) Gecko/20100101 Firefox/124.0",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:123.0) Gecko/20100101 Firefox/123.0",
    # iPhone Safari
    "Mozilla/5.0 (iPhone; CPU iPhone OS 17_4 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.4 Mobile/15E148 Safari/604.1",
    "Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1",
    # Android Chrome
    "Mozilla/5.0 (Linux; Android 14; Pixel 8) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.6367.82 Mobile Safari/537.36",
    "Mozilla/5.0 (Linux; Android 13; Samsung Galaxy S23) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/123.0.0.0 Mobile Safari/537.36",
    # Edge Windows
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
]


# ══════════════════════════════════════════════════════
# REFERRER POOL — Simulates organic traffic sources
# ══════════════════════════════════════════════════════
REFERRERS = [
    "https://www.google.com/",
    "https://www.google.com/search?q=health+tips+2024",
    "https://www.google.com/search?q=best+supplements+for+men",
    "https://www.google.com/search?q=how+to+lose+weight+fast",
    "https://www.facebook.com/",
    "https://t.co/",
    "https://l.instagram.com/",
    "https://www.bing.com/search?q=natural+remedies",
    "https://www.reddit.com/r/health/",
    "https://www.reddit.com/r/personalfinance/",
    "https://duckduckgo.com/?q=celebrity+news+2024",
    "https://news.google.com/",
    "https://flipboard.com/",
    "https://www.msn.com/",
    "https://www.yahoo.com/news/",
    "",  # Direct traffic (no referrer)
    "",
    "",
]


# ══════════════════════════════════════════════════════
# SMART SAMPLING FUNCTIONS
# ══════════════════════════════════════════════════════

def get_random_sites(n: int = 5, niches: list = None, geo: str = "US") -> list:
    """
    Pick n random sites from the pool.
    
    - If niches specified, pick from those niches only.
    - Otherwise, pick cross-niche for maximum diversity.
    - Geo biases the niche selection (e.g. AR geo → arabic niche).
    """
    GEO_NICHE_BIAS = {
        "SA": ["arabic", "health", "entertainment"],
        "AE": ["arabic", "health", "finance"],
        "MA": ["arabic", "entertainment", "slideshow"],
        "EG": ["arabic", "entertainment", "health"],
        "FR": ["french", "health", "entertainment"],
        "DE": ["german", "finance", "tech"],
        "ES": ["spanish", "health", "entertainment"],
        "MX": ["spanish", "health", "entertainment"],
        "US": ["health", "finance", "entertainment", "news", "slideshow"],
        "GB": ["health", "entertainment", "news", "slideshow"],
        "CA": ["health", "finance", "entertainment"],
        "AU": ["health", "entertainment", "news"],
        "JP": ["tech", "health", "entertainment"],
        "KR": ["tech", "health", "entertainment"],
        "IN": ["health", "finance", "entertainment"],
        "BR": ["health", "entertainment", "sports"],
    }

    # Determine which niches to sample from
    target_niches = niches or GEO_NICHE_BIAS.get(geo, list(SITE_POOL.keys()))

    # Ensure we include at least one high-density affiliate niche
    must_include = ["health", "slideshow", "entertainment"]
    for m in must_include:
        if m not in target_niches and m in SITE_POOL:
            target_niches.append(m)

    # Build candidate list from target niches
    candidates = []
    for niche in target_niches:
        if niche in SITE_POOL:
            candidates.extend(SITE_POOL[niche])

    # Remove duplicates and shuffle
    candidates = list(set(candidates))
    random.shuffle(candidates)

    return candidates[:n]


def get_random_ua() -> str:
    """Return a random user agent."""
    return random.choice(USER_AGENTS)


def get_random_referrer() -> str:
    """Return a random referrer (or empty string for direct)."""
    return random.choice(REFERRERS)


def get_rotation_config(geo: str = "US") -> dict:
    """
    Return a full rotation config for one crawl session:
    - sites to visit
    - user agent
    - referrer
    """
    sites = get_random_sites(n=random.randint(5, 8), geo=geo)
    return {
        "sites": sites,
        "user_agent": get_random_ua(),
        "referrer": get_random_referrer(),
    }


if __name__ == "__main__":
    # Test the pool
    import json
    config = get_rotation_config("US")
    print("=== Rotation Config Sample ===")
    print(f"User-Agent: {config['user_agent'][:80]}")
    print(f"Referrer:   {config['referrer']}")
    print(f"Sites ({len(config['sites'])}):")
    for s in config["sites"]:
        print(f"  - {s}")
    print()
    config_ar = get_rotation_config("SA")
    print("=== Arabic Config Sample ===")
    for s in config_ar["sites"]:
        print(f"  - {s}")
