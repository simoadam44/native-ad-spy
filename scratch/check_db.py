import os
from supabase import create_client

supabase_url = "https://avxoumymzbioeabxfcca.supabase.co"
supabase_key = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"
supabase = create_client(supabase_url, supabase_key)

res = supabase.table("ads").select("network").limit(100).execute()
networks = set(r['network'] for r in res.data)
print(f"Networks found: {networks}")

mgid_res = supabase.table("ads").select("network").ilike("network", "mgid").limit(5).execute()
print(f"Actual MGID values: {[r['network'] for r in mgid_res.data]}")
