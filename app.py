import streamlit as st
import os

# --- 1. إعداد الصفحة الأولي ---
# ملاحظة: استدعاء set_page_config يتم هنا فقط في الملف الرئيسي
st.set_page_config(
    page_title="Native Spy - Premium Ad Insights",
    page_icon="🕵️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# --- 2. ستايل الواجهة الداكنة الفاخرة (Premium Dark Theme) ---
st.markdown("""
<style>
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
    
    [data-testid="stSidebar"] {
        background-color: #13131A;
        border-right: 1px solid #1C1C27;
    }
    
    .stMetric {
        background-color: #13131A;
        padding: 20px;
        border-radius: 15px;
        border: 1px solid #1C1C27;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. إدارة الجلسة ---
if "authenticated" not in st.session_state:
    st.session_state["authenticated"] = False

# --- 4. تعريف الصفحات (Modern Navigation) ---
login_page = st.Page("pages/login.py", title="Login", icon="🔑", default=(not st.session_state["authenticated"]))
dashboard_page = st.Page("pages/dashboard.py", title="Dashboard", icon="📊", default=st.session_state["authenticated"])
admin_page = st.Page("pages/admin.py", title="Admin Panel", icon="🔐")

# --- 5. منطق التنقل والبناء (Dynamic Navigation) ---
if not st.session_state["authenticated"]:
    # إذا لم يكن مسجلاً، اظهر صفحة تسجيل الدخول فقط
    pg = st.navigation([login_page], position="hidden")
else:
    # القوائم المتاحة بعد الدخول
    menu_pages = [dashboard_page]
    if st.session_state.get("is_admin", False):
        menu_pages.append(admin_page)
    
    # بناء الشريط الجانبي المطوّر
    with st.sidebar:
        st.title("🕵️ Native Spy")
        st.write(f"👤 {st.session_state.get('email', 'Guest')}")
        
        # بادج الخطة
        plan = st.session_state.get("plan", "free").upper()
        color = "#7C3AED" if plan == "AGENCY" else "#06B6D4" if plan == "PRO" else "#6B7280"
        st.markdown(f'<span style="background-color: {color}; padding: 5px 15px; border-radius: 20px; font-weight: bold; font-size: 12px;">{plan} PLAN</span>', unsafe_allow_html=True)
        
        st.divider()
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.clear()
            st.session_state["authenticated"] = False
            st.rerun()

    pg = st.navigation(menu_pages)

# تشغيل الصفحة المختارة
pg.run()
