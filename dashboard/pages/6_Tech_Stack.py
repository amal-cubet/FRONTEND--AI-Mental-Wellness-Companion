import streamlit as st

# --- 1. HIDE THE DEFAULT NAVIGATION SIDEBAR ---
# This hides Streamlit's built-in "page" sidebar introduced in multipage apps.
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

# --- CUSTOM SIDEBAR ---
def custom_sidebar():
    with st.sidebar:
        st.title("Admin Menu")
        st.page_link("pages/1_Users.py", label="Users", icon="👥")
        st.page_link("pages/2_Schedules.py", label="Schedules", icon="🗓️")
        st.page_link("pages/3_Call_Console.py", label="Call Console", icon="📞")
        st.page_link("pages/4_Analytics.py", label="Analytics", icon="📊")
        st.page_link("pages/5_Settings.py", label="Settings", icon="⚙️")
        st.page_link("pages/6_Tech_Stack.py", label="Tech Stack", icon="💻")

        # Add a divider
        st.markdown("---")

        # Logout Button
        if st.button("Logout", key="logout_button"):
            # Clear the session state
            for key in st.session_state.keys():
                del st.session_state[key]
            # Redirect to the login page
            st.switch_page("login.py")

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
        st.markdown("- **Purpose:** Serves all data via REST endpoints, manages database interactions, and orchestrates the call logic.")

with tech_col2:
    with st.container(border=True):
        st.subheader("🧠 Conversation Workflow")
        st.markdown("- **Framework:** `LangGraph`")
        st.markdown("- **Purpose:** Manages the stateful, node-by-node conversation flow, from greeting to closing.")

with tech_col3:
    with st.container(border=True):
        st.subheader("🖥️ Frontend UI")
        st.markdown("- **Framework:** `Streamlit`")
        st.markdown("- **Purpose:** Creates the interactive admin dashboard and the real-time call console you are using now.")

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