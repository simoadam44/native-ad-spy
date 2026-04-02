import streamlit as st
import pandas as pd
from utils.db import supabase
import plotly.express as px
import requests
import os

# --- 1. إعداد الصفحة والتحقق من الصلاحيات ---

if "is_admin" not in st.session_state or not st.session_state["is_admin"]:
    st.error("Unauthorized. Admin access required.")
    st.switch_page("pages/login.py")

# --- 2. ستايل الأدمين ---
st.markdown("""
<style>
    .admin-card {
        background-color: #13131A;
        padding: 20px;
        border-radius: 12px;
        border: 1px solid #1C1C27;
        margin-bottom: 20px;
    }
</style>
""", unsafe_allow_html=True)

st.title("🔐 Admin Control Center")

# --- 3. القسم الأول: نظرة عامة (Overview) ---
st.header("📈 Overview")
col1, col2, col3, col4 = st.columns(4)

# جلب بيانات من Supabase
try:
    users_res = supabase.table("users").select("id", count="exact").execute()
    total_users = users_res.count or 0
    ads_res = supabase.table("ads").select("id", count="exact").execute()
    total_ads = ads_res.count or 0
except:
    total_users, total_ads = 0, 0

with col1: st.metric("Total Users", total_users)
with col2: st.metric("Active Ads", total_ads)
with col3: st.metric("Revenue (Est)", "$1,240")
with col4: st.metric("AI Tokens Used", "45K")

# --- 4. القسم الثاني: إدارة المستخدمين (User Management) ---
st.divider()
st.header("👥 User Management")

try:
    users_data = supabase.table("users").select("*").execute().data
    df_users = pd.DataFrame(users_data)
    if not df_users.empty:
        # عرض الجدول
        st.dataframe(df_users[["email", "plan", "is_active", "created_at", "last_login"]], use_container_width=True)
        
        # إجراءات التعديل
        email_to_edit = st.selectbox("Select User to Manage", df_users["email"].tolist())
        col_p1, col_p2, col_p3 = st.columns(3)
        with col_p1:
            new_plan = st.selectbox("Change Plan", ["free", "pro", "agency"])
        with col_p2:
            is_active = st.checkbox("Active Account", value=True)
        with col_p3:
            if st.button("Apply Changes", use_container_width=True):
                supabase.table("users").update({"plan": new_plan, "is_active": is_active}).eq("email", email_to_edit).execute()
                st.success(f"Updated {email_to_edit} successfully!")
    else:
        st.info("No users found.")
except Exception as e:
    st.error(f"Error loading users: {e}")

# --- 5. القسم الثالث: التحكم في الـ Crawlers ---
st.divider()
st.header("🕷️ Crawler Control")

with st.container():
    st.markdown('<div class="admin-card">', unsafe_allow_html=True)
    c1, c2 = st.columns([2, 1])
    with c1:
        st.write("**Crawler Status:** Running smoothly ✅")
        st.write("**Last Run:** 2 hours ago")
        st.write("**Ads Scraped this week:** 1,420")
    with c2:
        if st.button("🚀 Trigger Full Scan", use_container_width=True):
            GITHUB_TOKEN = os.environ.get("GITHUB_TOKEN")
            REPO = "simoadam44/native-ad-spy" # استبدل بمسار المستودع الفعلي
            WORKFLOW_ID = "crawler.yml"
            
            if GITHUB_TOKEN:
                headers = {
                    "Authorization": f"Bearer {GITHUB_TOKEN}",
                    "Accept": "application/vnd.github+json",
                    "X-GitHub-Api-Version": "2022-11-28"
                }
                url = f"https://api.github.com/repos/{REPO}/actions/workflows/{WORKFLOW_ID}/dispatches"
                data = {"ref": "main"}
                
                res = requests.post(url, headers=headers, json=data)
                if res.status_code == 204:
                    st.success("GitHub Action Dispatched! Crawlers are starting...")
                else:
                    st.error(f"Failed to trigger: {res.text}")
            else:
                st.warning("GITHUB_TOKEN not configured in environment.")
    st.markdown('</div>', unsafe_allow_html=True)

# تحليل توزيع الإعلانات
st.divider()
st.header("📊 Network Distribution")
try:
    # جلب توزيع الشبكات
    ads_dist = supabase.table("ads").select("network").execute().data
    df_dist = pd.DataFrame(ads_dist)
    if not df_dist.empty:
        fig = px.pie(df_dist, names='network', title='Ads by Network', hole=.4, color_discrete_sequence=px.colors.sequential.RdBu)
        st.plotly_chart(fig, use_container_width=True)
except:
    st.info("No data for chart.")

st.divider()
st.caption("Native Spy Admin Panel v1.0.0")
