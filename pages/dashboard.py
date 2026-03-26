import streamlit as st
import pandas as pd
from utils.db import get_ads, get_stats, supabase
from utils.auth import update_last_login
import time

# --- 1. إعداد الصفحة ---
st.set_page_config(page_title="Dashboard - Native Spy", layout="wide")

# --- 2. التحقق من الهوية ---
if "authenticated" not in st.session_state or not st.session_state["authenticated"]:
    st.switch_page("pages/login.py")

# --- 3. تعريف الخطط والحدود ---
PLANS = {
    "free":   {"ads_limit": 50,   "ai_limit": 0},
    "pro":    {"ads_limit": 9999, "ai_limit": 50},
    "agency": {"ads_limit": 9999, "ai_limit": 9999}
}
user_plan = st.session_state.get("plan", "free")
limits = PLANS.get(user_plan, PLANS["free"])

# --- 4. ستايل الواجهة الداكنة الفاخرة (Premium CSS) ---
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Syne:wght@700&display=swap');
    
    .stApp {{
        background-color: #0A0A0F;
        color: #F1F0F5;
        font-family: 'DM Sans', sans-serif;
    }}
    
    /* كارت الإعلان */
    .ad-card {{
        background-color: #13131A;
        border: 1px solid #1C1C27;
        border-radius: 15px;
        padding: 0px;
        margin-bottom: 25px;
        transition: all 0.3s ease;
        overflow: hidden;
    }}
    
    .ad-card:hover {{
        transform: translateY(-5px);
        border-color: #7C3AED;
        box-shadow: 0 10px 20px rgba(124, 58, 237, 0.2);
    }}
    
    .ad-image {{
        width: 100%;
        height: 180px;
        object-fit: cover;
        border-bottom: 1px solid #1C1C27;
    }}
    
    .ad-content {{
        padding: 15px;
    }}
    
    .ad-title {{
        font-size: 16px;
        font-weight: 600;
        color: #F1F0F5;
        margin-bottom: 10px;
        display: -webkit-box;
        -webkit-line-clamp: 2;
        -webkit-box-orient: vertical;
        overflow: hidden;
        height: 44px;
    }}
    
    .network-badge {{
        display: inline-block;
        padding: 2px 10px;
        border-radius: 10px;
        font-size: 10px;
        font-weight: bold;
        text-transform: uppercase;
        margin-right: 10px;
    }}
    
    .mgid {{ background-color: #7C3AED; color: white; }}
    .taboola {{ background-color: #06B6D4; color: white; }}
    .outbrain {{ background-color: #F59E0B; color: white; }}
    .revcontent {{ background-color: #EF4444; color: white; }}
    
    .impressions {{
        color: #F59E0B;
        font-weight: bold;
        font-size: 14px;
    }}
    
    /* شريط الإحصائيات */
    .stat-box {{
        background-color: #13131A;
        border: 1px solid #1C1C27;
        border-radius: 12px;
        padding: 15px;
        text-align: center;
    }}
</style>
""", unsafe_allow_html=True)

# --- 5. الشريط الجانبي (Sidebar UI) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1041/1041916.png", width=60)
    st.markdown(f"### {st.session_state['email']}")
    
    # بادج الخطة
    plan_color = "#7C3AED" if user_plan == "agency" else "#06B6D4" if user_plan == "pro" else "#6B7280"
    st.markdown(f'<div style="background-color: {plan_color}; padding: 5px 15px; border-radius: 20px; text-align: center; font-weight: bold; font-size: 13px;">{user_plan.upper()} PLAN</div>', unsafe_allow_html=True)
    
    st.divider()
    
    # عداد الذكاء الاصطناعي
    if user_plan != "free":
        st.write(f"🤖 AI Credits: **24 / {limits['ai_limit']}**")
        st.progress(24/limits['ai_limit'] if limits['ai_limit'] > 0 else 0)
    else:
        st.warning("Upgrade to PRO for AI features")
        
    st.divider()
    
    # الفلاتر (Filters)
    st.header("⚙️ Filters")
    search = st.text_input("Search Title", placeholder="Keyword...")
    networks = st.multiselect("Networks", ["Taboola", "MGID", "Outbrain", "Revcontent"], default=[])
    sort_by = st.selectbox("Sort By", ["newest", "oldest", "impressions"])
    min_imp = st.slider("Min Impressions", 0, 1000, 0)
    
    st.divider()
    
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 6. الصفحة الرئيسية للجولة (Main Dashboard) ---
st.title("📊 Ads Discovery")

# شريط الإحصائيات (Stats Bar)
stats = get_stats()
c1, c2, c3, c4 = st.columns(4)
with c1: st.markdown(f'<div class="stat-box"><small>Total Ads</small><h3>{stats["total_ads"]}</h3></div>', unsafe_allow_html=True)
with c2: st.markdown(f'<div class="stat-box"><small>New Today</small><h3>{stats["today_ads"]}</h3></div>', unsafe_allow_html=True)
with c3: st.markdown(f'<div class="stat-box"><small>Trending</small><h3>{stats["trending"]} 🔥</h3></div>', unsafe_allow_html=True)
with c4: st.markdown(f'<div class="stat-box"><small>Top Network</small><h3>{stats["top_network"]}</h3></div>', unsafe_allow_html=True)

st.write("")

# --- 7. جلب البيانات والمعالجة (Pagination) ---
items_per_page = 30
if "page_offset" not in st.session_state: st.session_state.page_offset = 0

ads_data = get_ads(
    search=search, 
    networks=networks, 
    sort_by=sort_by, 
    min_impressions=min_imp,
    limit=items_per_page,
    offset=st.session_state.page_offset
)

# تفعيل حدود الخطة المجانية
if user_plan == "free":
    ads_data = ads_data[:limits["ads_limit"]]

# --- 8. عرض شبكة الإعلانات (Ads Grid) ---
if not ads_data:
    st.info("No ads found matching your filters.")
else:
    # تقسيم العرض إلى 3 أعمدة
    for i in range(0, len(ads_data), 3):
        cols = st.columns(3)
        for j in range(3):
            if i + j < len(ads_data):
                ad = ads_data[i+j]
                with cols[j]:
                    with st.container():
                        # شكل الكارت باستخدام HTML
                        net_class = ad['network'].lower()
                        st.markdown(f"""
                        <div class="ad-card">
                            <img src="{ad['image']}" class="ad-image">
                            <div class="ad-content">
                                <div class="ad-title">{ad['title']}</div>
                                <div style="display: flex; justify-content: space-between; align-items: center; margin-top: 10px;">
                                    <span class="network-badge {net_class}">{ad['network']}</span>
                                    <span class="impressions">{ad['impressions']} 🔥</span>
                                </div>
                                <div style="font-size: 11px; color: #6B7280; margin-top: 5px;">
                                    📅 First: {ad['created_at'][:10]} | Last: {ad['last_seen'][:10] if ad['last_seen'] else 'Today'}
                                </div>
                            </div>
                        </div>
                        """, unsafe_allow_html=True)
                        
                        # أزرار التفاعل (Streamlit native for functionality)
                        btn_col1, btn_col2, btn_col3 = st.columns([1,1,1])
                        with btn_col1:
                            if st.button("🔗 Visit", key=f"v_{ad['id']}", use_container_width=True):
                                st.write(f"Opening: {ad['landing']}")
                        with btn_col2:
                            # تعطيل الذكاء الاصطناعي للمجانيين
                            if st.button("🤖 AI", key=f"ai_{ad['id']}", use_container_width=True, disabled=(user_plan=="free")):
                                st.toast("Coming Soon: AI Analysis!")
                        with btn_col3:
                            if st.button("❤️", key=f"f_{ad['id']}", use_container_width=True):
                                try:
                                    supabase.table("favorites").insert({
                                        "user_id": st.session_state["user_id"],
                                        "ad_id": ad['id']
                                    }).execute()
                                    st.toast("Added to Favorites!")
                                except:
                                    st.toast("Already in favorites!")
                        
                        # تفاصيل التوسيع (Expandable Details)
                        with st.expander("Show Details"):
                            st.write(f"**Full Title:** {ad['title']}")
                            st.write(f"**Landing URL:** {ad['landing']}")
                            st.write(f"**Source Site:** {ad['source']}")

# --- 9. التحكم في الصفحات (Pagination Controls) ---
st.divider()
p_col1, p_col2, p_col3 = st.columns([1,2,1])
with p_col1:
    if st.button("⬅️ Previous", disabled=(st.session_state.page_offset == 0)):
        st.session_state.page_offset -= items_per_page
        st.rerun()
with p_col3:
    if st.button("Next ➡️", disabled=(len(ads_data) < items_per_page)):
        st.session_state.page_offset += items_per_page
        st.rerun()
