import asyncio
import os
import sys
from supabase import create_client

# Manually set environment variables from web/.env.local
SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

async def test_update():
    print("Testing Supabase update with anon key...")
    try:
        # Fetch one ad
        res = supabase.table("ads").select("id").limit(1).execute()
        if not res.data:
            print("No ads found to test.")
            return
        
        ad_id = res.data[0]['id']
        print(f"Attempting to update ad ID: {ad_id}")
        
        # Try a dummy update to a field that doesn't trigger much
        update_res = supabase.table("ads").update({"classification_confidence": "low"}).eq("id", ad_id).execute()
        print("Update successful!")
    except Exception as e:
        print(f"Update failed: {e}")

if __name__ == "__main__":
    asyncio.run(test_update())
