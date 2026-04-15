import os
from supabase import create_client

def check_db():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        print("Missing Supabase credentials")
        return
    
    supabase = create_client(url, key)
    res = supabase.table("ads").select("title, landing, source").eq("network", "MGID").order("created_at", desc=True).limit(20).execute()
    
    for r in res.data:
        print(f"Title: {r['title']}")
        print(f"Landing: {r['landing']}")
        print("-" * 30)

if __name__ == "__main__":
    check_db()
