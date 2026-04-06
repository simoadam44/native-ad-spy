import bcrypt
import streamlit as st
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from utils.db import get_user_by_email, insert_user, update_user

ADMIN_PASSWORD = os.environ.get("ADMIN_PASSWORD", "admin123")

def hash_password(password: str) -> str:
    salt = bcrypt.gensalt()
    return bcrypt.hashpw(password.encode(), salt).decode()

def verify_password(password: str, hashed: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode(), hashed.encode())
    except:
        return False

def check_user(email, password):
    # --- 1. التحقق من المسؤول (Admin) ---
    if email == "admin" and password == ADMIN_PASSWORD:
        return {
            "id": "admin",
            "email": "admin",
            "plan": "agency",
            "is_admin": True
        }
    
    # --- 2. التحقق من المستخدم في قاعدة البيانات ---
    user = get_user_by_email(email)
    if user and verify_password(password, user['password_hash']):
        if not user['is_active']:
            st.error("Account is inactive. Please contact support.")
            return None
        return {
            "id": user['id'],
            "email": user['email'],
            "plan": user['plan'],
            "is_admin": False
        }
    return None

def create_user(email, password):
    # التحقق من وجود المستخدم مسبقاً
    if get_user_by_email(email):
        return None, "Email already exists."
    
    hashed = hash_password(password)
    user_data = {
        "email": email,
        "password_hash": hashed,
        "plan": "free",
        "is_active": True,
        "ai_uses_today": 0
    }
    
    new_user = insert_user(user_data)
    if new_user:
        return new_user, None
    return None, "Error creating account. Please try again."

def update_last_login(user_id):
    if user_id == "admin": return
    update_user(user_id, {"last_login": "now()"})

def reset_daily_ai_usage(user_id):
    if user_id == "admin": return
    update_user(user_id, {"ai_uses_today": 0})
