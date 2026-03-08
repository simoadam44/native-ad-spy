import streamlit as st
from supabase import create_client
import pandas as pd # مكتبة أساسية لتحليل البيانات

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
        st.error(f"خطأ: {e}")
        return []

ads_data = load_data()

if ads_data:
    # --- تحويل البيانات إلى DataFrame لتسهيل التجميع ---
    df = pd.DataFrame(ads_data)
    
    # تجميع البيانات حسب رابط الإعلان (Landing) وحساب عدد مرات التكرار (Impressions)
    # نأخذ أول عنوان وأول صورة وجدناها لهذا الرابط
    grouped_df = df.groupby(['landing']).agg({
        'title': 'first',
        'image': 'first',
        'source': 'first',
        'landing': 'count' # يحسب عدد التكرارات
    }).rename(columns={'landing': 'impressions'}).reset_index()

    # ترتيب حسب الأكثر تكراراً
    grouped_df = grouped_df.sort_values(by='impressions', ascending=False)

    # --- الفلترة ---
    search_query = st.sidebar.text_input("🔍 ابحث عن كلمة مفتاحية", "")
    filtered_df = grouped_df[grouped_df['title'].str.contains(search_query, case=False, na=False)]

    st.write(f"تم العثور على **{len(filtered_df)}** إعلان فريد.")

    # --- العرض ---
    cols = st.columns(3) 
    for index, row in filtered_df.iterrows():
        with cols[index % 3]:
            with st.container(border=True):
                if row['image'] and row['image'].startswith('http'):
                    st.image(row['image'], use_container_width=True)
                else:
                    st.image("https://via.placeholder.com/400x250?text=No+Image", use_container_width=True)
                
                st.subheader(row['title'][:50] + "..." if len(row['title']) > 50 else row['title'])
                
                # إضافة عداد مرات الظهور
                st.metric(label="📊 مرات الظهور (Impressions)", value=int(row['impressions']))
                
                st.caption(f"📍 المصدر: {row['source']}")
                st.link_button("🚀 زيارة العرض", row['landing'], use_container_width=True)

else:
    st.info("لا توجد بيانات حالياً.")
