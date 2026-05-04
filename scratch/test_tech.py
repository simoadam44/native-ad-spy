import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.tech_analyzer import get_site_tech
import json

def test_tech(url):
    print(f"🔍 Analyzing {url}...")
    results = get_site_tech(url)
    print(json.dumps(results, indent=2))

if __name__ == "__main__":
    url = sys.argv[1] if len(sys.argv) > 1 else "https://wordpress.org"
    test_tech(url)
