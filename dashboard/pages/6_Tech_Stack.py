import os, sys

# --- Ensure root directory is in sys.path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.auth_cookie import is_authenticated, inject_back_button_limiter, clear_auth, inject_navigation_blocker
import time

import streamlit as st

# --- Authentication Guard ---
# if 'authenticated' not in st.session_state or not st.session_state.authenticated:
#     st.warning("You are not logged in. Redirecting to login page...")
#     st.switch_page("login.py")


# --- 1. HIDE THE DEFAULT NAVIGATION SIDEBAR ---
# This hides Streamlit's built-in "page" sidebar introduced in multipage apps.import time
# --- CRITICAL FIX: Add initialization flag to prevent premature checks ---
if 'auth_initialized' not in st.session_state:
    st.session_state.auth_initialized = False

# --- Show loading screen during first load ---
if not st.session_state.auth_initialized:
    with st.spinner("Loading..."):
        time.sleep(0.3)  # Give time for session restoration
        st.session_state.auth_initialized = True
        st.rerun()

# --- NOW check authentication (after initialization) ---
inject_back_button_limiter()

if not is_authenticated():
    st.warning("⚠️ You are not logged in. Redirecting to login page...")
    time.sleep(0.5)
    st.switch_page("login.py")
    st.stop()

st.set_page_config(
    page_title="Tech Stack",
    page_icon="💻",
    layout="wide"
)

st.markdown(
    """
    <style>
        [data-testid="stSidebarNav"] {
            display: none;
        }
    </style>
    """,
    unsafe_allow_html=True,
)


def custom_sidebar():
    with st.sidebar:
        st.title("Admin Menu")
        st.page_link("pages/1_Users.py", label="Users", icon="👥")
        st.page_link("pages/2_Schedules.py", label="Schedules", icon="🗓️")
        st.page_link("pages/3_Call_Console.py", label="Call Console", icon="📞")
        st.page_link("pages/4_Analytics.py", label="Analytics", icon="📊")
        st.page_link("pages/5_Settings.py", label="Settings", icon="⚙️")
        st.page_link("pages/6_Tech_Stack.py", label="Tech Stack", icon="💻")
        st.markdown("---")

        # Show session info
        if st.session_state.get('login_time'):
            from datetime import datetime
            try:
                login_time = datetime.fromisoformat(st.session_state.login_time)
                st.caption(f"🕐 Logged in: {login_time.strftime('%I:%M %p')}")
            except:
                pass

        # Initialize logout confirmation state
        if 'show_logout_confirmation' not in st.session_state:
            st.session_state.show_logout_confirmation = False

        # Logout button - triggers confirmation dialog
        if st.button("🚪 Logout", key="logout_button", use_container_width=True, type="primary"):
            st.session_state.show_logout_confirmation = True
            st.rerun()

    # Logout Confirmation Dialog (outside sidebar)
    if st.session_state.get('show_logout_confirmation', False):
        @st.dialog("Confirm Logout")
        def logout_confirmation_dialog():
            st.warning("⚠️ Are you sure you want to logout?")

            col1, col2 = st.columns(2)

            with col1:
                if st.button("✅ Yes, Logout", type="primary", use_container_width=True):
                    # Clear authentication
                    clear_auth()

                    # Clear all session state except auth flags
                    keys_to_preserve = ['authenticated', 'logout_triggered']
                    for key in list(st.session_state.keys()):
                        if key not in keys_to_preserve:
                            del st.session_state[key]

                    st.success("✅ Logged out successfully!")
                    inject_navigation_blocker()

                    time.sleep(0.5)
                    st.switch_page("login.py")

            with col2:
                if st.button("❌ Cancel", use_container_width=True):
                    st.session_state.show_logout_confirmation = False
                    st.rerun()

        logout_confirmation_dialog()


# --- Call the sidebar function at the top of the page ---
custom_sidebar()

st.title("💻 Tech Stack & Local Setup")

# --- Display the local image ---
# # CORRECTED LINE: Assumes you created an 'assets' folder and saved the image there.
# st.image(
#     "assets/architecture.png",
#     caption="High-level architecture of the AI Mental Wellness Companion.",
#     use_container_width=True
# )

st.markdown("---")

# --- 1. Technology Stack Section ---
st.header("🛠️ Technology Stack")
st.markdown(
    """
    This Proof of Concept (POC) is built using a modern, open-source Python stack designed for rapid development and deployment of AI-powered web applications.
    """
)

tech_col1, tech_col2, tech_col3 = st.columns(3)

with tech_col1:
    with st.container(border=True):
        st.subheader("🐍 Backend API")
        st.markdown("- **Framework:** `FastAPI`")
        st.markdown(
            "- **Purpose:** Serves all data via REST endpoints, manages database interactions, and orchestrates the call logic.")

with tech_col2:
    with st.container(border=True):
        st.subheader("🧠 Conversation Workflow")
        st.markdown("- **Framework:** `LangGraph`")
        st.markdown("- **Purpose:** Manages the stateful, node-by-node conversation flow, from greeting to closing.")

with tech_col3:
    with st.container(border=True):
        st.subheader("🖥️ Frontend UI")
        st.markdown("- **Framework:** `Streamlit`")
        st.markdown(
            "- **Purpose:** Creates the interactive admin dashboard and the real-time call console you are using now.")

# --- CORRECTED DATABASE SECTION ---
st.markdown(
    """
    - **Database:** `MongoDB` for flexible, scalable storage of users, calls, and memories.
    - **Language:** `Python 3.11+`
    """
)

st.markdown("---")

# --- 2. How to Run Locally Section ---
st.header("🚀 How to Run Locally")
st.markdown("Follow these steps to set up and run the entire application on your local machine.")

st.subheader("1. Prerequisites")
st.markdown("- **Python:** Ensure you have Python 3.11 or newer installed.")
st.markdown("- **pip:** Python's package installer should be available.")
st.markdown("- **MongoDB:** A running instance of MongoDB is required.")

st.subheader("2. Clone the Repository")
st.markdown("First, get the source code from the repository.")
st.code("git clone <your-repository-url>\\ncd <repository-folder>", language="bash")

st.subheader("3. Install Dependencies")
st.markdown("Install all required Python libraries using the `requirements.txt` file.")
st.code("pip install -r requirements.txt", language="bash")

st.subheader("4. Run the Backend Server")
st.markdown("Open a terminal and start the FastAPI backend server. It will typically run on `http://127.0.0.1:8000`.")
st.code("uvicorn main:app --reload", language="bash")

st.subheader("5. Run the Frontend Application")
st.markdown("Open a **second terminal** and run the Streamlit application. This is the dashboard you see now.")
st.code("streamlit run login.py", language="bash")

st.success(
    "Once both services are running, you can access the Streamlit dashboard in your browser, "
    "and it will be able to communicate with the FastAPI backend."
)