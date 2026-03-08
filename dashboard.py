
import streamlit as st
from supabase import create_client
import pandas as pd

# إعدادات الاتصال
SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Simo Native Spy", layout="wide")

# نظام اللغات
lang = st.sidebar.selectbox("🌐 Language / اللغة", ["ar", "en", "fr"])
trans = {
    "ar": {"title": "🕵️‍♂️ أداة تجسس سيمو", "sidebar": "⚙️ إعدادات الفلترة", "search": "🔍 ابحث عن كلمة...", "net_filter": "📊 اختر الشبكة:", "count": "تم العثور على", "ads": "إعلان", "imp": "الظهور", "net": "الشبكة", "first": "أول ظهور", "last": "آخر ظهور", "btn": "🚀 زيارة العرض"},
    "en": {"title": "🕵️‍♂️ Simo Native Spy", "sidebar": "⚙️ Filter Settings", "search": "🔍 Search keyword", "net_filter": "📊 Choose network:", "count": "Found", "ads": "ads", "imp": "Impressions", "net": "Network", "first": "First", "last": "Last", "btn": "🚀 Visit"},
    "fr": {"title": "🕵️‍♂️ Simo Native Spy", "sidebar": "⚙️ Filtres", "search": "🔍 Rechercher...", "net_filter": "📊 Réseau :", "count": "Trouvé", "ads": "annonces", "imp": "Impressions", "net": "Réseau", "first": "1ère vue", "last": "Dernière", "btn": "🚀 Voir"}
}
t = trans[lang]

st.title(t["title"])

@st.cache_data(ttl=300)
def load_data():
    try:
        response = supabase.table("ads").select("*").execute()
        return response.data
    except Exception:
        return []

# جلب البيانات (يجب أن يكون هنا لتعريف المتغير)
ads_data = load_data()

if ads_data:
    df = pd.DataFrame(ads_data)
    df['created_at'] = pd.to_datetime(df['created_at'])
    
    st.sidebar.header(t["sidebar"])
    search_query = st.sidebar.text_input(t["search"], "")
    
    available_networks = sorted(df['network'].dropna().unique().tolist())
    # استخدام multiselect
    selected_networks = st.sidebar.multiselect(t["net_filter"], available_networks, default=available_networks)
    
    # فلترة البيانات (المنطق الصحيح لعرض الكل إذا لم يتم اختيار شيء)
    if not selected_networks:
        df_filtered = df
    else:
        df_filtered = df[df['network'].isin(selected_networks)]
        
    if search_query:
        df_filtered = df_filtered[df_filtered['title'].str.contains(search_query, case=False, na=False)]

    # تجميع البيانات
    grouped_df = df_filtered.groupby(['landing', 'network']).agg({'title': 'first', 'image': 'first', 'source': 'first', 'created_at': ['count', 'min', 'max']})
    grouped_df.columns = ['title', 'image', 'source', 'impressions', 'first_seen', 'last_seen']
    grouped_df = grouped_df.reset_index().sort_values(by='impressions', ascending=False)

    st.write(f"{t['count']} **{len(grouped_df)}** {t['ads']}.")

    # العرض
    cols = st.columns(3) 
    for index, row in grouped_df.iterrows():
        with cols[index % 3]:
            with st.container(border=True):
                st.image(row['image'] if row['image'] and row['image'].startswith('http') else "https://via.placeholder.com/400x250", use_container_width=True)
                st.subheader(row['title'][:40] + "...")
                st.markdown(f"<small>📊 {t['imp']}: {int(row['impressions'])} | 🌐 {t['net']}: {row['network']} <br> 🗓️ {t['first']}: {str(row['first_seen'])[:10]} <br> ⏳ {t['last']}: {str(row['last_seen'])[:10]}</small>", unsafe_allow_html=True)
                st.link_button(t['btn'], row['landing'], use_container_width=True)
else:
    st.info("No data / لا توجد بيانات. Run Crawler!")
