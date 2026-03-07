import requests
from bs4 import BeautifulSoup

site = "https://edition.cnn.com"

html = requests.get(site).text
soup = BeautifulSoup(html,"html.parser")

ads = soup.select(".trc_spotlight_item")

for ad in ads:

    title = ad.get_text(strip=True)

    img = ad.find("img")
    image = img["src"] if img else ""

    link = ad.find("a")
    landing = link["href"] if link else ""

    print("TITLE:", title)
    print("IMAGE:", image)
    print("LINK:", landing)
    print("-----")
