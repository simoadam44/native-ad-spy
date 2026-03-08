import streamlit as st
from supabase import create_client
import pandas as pd

# ... (إعدادات الاتصال ثابتة كما هي) ...

# 1. نظام اللغات المحدث (مع الإنجليزية)
lang = st.sidebar.selectbox("🌐 Language / Langue / اللغة", ["ar", "en", "fr"])
trans = {
    "ar": {"title": "🕵️‍♂️ أداة تجسس سيمو", "sidebar": "⚙️ إعدادات الفلترة", "search": "🔍 ابحث عن كلمة مفتاحية", "net_filter": "📊 اختر شبكة الإعلانات:", "count": "تم العثور على", "ads": "إعلان فريد", "imp": "الظهور", "net": "الشبكة", "first": "أول ظهور", "last": "آخر ظهور", "btn": "🚀 زيارة العرض"},
    "en": {"title": "🕵️‍♂️ Simo Native Spy Tool", "sidebar": "⚙️ Filter Settings", "search": "🔍 Search keyword", "net_filter": "📊 Choose ad network:", "count": "Found", "ads": "unique ads", "imp": "Impressions", "net": "Network", "first": "First seen", "last": "Last seen", "btn": "🚀 Visit Offer"},
    "fr": {"title": "🕵️‍♂️ Simo Native Spy Tool", "sidebar": "⚙️ Paramètres de filtre", "search": "🔍 Rechercher par mot-clé", "net_filter": "📊 Choisir le réseau :", "count": "Trouvé", "ads": "annonces uniques", "imp": "Impressions", "net": "Réseau", "first": "1ère apparition", "last": "Dernière apparition", "btn": "🚀 Voir l'offre"}
}
t = trans[lang]

st.title(t["title"])
st.sidebar.header(t["sidebar"]) # تم ربط العنوان بالترجمة

# ... (دالة load_data كما هي) ...

if ads_data:
    df = pd.DataFrame(ads_data)
    df['created_at'] = pd.to_datetime(df['created_at'])
    
    # الفلترة
    search_query = st.sidebar.text_input(t["search"], "")
    available_networks = sorted(df['network'].dropna().unique().tolist())
    
    # الحل: وضع الخيار الافتراضي هو كل الشبكات
    selected_networks = st.sidebar.multiselect(t["net_filter"], available_networks, default=available_networks)
    
    # المنطق الصحيح: إذا لم يتم اختيار شيء، اعرض الكل
    if not selected_networks:
        df_filtered = df
    else:
        df_filtered = df[df['network'].isin(selected_networks)]
        
    if search_query:
        df_filtered = df_filtered[df_filtered['title'].str.contains(search_query, case=False, na=False)]

    # تجميع البيانات
    grouped_df = df_filtered.groupby(['landing', 'network']).agg({
        'title': 'first', 'image': 'first', 'source': 'first',
        'created_at': ['count', 'min', 'max']
    })
    grouped_df.columns = ['title', 'image', 'source', 'impressions', 'first_seen', 'last_seen']
    grouped_df = grouped_df.reset_index().sort_values(by='impressions', ascending=False)

    st.write(f"{t['count']} **{len(grouped_df)}** {t['ads']}.")
    
    # ... (باقي كود العرض كما هو) ...
