import requests
import sys

# Ensure UTF-8 output for Windows console
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8')

# New Datacenter Proxy Details (HTTP)
PROXY_CONFIG = {
    "server": "http://gw.dataimpulse.com:823",
    "username": "7dce367ee7442e94dcd3",
    "password": "30243fe81b50b2de"
}

def test_proxy():
    proxy_url = f"http://{PROXY_CONFIG['username']}:{PROXY_CONFIG['password']}@gw.dataimpulse.com:823"
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }
    
    print(f"Testing HTTP Proxy: {proxy_url.split('@')[1]}")
    try:
        response = requests.get("https://ipapi.co/json/", proxies=proxies, timeout=20)
        print("✅ Success!")
        data = response.json()
        print(f"IP: {data.get('ip')}")
        print(f"Country: {data.get('country_name')}")
        print(f"Org: {data.get('org')}")
    except Exception as e:
        print(f"❌ Failed: {e}")

if __name__ == "__main__":
    test_proxy()
