import streamlit as st
from supabase import create_client
import pandas as pd

# إعدادات الاتصال بـ Supabase
SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# إعدادات الصفحة
st.set_page_config(page_title="Simo Native Spy", layout="wide")
st.title("🕵️‍♂️ Simo Native Spy Tool")

if st.sidebar.button("🔄 تحديث البيانات الآن"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.header("إعدادات الفلترة")

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
    
    # --- الفلترة المتقدمة ---
    search_query = st.sidebar.text_input("🔍 ابحث عن كلمة مفتاحية", "")
    
    # اختيار الشبكات
    available_networks = sorted(df['network'].dropna().unique().tolist())
    selected_networks = st.sidebar.multiselect("📊 اختر شبكة الإعلانات:", available_networks, default=available_networks)
    
    # تصفية البيانات أولاً
    df_filtered = df[df['network'].isin(selected_networks)]
    if search_query:
        df_filtered = df_filtered[df_filtered['title'].str.contains(search_query, case=False, na=False)]

    # --- تجميع البيانات (Groupby) ---
    grouped_df = df_filtered.groupby(['landing', 'network']).agg({
        'title': 'first',
        'image': 'first',
        'source': 'first',
        'landing': 'count'
    }).rename(columns={'landing': 'impressions'}).reset_index()

    grouped_df = grouped_df.sort_values(by='impressions', ascending=False)

    st.write(f"تم العثور على **{len(grouped_df)}** إعلان فريد.")

    # --- عرض الإعلانات ---
    cols = st.columns(3) 
    for index, row in grouped_df.iterrows():
        with cols[index % 3]:
            with st.container(border=True):
                if row['image'] and row['image'].startswith('http'):
                    st.image(row['image'], use_container_width=True)
                else:
                    st.image("https://via.placeholder.com/400x250?text=No+Image", use_container_width=True)
                
                st.subheader(row['title'][:50] + "..." if len(row['title']) > 50 else row['title'])
                
                # عرض الشبكة ومرات الظهور
                col1, col2 = st.columns(2)
                col1.metric("📊 الظهور", int(row['impressions']))
                col2.markdown(f"**الشبكة:**\n{row['network']}")
                
                st.caption(f"📍 المصدر: {row['source']}")
                st.link_button("🚀 زيارة العرض", row['landing'], use_container_width=True)

else:
    st.info("لا توجد بيانات حالياً. تأكد من تشغيل الكراولر.")
