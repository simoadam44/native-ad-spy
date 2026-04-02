import streamlit as st
from utils.db import get_ads, get_stats, get_favorites, toggle_favorite, increment_ai_usage, supabase
from utils.auth import update_last_login
from utils.ai import analyze_ad, generate_similar, niche_report
import time

# --- 1. إعدادات الصفحة ---
# تم نقل set_page_config إلى app.py

PLANS = {
    "free":   {"ads_limit": 50,   "ai_limit": 0},
    "pro":    {"ads_limit": 9999, "ai_limit": 50},
    "agency": {"ads_limit": 9999, "ai_limit": 9999}
}
user_plan = st.session_state.get("plan", "free")
limits = PLANS.get(user_plan, PLANS["free"])

# جلب بيانات المستخدم الحالية (لاستهلاك الذكاء الاصطناعي)
try:
    user_data = supabase.table("users").select("ai_uses_today").eq("id", st.session_state["user_id"]).execute().data[0]
    ai_used = user_data.get("ai_uses_today", 0)
except:
    ai_used = 0

# (الستايل المتطور...)
st.markdown(f"""
<style>
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700&family=Syne:wght@700&display=swap');
    
    .stApp {{
        background-color: #0A0A0F;
        color: #F1F0F5;
        font-family: 'DM Sans', sans-serif;
    }}
    
    .ad-card {{ background-color: #13131A; border: 1px solid #1C1C27; border-radius: 15px; margin-bottom: 25px; transition: all 0.3s ease; overflow: hidden; }}
    .ad-card:hover {{ transform: translateY(-5px); border-color: #7C3AED; box-shadow: 0 10px 20px rgba(124, 58, 237, 0.2); }}
    .ad-image {{ width: 100%; height: 180px; object-fit: cover; border-bottom: 1px solid #1C1C27; }}
    .ad-content {{ padding: 15px; }}
    .ad-title {{ font-size: 16px; font-weight: 600; color: #F1F0F5; margin-bottom: 10px; display: -webkit-box; -webkit-line-clamp: 2; -webkit-box-orient: vertical; overflow: hidden; height: 44px; }}
    .network-badge {{ display: inline-block; padding: 2px 10px; border-radius: 10px; font-size: 10px; font-weight: bold; text-transform: uppercase; margin-right: 10px; }}
    .mgid {{ background-color: #7C3AED; color: white; }}
    .taboola {{ background-color: #06B6D4; color: white; }}
    .outbrain {{ background-color: #F59E0B; color: white; }}
    .revcontent {{ background-color: #EF4444; color: white; }}
    .impressions {{ color: #F59E0B; font-weight: bold; font-size: 14px; }}
    .stat-box {{ background-color: #13131A; border: 1px solid #1C1C27; border-radius: 12px; padding: 15px; text-align: center; }}
    
    .ai-analysis-box {{
        background: linear-gradient(135deg, #1e1b4b 0%, #13131A 100%);
        border: 1px solid #7C3AED;
        padding: 20px;
        border-radius: 15px;
        margin-top: 15px;
    }}
</style>
""", unsafe_allow_html=True)

# --- 5. الشريط الجانبي (Sidebar UI) ---
with st.sidebar:
    st.image("https://cdn-icons-png.flaticon.com/512/1041/1041916.png", width=60)
    st.markdown(f"### {st.session_state['email']}")
    plan_color = "#7C3AED" if user_plan == "agency" else "#06B6D4" if user_plan == "pro" else "#6B7280"
    st.markdown(f'<div style="background-color: {plan_color}; padding: 5px 15px; border-radius: 20px; text-align: center; font-weight: bold; font-size: 13px;">{user_plan.upper()} PLAN</div>', unsafe_allow_html=True)
    
    st.divider()
    if user_plan != "free":
        st.write(f"🤖 AI Credits: **{ai_used} / {limits['ai_limit']}**")
        st.progress(ai_used/limits['ai_limit'] if limits['ai_limit'] > 0 else 0)
    else:
        st.warning("Upgrade for AI features")
        
    st.divider()
    st.header("⚙️ Filters")
    search = st.text_input("Search Title", placeholder="Keyword...")
    networks = st.multiselect("Networks", ["Taboola", "MGID", "Outbrain", "Revcontent"], default=[])
    sort_by = st.selectbox("Sort By", ["newest", "oldest", "impressions"])
    min_imp = st.slider("Min Impressions", 0, 1000, 0)
    
    if st.button("🚪 Logout", use_container_width=True):
        st.session_state.clear()
        st.rerun()

# --- 6. واجهة العرض الرئيسية ---
st.title("📊 Ads Discovery")

tab_main, tab_favs, tab_report = st.tabs(["🚀 Global Ads", "❤️ My Favorites", "📈 Niche Report"])

with tab_main:
    stats = get_stats()
    c1, c2, c3, c4 = st.columns(4)
    with c1: st.markdown(f'<div class="stat-box"><small>Total Ads</small><h3>{stats["total_ads"]}</h3></div>', unsafe_allow_html=True)
    with c2: st.markdown(f'<div class="stat-box"><small>New Today</small><h3>{stats["today_ads"]}</h3></div>', unsafe_allow_html=True)
    with c3: st.markdown(f'<div class="stat-box"><small>Trending</small><h3>{stats["trending"]} 🔥</h3></div>', unsafe_allow_html=True)
    with c4: st.markdown(f'<div class="stat-box"><small>Top Network</small><h3>{stats["top_network"]}</h3></div>', unsafe_allow_html=True)
    st.write("")

    items_per_page = 30
    if "page_offset" not in st.session_state: st.session_state.page_offset = 0

    ads_data = get_ads(search=search, networks=networks, sort_by=sort_by, min_impressions=min_imp, limit=items_per_page, offset=st.session_state.page_offset)
    if user_plan == "free": ads_data = ads_data[:limits["ads_limit"]]

    if not ads_data:
        st.info("No ads found matching your filters.")
    else:
        for i in range(0, len(ads_data), 3):
            cols = st.columns(3)
            for j in range(3):
                if i + j < len(ads_data):
                    ad = ads_data[i+j]
                    with cols[j]:
                        with st.container():
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
                                        📅 First: {ad['created_at'][:10]}
                                    </div>
                                </div>
                            </div>
                            """, unsafe_allow_html=True)
                            
                            b_col1, b_col2, b_col3 = st.columns([1,1,1])
                            with b_col1:
                                st.link_button("🔗 Visit", ad['landing'], use_container_width=True)
                            with b_col2:
                                if st.button("🤖 AI", key=f"ai_{ad['id']}", use_container_width=True, disabled=(user_plan=="free" or ai_used >= limits['ai_limit'])):
                                    with st.spinner("Claude is analyzing..."):
                                        analysis = analyze_ad(ad['title'], ad['network'])
                                        if "error" not in analysis:
                                            increment_ai_usage(st.session_state["user_id"])
                                            st.session_state[f"ai_res_{ad['id']}"] = analysis
                                            st.rerun() # لتحديث Credits في الشريط الجانبي
                                        else:
                                            st.error(analysis["error"])
                            with b_col3:
                                if st.button("❤️", key=f"f_{ad['id']}", use_container_width=True):
                                    status = toggle_favorite(st.session_state["user_id"], ad['id'])
                                    st.toast("Saved!" if status == "added" else "Removed!")

                            if f"ai_res_{ad['id']}" in st.session_state:
                                res = st.session_state[f"ai_res_{ad['id']}"]
                                st.markdown(f"""
                                <div class="ai-analysis-box">
                                    <small style="color: #06B6D4;">HOOK:</small> {res.get('hook', 'N/A')}<br>
                                    <small style="color: #06B6D4;">ANGLE:</small> {res.get('angle', 'N/A')}<br>
                                    <small style="color: #7C3AED;">SCORE:</small> {res.get('score', '0')}/10<br>
                                    <hr style="border: 0.5px solid #1C1C27;">
                                    <strong>💡 Tip:</strong> {res.get('tip', 'N/A')}
                                </div>
                                """, unsafe_allow_html=True)
                            
                            with st.expander("Details"):
                                st.write(f"**Landing:** {ad['landing']}")
                                st.write(f"**Source:** {ad['source']}")
                                
    # Pagination
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

with tab_favs:
    st.header("Saved Ads")
    fav_ads = get_favorites(st.session_state["user_id"])
    if not fav_ads:
        st.write("You haven't saved any ads yet.")
    else:
        # عرض الإعلانات المفضلة بنفس التنسيق (مختصر هنا)
        for f_ad in fav_ads:
            st.write(f"✅ {f_ad['title']} ({f_ad['network']})")

with tab_report:
    st.header("Strategic Niche Report")
    selected_net = st.selectbox("Select Network for Analysis", ["MGID", "Taboola", "Outbrain", "Revcontent"])
    if st.button("Generate Niche Report", disabled=(user_plan=="free")):
        with st.spinner("Crunching data with Claude..."):
            report = niche_report(selected_net)
            if "error" not in report:
                st.subheader(f"Analyzing {selected_net}")
                st.write(f"**Dominant Angle:** {report['dominant_angle']}")
                st.write("**Top Hooks:**")
                for hook in report['top_hooks']: st.write(f"- {hook}")
                st.info(f"**Expert Tip:** {report['recommendation']}")
            else:
                st.error(report['error'])

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
