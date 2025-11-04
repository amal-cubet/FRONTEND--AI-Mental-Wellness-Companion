# In pages/5_Settings.py

import streamlit as st
import requests

# --- 1. HIDE THE DEFAULT NAVIGATION SIDEBAR ---
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
        st.markdown("---")
        if st.button("Logout", key="logout_button"):
            for key in st.session_state.keys():
                del st.session_state[key]
            st.switch_page("login.py")


custom_sidebar()

backend_url = "http://127.0.0.1:8000"
st.title("⚙️ Settings")

# --- DEFAULT FALLBACK PERSONAS ---
DEFAULT_PERSONAS = {
    "Friendly": "Start the conversation with a warm and cheerful tone. Use emojis and be very encouraging. Ask about their day and mention something positive.",
    "Calm": "Use a soothing and gentle tone. Speak slowly and clearly. Focus on creating a relaxing atmosphere. Avoid overly energetic language.",
    "Cheerful": "Be upbeat and positive. Use exclamation points where appropriate. Your goal is to bring a smile to their face and lift their spirits."
}


# --- FETCH PERSONAS FROM BACKEND ---
@st.cache_data(ttl=300)  # Cache for 5 minutes
def fetch_personas():
    try:
        response = requests.get(f"{backend_url}/personas/")
        if response.status_code == 200:
            data = response.json()
            if data:
                st.toast("Fetched latest personas from database.", icon="☁️")
                return data
            else:
                st.warning("No personas found in database. Loading defaults.", icon="⚠️")
                return DEFAULT_PERSONAS
        else:
            st.error(f"Failed to fetch personas: {response.text}")
            return DEFAULT_PERSONAS
    except requests.exceptions.ConnectionError:
        st.error("Connection Error: Could not connect to backend. Loading default personas.")
        return DEFAULT_PERSONAS
    except Exception as e:
        st.error(f"An error occurred: {e}")
        return DEFAULT_PERSONAS


# Initialize session state with fetched data
if 'personas' not in st.session_state:
    st.session_state.personas = fetch_personas()

if 'conversation_template' not in st.session_state:
    st.session_state.conversation_template = ["Greeting", "Recall Memory", "Empathetic Check-in", "Topic Nudge",
                                              "Closing"]

# --- 1. PERSONAS MANAGEMENT ---
st.header("🎭 Personas")
st.markdown("Manage the tone and style presets for the AI companion.")

# Ensure we always display the core personas
persona_names = list(DEFAULT_PERSONAS.keys())

persona_cols = st.columns(len(persona_names))

for i, name in enumerate(persona_names):
    with persona_cols[i]:
        with st.container(border=True):
            st.subheader(name)

            # Get the current prompt from session state, falling back to default if key is missing
            current_prompt = st.session_state.personas.get(name, DEFAULT_PERSONAS[name])

            with st.expander("View/Edit Prompt"):
                new_prompt = st.text_area(
                    f"Prompt for {name}",
                    value=current_prompt,
                    height=200,
                    key=f"prompt_{name}"
                )

                if st.button("Save", key=f"save_{name}"):
                    # This is an API call to the backend
                    try:
                        payload = {"name": name, "prompt": new_prompt}
                        response = requests.post(f"{backend_url}/personas/", json=payload)

                        if response.status_code == 200:
                            st.toast(f"{name} persona updated successfully!", icon="✅")
                            # Update session state and clear cache to force refetch
                            st.session_state.personas[name] = new_prompt
                            st.cache_data.clear()
                            st.rerun()
                        else:
                            st.error(f"Failed to save: {response.text}")

                    except Exception as e:
                        st.error(f"An error occurred: {e}")

st.markdown("---")

# --- 2. CONVERSATION TEMPLATE ---
st.header("💬 Conversation Template")
st.markdown("Define the sequence of nodes for the conversation flow.")

col_template, col_actions = st.columns([2, 1])

with col_template:
    with st.container(border=True, height=300):
        for index, node in enumerate(st.session_state.conversation_template):
            st.markdown(f"**{index + 1}. {node}**")

with col_actions:
    st.info("Drag-and-drop to reorder is a planned feature for a future version.")

    if st.button("Reset to Defaults", use_container_width=True):
        st.session_state.conversation_template = ["Greeting", "Recall Memory", "Empathetic Check-in", "Topic Nudge",
                                                  "Closing"]
        st.toast("Conversation template has been reset.", icon="🔄")
        st.rerun()