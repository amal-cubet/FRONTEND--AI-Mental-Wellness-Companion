import streamlit as st

import sys, os

# --- Ensure root directory is in sys.path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

print("🧩 Added to sys.path:", project_root)


hide_sidebar_style = """
    <style>
        [data-testid="stSidebar"] {display: none;}
        [data-testid="collapsedControl"] {display: none;}
    </style>
"""
st.markdown(hide_sidebar_style, unsafe_allow_html=True)

st.title("AI-Mental Wellness Companion")
st.write("AI-Mental Wellness Companion act as a friendly companion for the elderly.")


if "user_role" in st.session_state and st.session_state["user_role"] == "admin":
    st.switch_page("pages/1_Users.py")


st.subheader("Admin Login")
username = st.text_input("Username")
password = st.text_input("Password", type="password")

if st.button("Login"):
    if username == "admin" and password == "admin":
        st.session_state["user_role"] = "admin"
        st.switch_page("pages/1_Users.py")
    else:
        st.error("Wrong username or password")