import requests
import os

TARGET_COUNTRY = "US"
PROXY_CONFIG = {
    "server": "http://gw.dataimpulse.com:823",
    "username": f"85ccde32f1cc6c7ad458__country-{TARGET_COUNTRY}",
    "password": "78c188c405598b8a"
}

def test_proxy():
    proxy_url = f"http://{PROXY_CONFIG['username']}:{PROXY_CONFIG['password']}@gw.dataimpulse.com:823"
    proxies = {
        "http": proxy_url,
        "https": proxy_url
    }
    
    print(f"Testing proxy for {TARGET_COUNTRY}...")
    try:
        response = requests.get("https://ipapi.co/json/", proxies=proxies, timeout=20)
        print("Response Success!")
        print(response.json())
    except Exception as e:
        print(f"Proxy Test Failed: {e}")

if __name__ == "__main__":
    test_proxy()
