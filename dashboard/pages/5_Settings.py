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

st.title("⚙️ Settings")


# --- INITIALIZE MOCK DATA IN SESSION STATE ---
def initialize_settings():
    if 'personas' not in st.session_state:
        st.session_state.personas = {
            "Friendly": "Start the conversation with a warm and cheerful tone. Use emojis and be very encouraging. Ask about their day and mention something positive.",
            "Calm": "Use a soothing and gentle tone. Speak slowly and clearly. Focus on creating a relaxing atmosphere. Avoid overly energetic language.",
            "Cheerful": "Be upbeat and positive. Use exclamation points where appropriate. Your goal is to bring a smile to their face and lift their spirits."
        }
    if 'conversation_template' not in st.session_state:
        st.session_state.conversation_template = ["Greeting", "Recall Memory", "Empathetic Check-in", "Topic Nudge",
                                                  "Closing"]


initialize_settings()

# --- 1. PERSONAS MANAGEMENT ---
st.header("🎭 Personas")
st.markdown("Manage the tone and style presets for the AI companion.")

persona_cols = st.columns(len(st.session_state.personas))

for i, (name, prompt) in enumerate(st.session_state.personas.items()):
    with persona_cols[i]:
        with st.container(border=True):
            st.subheader(name)

            with st.expander("View/Edit Prompt"):
                new_prompt = st.text_area(
                    f"Prompt for {name}",
                    value=prompt,
                    height=200,
                    key=f"prompt_{name}"
                )

                if st.button("Save", key=f"save_{name}"):
                    # In a real app, this would be an API call
                    st.session_state.personas[name] = new_prompt
                    st.toast(f"{name} persona updated!", icon="✅")
                    # No rerun needed, text_area updates automatically on button press

st.markdown("---")

# --- 2. CONVERSATION TEMPLATE ---
st.header("💬 Conversation Template")
st.markdown("Define the sequence of nodes for the conversation flow.")

col_template, col_actions = st.columns([2, 1])

with col_template:
    with st.container(border=True, height=300):
        # Display the list of nodes
        for index, node in enumerate(st.session_state.conversation_template):
            st.markdown(f"**{index + 1}. {node}**")

with col_actions:
    st.info("Drag-and-drop to reorder is a planned feature for a future version.")

    if st.button("Reset to Defaults", use_container_width=True):
        # Reset the state to the original list
        st.session_state.conversation_template = ["Greeting", "Recall Memory", "Empathetic Check-in", "Topic Nudge",
                                                  "Closing"]
        st.toast("Conversation template has been reset.", icon="🔄")
        st.rerun()