import streamlit as st
import sys, os, time

# --- Ensure root directory is in sys.path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.auth_cookie import set_auth_cookie, is_authenticated

# --- Streamlit Page Config ---
st.set_page_config(page_title="Login", page_icon="🔐", layout="centered")

if is_authenticated():
    st.success("✅ Already logged in! Redirecting...")
    time.sleep(0.5)
    st.switch_page("pages/1_Users.py")
    st.stop()

# --- Hide Sidebar ---
st.markdown("""
    <style>
        [data-testid="stSidebar"] {display: none;}
        [data-testid="collapsedControl"] {display: none;}
    </style>
""", unsafe_allow_html=True)

# --- Page Title ---
st.title("AI-Mental Wellness Companion")
st.write("Your friendly companion for elderly mental wellness 💬")

# --- ONLY CHECK AFTER PAGE LOADS - Remove premature redirect ---
# DON'T put is_authenticated() check here at the top

# --- Login Form ---
st.subheader("Admin Login")

# Initialize error states
if "username_error" not in st.session_state:
    st.session_state.username_error = ""
if "password_error" not in st.session_state:
    st.session_state.password_error = ""
if "general_error" not in st.session_state:
    st.session_state.general_error = ""

username = st.text_input("Username")
if st.session_state.username_error:
    st.error(st.session_state.username_error)

password = st.text_input("Password", type="password")
if st.session_state.password_error:
    st.error(st.session_state.password_error)

if st.session_state.general_error:
    st.error(st.session_state.general_error)

# --- Handle Login Logic ---
if st.button("Login"):
    st.session_state.username_error = ""
    st.session_state.password_error = ""
    st.session_state.general_error = ""

    correct_username = "admin"
    correct_password = "admin"

    if username == correct_username and password == correct_password:
        # ✅ Set authentication FIRST
        set_auth_cookie()

        # ✅ Then show success message
        st.success("✅ Login successful! Redirecting...")

        # ✅ Wait a bit for session state to propagate
        time.sleep(0.5)

        st.rerun()

    elif username != correct_username and password == correct_password:
        st.session_state.username_error = "Incorrect username"
        st.rerun()
    elif username == correct_username and password != correct_password:
        st.session_state.password_error = "Incorrect password"
        st.rerun()
    else:
        st.session_state.general_error = "Wrong username or password"
        st.rerun()

# Footer
st.markdown("---")
st.caption("© 2025 AI-Mental Wellness Companion • Admin Portal")