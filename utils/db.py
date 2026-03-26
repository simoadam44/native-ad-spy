import os
import streamlit as st
from supabase import create_client, Client

# --- 1. إعدادات قاعدة البيانات ---
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")

@st.cache_resource
def get_supabase_client() -> Client:
    if not SUPABASE_URL or not SUPABASE_KEY:
        st.error("Missing SUPABASE_URL or SUPABASE_KEY environment variables.")
        return None
    return create_client(SUPABASE_URL, SUPABASE_KEY)

supabase = get_supabase_client()

# --- 2. وظائف الإعلانات ---
@st.cache_data(ttl=120)
def get_ads(search="", networks=None, sort_by="newest", min_impressions=0, limit=30, offset=0):
    try:
        query = supabase.table("ads").select("*")
        
        if search:
            query = query.ilike("title", f"%{search}%")
        
        if networks:
            query = query.in_("network", networks)
            
        if min_impressions > 0:
            query = query.gte("impressions", min_impressions)
            
        # الترتيب
        if sort_by == "newest":
            query = query.order("created_at", ascending=False)
        elif sort_by == "oldest":
            query = query.order("created_at", ascending=True)
        elif sort_by == "impressions":
            query = query.order("impressions", ascending=False)
            
        # التنقل (Pagination)
        query = query.range(offset, offset + limit - 1)
        
        res = query.execute()
        return res.data if res.data else []
    except Exception as e:
        print(f"Error fetching ads: {e}")
        return []

@st.cache_data(ttl=300)
def get_stats():
    try:
        # إحصائيات سريعة
        total_ads = supabase.table("ads").select("id", count="exact").execute().count
        today_ads = supabase.table("ads").select("id", count="exact").gte("created_at", "now() - interval '24 hours'").execute().count
        top_network = "MGID" # تجريبي، يمكن حسابها بدقة برمجياً
        return {
            "total_ads": total_ads or 0,
            "today_ads": today_ads or 0,
            "trending": 0, # سيتم حسابه لاحقاً
            "top_network": top_network
        }
    except:
        return {"total_ads": 0, "today_ads": 0, "trending": 0, "top_network": "N/A"}

# --- 3. وظائف المستخدمين ---
def get_user_by_email(email):
    try:
        res = supabase.table("users").select("*").eq("email", email).execute()
        return res.data[0] if res.data else None
    except:
        return None

def insert_user(user_data):
    try:
        res = supabase.table("users").insert(user_data).execute()
        return res.data[0] if res.data else None
    except Exception as e:
        print(f"Error inserting user: {e}")
        return None

def update_user(user_id, updates):
    try:
        supabase.table("users").update(updates).eq("id", user_id).execute()
        return True
    except:
        return False

# --- 4. المفضلة (Favorites) ---
def get_favorites(user_id):
    try:
        res = supabase.table("favorites").select("ad_id").eq("user_id", user_id).execute()
        ad_ids = [row['ad_id'] for row in res.data] if res.data else []
        if not ad_ids: return []
        
        ads_res = supabase.table("ads").select("*").in_("id", ad_ids).execute()
        return ads_res.data if ads_res.data else []
    except:
        return []

def toggle_favorite(user_id, ad_id):
    try:
        # التحقق من وجوده
        existing = supabase.table("favorites").select("id").eq("user_id", user_id).eq("ad_id", ad_id).execute()
        if existing.data:
            supabase.table("favorites").delete().eq("id", existing.data[0]['id']).execute()
            return "removed"
        else:
            supabase.table("favorites").insert({"user_id": user_id, "ad_id": ad_id}).execute()
            return "added"
    except:
        return "error"

# --- 5. استهلاك الذكاء الاصطناعي (AI Usage) ---
def increment_ai_usage(user_id):
    if user_id == "admin": return True
    try:
        user = supabase.table("users").select("ai_uses_today").eq("id", user_id).execute()
        if user.data:
            new_count = (user.data[0]['ai_uses_today'] or 0) + 1
            supabase.table("users").update({"ai_uses_today": new_count}).eq("id", user_id).execute()
            return True
    except:
        pass
    return False
