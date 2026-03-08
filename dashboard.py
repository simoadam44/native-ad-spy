import streamlit as st
from supabase import create_client

# إعدادات الاتصال بـ Supabase
SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"

supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# إعدادات الصفحة
st.set_page_config(page_title="Simo Native Spy", layout="wide")

st.title("🕵️‍♂️ Simo Native Spy Tool")

# إضافة زر لتحديث البيانات يدوياً في الشريط الجانبي
if st.sidebar.button("🔄 تحديث البيانات الآن"):
    st.cache_data.clear()
    st.rerun()

st.sidebar.header("إعدادات الفلترة")

# 1. جلب البيانات من Supabase
@st.cache_data(ttl=300) # تقليل الوقت لـ 5 دقائق لسرعة التحديث
def load_data():
    try:
        response = supabase.table("ads").select("*").order("created_at", desc=True).execute()
        return response.data
    except Exception as e:
        st.error(f"خطأ في جلب البيانات: {e}")
        return []

ads_data = load_data()

if ads_data:
    # --- قسم الفلترة في الشريط الجانبي ---
    search_query = st.sidebar.text_input("🔍 ابحث عن كلمة مفتاحية", "")
    
    all_sources = sorted(list(set([ad["source"] for ad in ads_data])))
    source_filter = st.sidebar.multiselect("🌐 اختر مواقع محددة:", all_sources, default=all_sources)

    # --- تطبيق الفلترة ---
    filtered_ads = [
        ad for ad in ads_data 
        if (search_query.lower() in ad["title"].lower()) and (ad["source"] in source_filter)
    ]

    st.write(f"تم العثور على **{len(filtered_ads)}** إعلان.")

    # --- عرض الإعلانات في شبكة (Grid) ---
    # استخدام columns من Streamlit لعرض الصور بشكل أفضل
    cols = st.columns(3) 
    
    for index, ad in enumerate(filtered_ads):
        with cols[index % 3]:
            # إنشاء حاوية لكل إعلان
            with st.container(border=True):
                # عرض الصورة باستخدام دالة سريم ليت الرسمية
                if ad.get('image') and ad['image'].startswith('http'):
                    st.image(ad['image'], use_container_width=True)
                else:
                    st.image("https://via.placeholder.com/400x250?text=No+Image+Found", use_container_width=True)
                
                # العنوان والبيانات
                st.subheader(ad['title'][:60] + "..." if len(ad['title']) > 60 else ad['title'])
                st.caption(f"📍 المصدر: {ad['source']}")
                
                # زر الزيارة
                st.link_button("🚀 زيارة العرض", ad['landing'], use_container_width=True)

else:
    st.info("لم يتم العثور على بيانات في قاعدة البيانات حالياً. تأكد من تشغيل الكراولر.")
