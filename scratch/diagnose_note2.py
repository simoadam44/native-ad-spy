import asyncio
import sys
import os
sys.path.append(os.getcwd())
from playwright.async_api import async_playwright
from utils.deep_navigator import find_real_offer_deep

async def debug_ad():
    url = "https://smarterlivingdaily.org/lps/F1h7P22F4/?cc=US&c=wbl9ga05bil1oj4ijm0opa72&r=289325_joehoft.com_2472404_US_DESKTOP_Windows&t=66729985-64f1-4eee-a6f7-e69ac6bb45f7&ti=5%2C15%2C30%2C60%2C120&cep=uv2aIyHb9E0tSPsG0nbrk8cICYvSjJoqyg2FkdppxBgnOv-_uNY6XecIWq51ffos6gvDsK2mqIaQdGZIp6ic4HsDYTVxGTcWKuKxgwnNgqZ3Nxjfftwc_KS5GU5-iXMOR7V8iMu9kzP33xbYPdcycaMQ7s0USY2Xl9RMjNOhUX-qitVTEcdAf9fciFaMPGFqA2CbSgrM6w_RxDy0GFhGF6WhqRCTA24iZ4IFNM5DNex_G-CHaRsiakJPpkd06KIwGhJe1_k4N2DMh130hk_7-W1tMwAfY7mS17oJTHMT2bElKpTYwTU2Q5a7kTT5RHOHIjcn8M6-dcDQvAElFYKlvrUo5t_lwH9gXZvT6W_PfxpB56OJw0GLXlmGjKYauAm_KA6dNYGU4p84zGG1zM8KpO5iFDAm2ifpNwunPATdJZlHQT8zfM8hUvLT6kem9EQKw-hcB_rOmNu1y62siJA_JRaxgukic3oyAmd7sfwMngeE0ch3tgiagsN0xAVuJzflwAScYtUQ-vb8IA9RyMPaSZQY_XEjRDmJh8BzKr-k1OcNdQnnb2NislpjgEnT96rfHUHsuU-Q5AVCyvIby_l3AIoaXL3LT9sEyJbgOlsnTSnoXT9Aa55elM2huvjdLvZ8BJtSxsG90Mkeq258aq0Knc9uOhzEE-KgW6OZLazunV6QJfqIxs9ybc4IsqUmCtVKBwOvS_T4BkDlkfRehUerMg5483loyyUY4rfG4vhNjnMbCdMIHjxlAPpzenVCdskQC8si0aIIMkhLhuTMUE1cOA&lptoken=1743779a789900e694da&widget_id=289325&content_id=14151159&boost_id=2472404&sn=joehoft.com&wn=joehoft.com+-+Below+Article&pt=Below+Article&hl=This+Pillow+Solves+Sleep+Apnea+Problems+by+Keeping+Airway+Open+While+You+Sleep&rc_uuid=29de290c-4d17-49ce-9116-2ed0d196ae23"
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        context = await browser.new_context()
        page = await context.new_page()
        
        print(f"--- Diagnosing Ad ---")
        result = await find_real_offer_deep(page, url)
        
        print(f"Result: {result}")
        await browser.close()

if __name__ == "__main__":
    asyncio.run(debug_ad())
