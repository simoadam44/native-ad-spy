"""Script to patch lp_analyzer.py with new features."""
import re

with open("utils/lp_analyzer.py", "r", encoding="utf-8") as f:
    content = f.read()

# ---- PATCH 1: Update extract_target_from_params dest_params ----
old = 'dest_params = ["requestUrl", "dest", "url", "u", "target", "redirect", "destination"]'
new = 'dest_params = [\n            "requestUrl", "dest", "url", "u", "target", "redirect", "destination",\n            "caller_url", "return_url", "final_url", "goto", "next", "landing"\n        ]'
content = content.replace(old, new, 1)

# ---- PATCH 2: Add new functions after extract_target_from_params ----
insertion_point = '\nasync def wait_for_actual_landing'
URL_REGEX = r"https?://[^\s\"'<>\)\\]+"
new_functions = '''
def is_api_endpoint(url):
    """Returns True if the URL looks like an API/analytics/sync endpoint."""
    if not url: return True
    path = urlparse(url.lower()).path
    api_patterns = [
        "/api/", "/v2/", "/v1/", "/v3/", "/internal/", "/metrics",
        "/sync", "/imsync", "/usersync", "/ingest", "/ingest.php",
        "/analytics", "/collect", "/pixel", "/beacon",
        "/track", "/tracker", ".ashx",
    ]
    return any(p in path for p in api_patterns)

def extract_affiliate_from_html(html):
    """
    HTML-FIRST APPROACH (like AdPlexity/Anstrex):
    Scan page HTML for affiliate destination URLs before any clicking.
    """
    if not html: return ""
    url_pattern = r"https?://[^\\s\\"'<>\\)\\\\]+"
    all_urls = re.findall(url_pattern, html)
    best_url = ""
    for url in all_urls:
        url = url.rstrip(".,;)")
        url_lower = url.lower()
        if not any(sig in url_lower for sig in AFFILIATE_SIGNATURES):
            continue
        if is_api_endpoint(url) or not is_meaningful_url(url):
            continue
        skip_domains = [
            "google-analytics", "googletagmanager", "doubleclick",
            "facebook.com/tr", "clickbank.net/sellerhop",
            "tracking.buygoods", "cbtb.clickbank",
            "ml314.com", "permutive.com", "newsroom.bi"
        ]
        if any(sd in url_lower for sd in skip_domains):
            continue
        priority_paths = ["/pay/", "/order/", "/checkout/", "/vsl", "/video/", "/buy"]
        if any(p in url_lower for p in priority_paths):
            return url
        if not best_url:
            best_url = url
    return best_url

async def wait_for_actual_landing'''

content = content.replace(insertion_point, new_functions, 1)

# ---- PATCH 3: Update handle_response to filter API endpoints ----
old_handler = 'if not is_meaningful_url(r_url): return\n                if status < 200'
new_handler = 'if not is_meaningful_url(r_url): return\n                if is_api_endpoint(r_url): return\n                if status < 200'
content = content.replace(old_handler, new_handler, 1)

# ---- PATCH 4: Use HTML-First extraction for final_offer_url ----
old_final = '        result["final_offer_url"] = page.url\n        result["cloaking"]'
new_final = ('        html_aff = extract_affiliate_from_html(content)\n'
             '        if html_aff:\n'
             '            print(f"HTML-First Match: {html_aff[:80]}")\n'
             '            result["final_offer_url"] = html_aff\n'
             '        else:\n'
             '            result["final_offer_url"] = page.url\n'
             '        result["cloaking"]')
content = content.replace(old_final, new_final, 1)

with open("utils/lp_analyzer.py", "w", encoding="utf-8") as f:
    f.write(content)

print("Patch applied. Verifying syntax...")
import py_compile
try:
    py_compile.compile("utils/lp_analyzer.py", doraise=True)
    print("SYNTAX OK!")
except py_compile.PyCompileError as e:
    print(f"SYNTAX ERROR: {e}")
