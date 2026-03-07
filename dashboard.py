# dashboard.py
import streamlit as st
from supabase import create_client

# إعدادات الاتصال بـ Supabase
SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# إعدادات الصفحة
st.set_page_config(page_title="Simo Native Spy", layout="wide")

st.title("🕵️‍♂️ Simo Native Spy Tool")
st.sidebar.header("إعدادات الفلترة")

# 1. جلب البيانات من Supabase
@st.cache_data(ttl=600) # تخزين مؤقت للبيانات لمدة 10 دقائق لتسريع اللوحة
def load_data():
    response = supabase.table("ads").select("*").order("created_at", desc=True).execute()
    return response.data

ads_data = load_data()

if ads_data:
    # --- قسم الفلترة في الشريط الجانبي ---
    search_query = st.sidebar.text_input("🔍 ابحث عن كلمة مفتاحية (مثل: Health, Crypto)", "")
    
    # استخراج قائمة المواقع المصدر الفريدة للفلترة
    all_sources = sorted(list(set([ad["source"] for ad in ads_data])))
    source_filter = st.sidebar.multiselect("🌐 اختر مواقع محددة:", all_sources, default=all_sources)

    # --- تطبيق الفلترة على البيانات ---
    filtered_ads = [
        ad for ad in ads_data 
        if (search_query.lower() in ad["title"].lower()) and (ad["source"] in source_filter)
    ]

    st.write(f"تم العثور على **{len(filtered_ads)}** إعلان.")

    # --- عرض الإعلانات في شبكة (Grid) ---
    cols = st.columns(3) # عرض 3 إعلانات في كل صف
    
    for index, ad in enumerate(filtered_ads):
        with cols[index % 3]:
            st.markdown(f"""
                <div style="border: 1px solid #ddd; padding: 10px; border-radius: 10px; margin-bottom: 20px; background-color: #f9f9f9;">
                    <img src="{ad['image']}" style="width: 100%; border-radius: 5px; height: 150px; object-fit: cover;">
                    <h4 style="height: 60px; overflow: hidden; font-size: 16px;">{ad['title']}</h4>
                    <p style="font-size: 12px; color: gray;">المصدر: {ad['source']}</p>
                    <a href="{ad['landing']}" target="_blank" style="display: block; text-align: center; background-color: #ff4b4b; color: white; padding: 5px; border-radius: 5px; text-decoration: none;">زيارة العرض</a>
                </div>
            """, unsafe_allow_html=True)

else:
    st.info("لم يتم العثور على بيانات في قاعدة البيانات حالياً.")
