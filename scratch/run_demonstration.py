import asyncio
import os
import json

# Set Credentials BEFORE importing deep_analyzer (which initializes client at module level)
os.environ["SUPABASE_URL"] = "https://avxoumymzbioeabxfcca.supabase.co"
os.environ["SUPABASE_KEY"] = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"

from deep_analyzer import deep_analyze_ad

async def run_demo():
    ad_id = 31494
    landing_url = "https://smeagol.revcontent.com/cv/v3/deKkeqZbvA-aLSaUCrl2vfugUTyffHcHsSHljci-sOIlwX-FNAdHzAwUoZILdcOeor98t29zJnXUVJqn7Oyhl2q7owOpuf6JpV8l6LLz3uTw5c_OszuRWf1EdiCh8C5omvR1DtBlX-lV1wyrzy6Z6yGRLv7nXJbCpQKfioEUWy8HnIBMEb1SQC1AyY2dcfvOoNc5MYP2hO51YROoPjmRm4Cw5Ic_b_m6uIQY2B-BCTyX9bgZf1ti90j0jW6wNlnWTlUOabN9H-m-t_qjw7NKQXJobu21guqist5gpcN8P4ZJBz82BvX2GIH5Pxe5Kxge3OzviDrjh5EnQZAmoE97o3IyDg7pvSIIwFkHLysD9ljkPbNCjpRLnZ2NA6l4IiiA9NCNzEMtVp0?p=GgFDMJ6Vgc8GOiRjNjRmMjk3MC04MzI5LTRjMTctOTMwZS1lMjdhNDRmODIwN2VCJGM0ZTI1ODMyLTcyMGItNDdhMi1hZmQxLTIyOGRjMjU0MWRkZUoLd2hpZS13YWxrZXJQlJwMWKjUEWILam9laG9mdC5jb21qB2Rlc2t0b3CQAQGRAjMzMzMzM-M_qgIPMTg1LjE5Ni4xMDkuMjM36gIQCghncmF5X2ltcBIEdHJ1ZeoCEgoJdGVzdF9tb2RlEgVmYWxzZeoCFwoOdXBzY2FsZWRfaW1hZ2USBWZhbHNl"
    title = "The Close Relationship Between Stress and Sleep"
    
    print("STARTING CLASSIFICATION AND SPYING JOURNEY...")
    print(f"Ad ID: {ad_id}")
    print(f"Title: {title}")
    
    try:
        result = await deep_analyze_ad(ad_id, landing_url, title)
        
        print("\n" + "="*40)
        print("JOURNEY COMPLETE: RESULTS")
        print("="*40)
        print(json.dumps(result, indent=2, default=str))
        print("="*40)
    except Exception as e:
        print(f"Demo Failed: {e}")

if __name__ == "__main__":
    asyncio.run(run_demo())
