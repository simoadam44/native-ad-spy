import os
import asyncio
from supabase import create_client

async def check_schema():
    url = os.environ.get("SUPABASE_URL", "https://avxoumymzbioeabxfcca.supabase.co")
    key = os.environ.get("SUPABASE_KEY", "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX")
    supabase = create_client(url, key)
    
    # Try to select one row from ads to see what columns we get
    try:
        res = supabase.table("ads").select("*").limit(1).execute()
        if res.data:
            print("Columns in 'ads' table:")
            print(list(res.data[0].keys()))
        else:
            print("No data in 'ads' table to check columns.")
    except Exception as e:
        print(f"Error checking ads table: {e}")

    try:
        res = supabase.table("analysis_logs").select("*").limit(1).execute()
        if res.data:
            print("\nColumns in 'analysis_logs' table:")
            print(list(res.data[0].keys()))
    except Exception as e:
        print(f"Error checking analysis_logs table: {e}")

if __name__ == "__main__":
    asyncio.run(check_schema())
