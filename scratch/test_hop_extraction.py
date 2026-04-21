import os
import sys
from urllib.parse import unquote

# Add current directory to path
sys.path.append(os.getcwd())

from utils.lp_analyzer import extract_target_from_params

def test_extraction():
    # User's problematic URL
    url = "https://hop.clickbank.net/sellerhop?vendor=jointvance&domain=wellnesssciencehub.com&affiliate=supaffcb&tid=288384&requestUrl=https%3A%2F%2Fwellnesssciencehub.com%2Fjointvance_cb%2Fvsl01mod%2F%3Faffiliate%3Dsupaffcb%26extclid%3Dd4vj7nuq6cvcrdrh3mtp9ef4%26tid%3D288384&extclid=d4vj7nuq6cvcrdrh3mtp9ef4"
    
    print(f"Original URL: {url}")
    target = extract_target_from_params(url)
    print(f"Extracted Target: {target}")
    
    expected = "https://wellnesssciencehub.com/jointvance_cb/vsl01mod/?affiliate=supaffcb&extclid=d4vj7nuq6cvcrdrh3mtp9ef4&tid=288384"
    if unquote(target) == unquote(expected):
        print("SUCCESS: Target correctly extracted!")
    else:
        print("FAILURE: Extraction failed or returned unexpected result.")

if __name__ == "__main__":
    test_extraction()
