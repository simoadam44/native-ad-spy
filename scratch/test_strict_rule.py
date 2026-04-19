import asyncio
import os
import sys

# Add parent dir to path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from deep_analyzer import deep_analyze_ad

async def test_strict_rule():
    # Problematic URL that was misclassified as Arbitrage
    url = "https://healthierlivingtips.org/int_jp_spl/?c=wnqbaf1roqf9qfqh3do1qi9k&r=289324_joehoft.com_2107485_MA_DESKTOP_Windows&t=66729985-64f1-4eee-a6f7-e69ac6bb45f7&ti=3,8,15&cep=n86QrJUn1Mt4bPYz9oc4sNIwT44JE3a2WkhFCOiWHveI7bF9ZktJQGXBuF1dg_P5fxdwPPHIA88bs-ScsNgo7jryOtKuEym3FfP01i0frB1m0JNCLpCfQLZYc2f9Io2YtAcd_9fO7INA7zvNEOs28aRjGlEahWEbZY6G4pEkK3L1M1oP-CpApL2tT2uh3lqxFxQhL5a9Kkww_WVmPUTGb1zeIuZLBm_5-9mBiXB2I9-RMNjvMVJVeqU3mYoNMe0lUs9kaYu03m8YfuYIplTgHeZkIJ9GU6CF8rBU41NvrBUAfJ0K9WOwFMcYMwX6sOY0zTW9mGZwDxIJlfnuHLZ56_5wEAESPaf5ri9soTX6_krjCmkAQBa4djKmIYaecu1HvKDll6SrNaDdQFbs6_-ONqSe6z1aF562a_Bq21f0vN968X1X8E4ansVdv6U4n1VOr_ZXlRJS_P8i8sQ4xc21LV1IrGTpWDm3aQr1_qCtPNMshP3MngVF7LtRGB9PpVAZPvwNfKR7mRATUyWVXKazjFFybhK4rSeeToNj60xidYuQaczTrdvXjraWNiE_SHdNV9zRjXr4YGBcKguMTVeoVy1mh6e5wAOmPGvlz5bPmdqLjasTd9-rK7KLUHqTJuZeFOq1Ewjmqr_e6nZmrGyvITZS4W2MnJzvj5sRPEAWx_Ry5sWG7416qVnr7-kmmVu-Rrj9DdjVM8XET0RJkKFHD_47pHUhmSk9RC_VQvnjkXoYr4dQV0htR8mG3KMGGEIsfOqD13JIxkmP9_Ri_vY2wA&lptoken=179f76d261d8332e72a6&widget_id=289324&content_id=11767933&boost_id=2107485&sn=joehoft.com&utm_source=289324&utm_term=joehoft.com&utm_campaign=2107485&utm_content=11767933&hl=Surgeon+Reveals%3A+Simple+Method+Ends+Joint+Pain+%26+Arthritis+%28Watch%29&pt=In-Article&wn=joehoft.com+-+3x1+In-article+%283%29&rc_uuid=885d2d24-8586-4732-af4d-2e0bb6027e07"
    title = "Surgeon Reveals: Simple Method Ends Joint Pain & Arthritis (Watch)"
    
    print(f"Testing URL: {url[:100]}...")
    
    # We use a dummy ID for testing
    result = await deep_analyze_ad(999999, url, title)
    
    print("\nAd Classification Result:")
    print(f"Type: {result.get('ad_type')}")
    print(f"Confidence: {result.get('confidence')}")
    print(f"Reason: {result.get('reason')}")
    print(f"Signals: {result.get('signals')}")
    
    if result.get('ad_type') == "Arbitrage":
        print("\nERROR: Still classified as Arbitrage!")
    else:
        print("\nSUCCESS: No longer classified as Arbitrage.")

if __name__ == "__main__":
    asyncio.run(test_strict_rule())
