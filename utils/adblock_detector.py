from bs4 import BeautifulSoup
import re

# A simplified, highly optimized list of common AdBlock Plus filter identifiers
# focused on native ads, display ads, and arbitrage networks.
AD_IDENTIFIERS = [
    re.compile(r'google_ads?'), re.compile(r'adsbygoogle'),
    re.compile(r'taboola'), re.compile(r'outbrain'),
    re.compile(r'revcontent'), re.compile(r'mgid'),
    re.compile(r'contentad'), re.compile(r'ad-container'),
    re.compile(r'sponsored-content'), re.compile(r'ad_slot'),
    re.compile(r'dfp-ad'), re.compile(r'advertisement'),
    re.compile(r'^ad-'), re.compile(r'-ad$'), re.compile(r'banner-ad'),
    re.compile(r'adx-'), re.compile(r'ads-box'),
    re.compile(r'zergnet'), re.compile(r'rc-widget')
]

def analyze_ad_density(html_content: str) -> dict:
    """
    Parses the HTML to find the ratio of ad elements to total content elements.
    High ad density is a very strong indicator of Arbitrage.
    """
    if not html_content:
        return {"ad_count": 0, "total_elements": 0, "density_ratio": 0.0, "is_high_density": False}
        
    soup = BeautifulSoup(html_content, "html.parser")
    
    # Exclude script and style tags from counting
    for script in soup(["script", "style", "noscript", "meta", "link"]):
        script.decompose()
        
    # Get all block-level elements that might hold content or ads
    elements = soup.find_all(['div', 'section', 'article', 'aside', 'li'])
    total_elements = len(elements)
    
    if total_elements == 0:
        return {"ad_count": 0, "total_elements": 0, "density_ratio": 0.0, "is_high_density": False}
        
    ad_count = 0
    ad_signatures_found = []
    
    for el in elements:
        element_id = el.get('id', '').lower()
        element_classes = ' '.join(el.get('class', [])).lower()
        
        # Check against ad identifiers
        combined_identifiers = f"{element_id} {element_classes}"
        
        if combined_identifiers.strip():
            for pattern in AD_IDENTIFIERS:
                if pattern.search(combined_identifiers):
                    ad_count += 1
                    ad_signatures_found.append(combined_identifiers)
                    break # Count this element as an ad and move to next
                    
    density_ratio = ad_count / total_elements if total_elements > 0 else 0
    
    # An Arbitrage site usually has a high ratio of ad wrappers to actual content blocks
    # A density > 0.08 (8%) of all block elements being ad containers is extremely high
    is_high_density = density_ratio > 0.08 or ad_count > 10
    
    return {
        "ad_count": ad_count,
        "total_elements": total_elements,
        "density_ratio": round(density_ratio, 4),
        "is_high_density": is_high_density,
        "signatures": list(set(ad_signatures_found))[:5] # Sample of found signatures
    }
