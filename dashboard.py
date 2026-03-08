
import streamlit as st
from supabase import create_client
import pandas as pd

# إعدادات الاتصال بـ Supabase
SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# إعدادات الصفحة
st.set_page_config(page_title="Simo Native Spy", layout="wide")

# نظام اللغات
lang = st.sidebar.selectbox("🌐 Language / اللغة", ["ar", "fr"])
trans = {
    "ar": {"title": "🕵️‍♂️ Simo Native Spy Tool", "search": "🔍 ابحث عن كلمة مفتاحية", "net_filter": "📊 اختر شبكة الإعلانات:", "count": "تم العثور على", "ads": "إعلان فريد", "imp": "الظهور", "net": "الشبكة", "first": "أول ظهور", "last": "آخر ظهور", "btn": "🚀 زيارة العرض"},
    "fr": {"title": "🕵️‍♂️ Simo Native Spy Tool", "search": "🔍 Rechercher par mot-clé", "net_filter": "📊 Choisir le réseau :", "count": "Nombre d'annonces :", "ads": "annonces uniques", "imp": "Impressions", "net": "Réseau", "first": "1ère apparition", "last": "Dernière apparition", "btn": "🚀 Voir l'offre"}
}
t = trans[lang]

st.title(t["title"])

if st.sidebar.button("🔄 تحديث البيانات الآن"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.header("⚙️ إعدادات الفلترة")

@st.cache_data(ttl=300)
def load_data():
    try:
        response = supabase.table("ads").select("*").execute()
        return response.data
    except Exception as e:
        st.error(f"خطأ في الاتصال: {e}")
        return []

ads_data = load_data()

if ads_data:
    df = pd.DataFrame(ads_data)
    df['created_at'] = pd.to_datetime(df['created_at']) # تحويل التاريخ
    
    # الفلترة
    search_query = st.sidebar.text_input(t["search"], "")
    available_networks = sorted(df['network'].dropna().unique().tolist())
    selected_networks = st.sidebar.multiselect(t["net_filter"], available_networks, default=available_networks)
    
    df_filtered = df[df['network'].isin(selected_networks)]
    if search_query:
        df_filtered = df_filtered[df_filtered['title'].str.contains(search_query, case=False, na=False)]

    # تجميع البيانات
    grouped_df = df_filtered.groupby(['landing', 'network']).agg({
        'title': 'first',
        'image': 'first',
        'source': 'first',
        'created_at': ['count', 'min', 'max']
    })
    grouped_df.columns = ['title', 'image', 'source', 'impressions', 'first_seen', 'last_seen']
    grouped_df = grouped_df.reset_index().sort_values(by='impressions', ascending=False)

    st.write(f"{t['count']} **{len(grouped_df)}** {t['ads']}.")

    # العرض
    cols = st.columns(3) 
    for index, row in grouped_df.iterrows():
        with cols[index % 3]:
            with st.container(border=True):
                if row['image'] and row['image'].startswith('http'):
                    st.image(row['image'], use_container_width=True)
                else:
                    st.image("https://via.placeholder.com/400x250?text=No+Image", use_container_width=True)
                
                st.subheader(row['title'][:45] + "..." if len(row['title']) > 45 else row['title'])
                
                # عرض البيانات بتنسيق صغير وأنيق
                st.markdown(f"""
                <small>
                📊 <b>{t['imp']}:</b> {int(row['impressions'])} | 🌐 <b>{t['net']}:</b> {row['network']} <br>
                🗓️ <b>{t['first']}:</b> {str(row['first_seen'])[:10]} <br>
                ⏳ <b>{t['last']}:</b> {str(row['last_seen'])[:10]}
                </small>
                """, unsafe_allow_html=True)
                
                st.link_button(t['btn'], row['landing'], use_container_width=True)
else:
    st.info("لا توجد بيانات حالياً.")
