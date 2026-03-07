# dashboard.py
import streamlit as st
from supabase import create_client

# معلومات Supabase (نفس المعلومات التي في crawler.py)
SUPABASE_URL = "https://avxoumymzbioeabxfcca.supabase.co"
SUPABASE_KEY = "sb_publishable_oY3GKsFRckyg7qye4Ez_GA_j8HDEDLX"

# إنشاء العميل للتواصل مع Supabase
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

st.title("🕵️‍♂️ Native Ads Spy Dashboard")
st.markdown("عرض جميع الإعلانات المجمعة من المواقع المختلفة")

# جلب كل الإعلانات من جدول ads
response = supabase.table("ads").select("*").execute()
ads = response.data

if ads:
    for ad in ads:
        st.image(ad["image"], width=300)
        st.subheader(ad["title"])
        st.write(f"🔗 [Landing Page]({ad['landing']})")
        st.write(f"🌐 Source: {ad['source']}")
        st.markdown("---")
else:
    st.info("لا توجد إعلانات حتى الآن.")
