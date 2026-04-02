import streamlit as st
import time
import os
from utils.auth import check_user, create_user, update_last_login

# --- 2. ستايل العرض المتميز (Premium Dark UI) ---
st.markdown("""
<style>
    /* إخفاء القائمة والأيقونات العلوية */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .stApp {
        background-color: #0A0A0F;
    }
    
    /* شكل الكارت المركزي */
    .login-container {
        max-width: 450px;
        margin: 100px auto auto;
        padding: 40px;
        background-color: #13131A;
        border-radius: 20px;
        box-shadow: 0 10px 30px rgba(0,0,0,0.5);
        border: 1px solid #1C1C27;
        text-align: center;
    }
    
    h1 {
        font-family: 'Syne', sans-serif;
        color: #F1F0F5;
        margin-bottom: 30px;
    }
</style>
""", unsafe_allow_html=True)

# --- 3. منطق الجلسة ---
def login_success(user):
    st.session_state["authenticated"] = True
    st.session_state["user_id"] = user["id"]
    st.session_state["email"] = user["email"]
    st.session_state["plan"] = user.get("plan", "free")
    st.session_state["is_admin"] = user.get("is_admin", False)
    
    # تحديث آخر موعد تسجيل دخول
    update_last_login(user["id"])
    
    st.success(f"Welcome back, {user['email']}!")
    time.sleep(1)
    st.rerun()

# --- 4. واجهة المستخدم ---
def main():
    st.markdown('<div class="login-container">', unsafe_allow_html=True)
    st.title("🕵️ Native Spy Tool")
    
    tab1, tab2 = st.tabs(["Login", "Register"])
    
    with tab1:
        with st.form("login_form"):
            email = st.text_input("Email", placeholder="your@email.com")
            password = st.text_input("Password", type="password")
            submitted = st.form_submit_button("Sign In")
            
            if submitted:
                if not email or not password:
                    st.error("Please fill all fields.")
                else:
                    user = check_user(email, password)
                    if user:
                        login_success(user)
                    else:
                        st.error("Invalid email or password.")
    
    with tab2:
        with st.form("register_form"):
            new_email = st.text_input("Email", placeholder="your@email.com")
            new_password = st.text_input("Password", type="password")
            confirm_pass = st.text_input("Confirm Password", type="password")
            reg_submitted = st.form_submit_button("Create Account")
            
            if reg_submitted:
                if not new_email or not new_password:
                    st.error("Please fill all fields.")
                elif new_password != confirm_pass:
                    st.error("Passwords do not match.")
                elif len(new_password) < 6:
                    st.error("Password too short.")
                else:
                    with st.spinner("Creating account..."):
                        user, error = create_user(new_email, new_password)
                        if user:
                            st.success("Account created! You can now login.")
                            time.sleep(1)
                        else:
                            st.error(error)
    
    st.markdown('</div>', unsafe_allow_html=True)

if __name__ == "__main__":
    main()
