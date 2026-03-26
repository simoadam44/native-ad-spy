import streamlit as st
import os

# --- 1. إعداد الصفحة الأولي ---
st.set_page_config(
    page_title="Native Spy - Premium Ad Insights",
    page_icon="🕵️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. ستايل الواجهة الداكنة الفاخرة (Premium Dark Theme) ---
st.markdown("""
<style>
    /* تحميل خطوط جوجل */
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Syne:wght@700&display=swap');
    
    html, body, [class*="css"] {
        font-family: 'DM Sans', sans-serif;
        background-color: #0A0A0F;
        color: #F1F0F5;
    }
    
    h1, h2, h3 {
        font-family: 'Syne', sans-serif;
        color: #FFFFFF;
    }
    
    /* ستايل الشريط الجانبي */
    [data-testid="stSidebar"] {
        background-color: #13131A;
        border-right: 1px solid #1C1C27;
    }
    
    /* ستايل الكروت البراقة */
    .stMetric {
        background-color: #13131A;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #1C1C27;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. إدارة الجلسة والتحقق من الهوية ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

if not st.session_state["authenticated"]:
    # الانتقال لصفحة تسجيل الدخول إذا لم يكن مسجلاً
    st.switch_page("pages/login.py")

# --- 4. الشريط الجانبي (SaaS Sidebar) ---
with st.sidebar:
    st.title("🕵️ Native Spy")
    st.write(f"👤 {st.session_state.get('email', 'Guest')}")
    
    # بادج الخطة
    plan = st.session_state.get("plan", "free").upper()
    color = "#7C3AED" if plan == "AGENCY" else "#06B6D4" if plan == "PRO" else "#6B7280"
    st.markdown(f'<span style="background-color: {color}; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 12px;">{plan} PLAN</span>', unsafe_allow_html=True)
    
    st.divider()
    
    # التنقل
    if st.button("📊 Dashboard", use_container_width=True):
        st.switch_page("pages/dashboard.py")
        
    if st.session_state.get("is_admin", False):
        if st.button("🔐 Admin Panel", use_container_width=True):
            st.switch_page("pages/admin.py")
            
    st.divider()
    
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 5. الصفحة الرئيسية (مرحباً) ---
st.title("Welcome to Native Spy 🚀")
st.write("Select a tool from the sidebar to get started.")

# عرض إحصائيات سريعة في الصفحة الرئيسية
from utils.db import get_stats
stats = get_stats()

col1, col2, col3, col4 = st.columns(4)
col1.metric("Total Ads", stats['total_ads'], "+12%")
col2.metric("New Today", stats['today_ads'], "Fresh")
col3.metric("Trending", stats['trending'], "🔥")
col4.metric("Top Network", stats['top_network'], "Live")

st.info("💡 Pro Tip: Use the AI Analysis tool in the Dashboard to discover winning angles!")
