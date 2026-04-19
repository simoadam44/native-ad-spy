import os
from supabase import create_client

SUPABASE_URL = os.environ.get("SUPABASE_URL", "https://avxoumymzbioeabxfcca.supabase.co")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

def check_filters():
    print("Checking unique trackers...")
    res = supabase.table("ads").select("tracker_tool").execute()
    trackers = set([r['tracker_tool'] for r in res.data if r['tracker_tool']])
    print(f"Found trackers: {trackers}")

    print("\nChecking unique affiliate networks...")
    res = supabase.table("ads").select("affiliate_network").execute()
    networks = set([r['affiliate_network'] for r in res.data if r['affiliate_network']])
    print(f"Found networks: {networks}")

if __name__ == "__main__":
    check_filters()
