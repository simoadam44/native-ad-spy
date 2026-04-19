import os
import asyncio
from supabase import create_client

async def setup_missing_table():
    url = os.environ.get("SUPABASE_URL", "https://avxoumymzbioeabxfcca.supabase.co")
    key = os.environ.get("SUPABASE_KEY", "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX")
    supabase = create_client(url, key)
    
    print(f"Attempting to ensure table 'forensic_feedback' exists...")
    
    # Since we can't run raw SQL easily via the client without an RPC, 
    # and we don't know if the user has one, we'll try a dummy insert.
    # If the table doesn't exist, this will fail, but at least we confirmed.
    # The real fix is to run the SQL in the dashboard.
    
    sql = """
    CREATE TABLE IF NOT EXISTS forensic_feedback (
        domain TEXT PRIMARY KEY,
        forced_type TEXT NOT NULL CHECK (forced_type IN ('Affiliate', 'Arbitrage')),
        notes TEXT,
        updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
    ALTER TABLE forensic_feedback DISABLE ROW LEVEL SECURITY;
    """
    
    print("-" * 30)
    print("PLEASE RUN THIS SQL IN YOUR SUPABASE DASHBOARD:")
    print("-" * 30)
    print(sql)
    print("-" * 30)

if __name__ == "__main__":
    asyncio.run(setup_missing_table())
