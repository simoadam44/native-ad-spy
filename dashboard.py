import streamlit as st
from supabase import create_client
import pandas as pd

# --- إعدادات الاتصال ---
SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.set_page_config(page_title="Simo Native Spy", layout="wide")

# --- نظام اللغات المطور ---
lang = st.sidebar.selectbox("🌐 Language / اللغة", ["ar", "en", "fr"])
trans = {
    "ar": {
        "title": "🕵️‍♂️ أداة تجسس سيمو", "sidebar": "⚙️ إعدادات الفلترة", "search": "🔍 ابحث عن كلمة...", 
        "net_filter": "📊 اختر الشبكة:", "count": "تم العثور على", "ads": "إعلان", 
        "imp": "الظهور", "net": "الشبكة", "first": "أول ظهور", "last": "آخر ظهور", "btn": "🚀 زيارة العرض"
    },
    "en": {
        "title": "🕵️‍♂️ Simo Native Spy", "sidebar": "⚙️ Filter Settings", "search": "🔍 Search keyword", 
        "net_filter": "📊 Choose network:", "count": "Found", "ads": "ads", 
        "imp": "Impressions", "net": "Network", "first": "First Seen", "last": "Last Seen", "btn": "🚀 Visit Ad"
    },
    "fr": {
        "title": "🕵️‍♂️ Simo Native Spy", "sidebar": "⚙️ Filtres", "search": "🔍 Rechercher...", 
        "net_filter": "📊 Réseau :", "count": "Trouvé", "ads": "annonces", 
        "imp": "Impressions", "net": "Réseau", "first": "1ère vue", "last": "Dernière vue", "btn": "🚀 Voir l'offre"
    }
}
t = trans[lang]

st.title(t["title"])

# --- جلب البيانات ---
@st.cache_data(ttl=60) # تقليل الكاش لتحديث أسرع للـ Impressions
def load_data():
    try:
        # نجلب البيانات مرتبة حسب آخر ظهور
        response = supabase.table("ads").select("*").order("last_seen", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"Error: {e}")
        return []

ads_data = load_data()

if ads_data:
    df = pd.DataFrame(ads_data)
    
    # تحويل التواريخ
    df['created_at'] = pd.to_datetime(df['created_at'])
    df['last_seen'] = pd.to_datetime(df['last_seen'])
    
    # --- القائمة الجانبية ---
    st.sidebar.header(t["sidebar"])
    search_query = st.sidebar.text_input(t["search"], "")
    
    # اختيار الشبكات
    available_networks = sorted(df['network'].dropna().unique().tolist())
    selected_networks = st.sidebar.multiselect(t["net_filter"], available_networks, default=available_networks)
    
    # --- منطق الفلترة ---
    df_filtered = df
    if selected_networks:
        df_filtered = df_filtered[df_filtered['network'].isin(selected_networks)]
        
    if search_query:
        df_filtered = df_filtered[df_filtered['title'].str.contains(search_query, case=False, na=False)]

    # ترتيب البيانات: الأكثر ظهوراً أولاً
    df_filtered = df_filtered.sort_values(by='impressions', ascending=False)

    st.write(f"{t['count']} **{len(df_filtered)}** {t['ads']}.")

    # --- عرض الإعلانات ---
    cols = st.columns(3) 
    for index, row in df_filtered.reset_index().iterrows():
        with cols[index % 3]:
            with st.container(border=True):
                # عرض الصورة مع التحقق من صحة الرابط
                img_url = row['image'] if row['image'] and row['image'].startswith('http') else "https://via.placeholder.com/400x250"
                st.image(img_url, use_container_width=True)
                
                # العنوان
                st.subheader(row['title'][:45] + "..." if len(row['title']) > 45 else row['title'])
                
                # معلومات الظهور والشبكة
                st.markdown(f"""
                <div style="background-color: rgba(255,255,255,0.05); padding: 10px; border-radius: 5px;">
                    <small>
                    🔥 <b>{t['imp']}:</b> {int(row['impressions'])} | 🌐 <b>{t['net']}:</b> {row['network']}<br>
                    🗓️ <b>{t['first']}:</b> {row['created_at'].strftime('%Y-%m-%d')}<br>
                    ⏳ <b>{t['last']}:</b> {row['last_seen'].strftime('%Y-%m-%d')}
                    </small>
                </div>
                """, unsafe_allow_html=True)
                
                st.write("") # مسافة بسيطة
                st.link_button(t['btn'], row['landing'], use_container_width=True)
else:
    st.info("No data / لا توجد بيانات. Run Crawler!")
