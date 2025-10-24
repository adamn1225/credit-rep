import streamlit as st
import hashlib
import pandas as pd
from pathlib import Path

USERS_FILE = Path("users.csv")

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

def verify_password(password: str, hashed: str) -> bool:
    return hash_password(password) == hashed

def load_users():
    if USERS_FILE.exists():
        return pd.read_csv(USERS_FILE)
    else:
        return pd.DataFrame(columns=["username", "password_hash", "role"])

def save_user(username, password, role="user"):
    users = load_users()
    if username in users["username"].values:
        raise ValueError("User already exists")
    hashed = hash_password(password)
    users = pd.concat([users, pd.DataFrame([{"username": username, "password_hash": hashed, "role": role}])])
    users.to_csv(USERS_FILE, index=False)

def login_form():
    st.sidebar.subheader("🔐 Login")
    username = st.sidebar.text_input("Username")
    password = st.sidebar.text_input("Password", type="password")
    if st.sidebar.button("Login"):
        users = load_users()
        user = users[users["username"] == username]
        if not user.empty and verify_password(password, user.iloc[0]["password_hash"]):
            st.session_state["auth_user"] = username
            st.session_state["role"] = user.iloc[0]["role"]
            st.success(f"Welcome, {username}!")
            st.experimental_rerun()
        else:
            st.error("Invalid credentials.")

def logout_button():
    if "auth_user" in st.session_state:
        if st.sidebar.button("Logout"):
            del st.session_state["auth_user"]
            del st.session_state["role"]
            st.experimental_rerun()
