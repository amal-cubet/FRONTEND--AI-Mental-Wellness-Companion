import streamlit as st
import requests
import pandas as pd
from datetime import time as dt_time

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

st.title("🗓️ Call Schedules")
st.markdown("Set up recurring daily call times for each user.")

# --- ROBUST STATE MANAGEMENT INITIALIZATION ---
if 'schedule_user_id' not in st.session_state:
    st.session_state.schedule_user_id = None
if 'current_schedule' not in st.session_state:
    st.session_state.current_schedule = []

# --- 1. USER SELECTION ---
try:
    response = requests.get(backend_url + "/users/")
    if response.status_code == 200:
        users = response.json()
        user_names = [user['name'] for user in users]

        selected_user_name = st.selectbox(
            "Select a User to Schedule",
            user_names,
            index=None,
            placeholder="Select a user..."
        )

        if selected_user_name:
            user = next((u for u in users if u['name'] == selected_user_name), None)
            user_id = user['id']

            # --- FETCH SCHEDULE ONLY WHEN USER CHANGES (THIS IS THE FIX) ---
            if st.session_state.schedule_user_id != user_id:
                try:
                    schedule_response = requests.get(f"{backend_url}/schedule/{user_id}")
                    if schedule_response.status_code == 200:
                        schedule_data = schedule_response.json()
                        st.session_state.current_schedule = schedule_data.get("call_times", [])
                    else:
                        # This case handles backend errors, but for a new user, the backend should return an empty list.
                        st.session_state.current_schedule = []

                    # Update the session state to track the currently selected user
                    st.session_state.schedule_user_id = user_id
                    st.rerun()  # Rerun once to ensure the display is updated after fetching

                except Exception as e:
                    st.error(f"Failed to fetch schedule: {e}")
                    st.session_state.current_schedule = []

            st.subheader(f"Schedule for {user['name']}")

            # --- Display and Manage Schedule Times ---
            if st.session_state.current_schedule:
                st.write("Current scheduled times:")
                for i, time_str in enumerate(st.session_state.current_schedule):
                    col1, col2 = st.columns([4, 1])
                    col1.success(time_str)
                    if col2.button(f"🗑️", key=f"del_{i}", use_container_width=True):
                        st.session_state.current_schedule.pop(i)
                        st.rerun()
            else:
                st.info("This user has no scheduled calls. Add a time below.")

            st.markdown("---")

            # --- Add New Time ---
            st.subheader("Add a New Time")
            col_time, col_button = st.columns([2, 1])
            new_time = col_time.time_input("Select a time to add", value=dt_time(9, 0), step=1800)

            if col_button.button("Add Time", use_container_width=True):
                new_time_str = new_time.strftime("%H:%M")
                if new_time_str not in st.session_state.current_schedule:
                    st.session_state.current_schedule.append(new_time_str)
                    st.session_state.current_schedule.sort()
                    st.rerun()
                else:
                    st.warning(f"The time {new_time_str} is already in the schedule.")

            st.markdown("---")

            # --- Save and Test Buttons ---
            final_col1, final_col2, final_col3 = st.columns([1, 1, 3])
            with final_col1:
                if st.button("💾 Save Schedule", type="primary", use_container_width=True):
                    schedule_payload = {
                        "user_id": user_id,
                        "call_times": st.session_state.current_schedule
                    }
                    try:
                        response = requests.post(f"{backend_url}/schedule/", json=schedule_payload)
                        if response.status_code == 200:
                            st.toast(f"Schedule for {user['name']} saved successfully!", icon="✅")
                        else:
                            st.error(f"Failed to save schedule. Error: {response.text}")
                    except Exception as e:
                        st.error(f"An error occurred: {e}")

            with final_col2:
                if st.button("▶️ Test Call Now", use_container_width=True):
                    st.session_state['user_for_call'] = user
                    st.success(f"Preparing test call for {user['name']}...")
                    time.sleep(1)
                    st.switch_page("pages/3_Call_Console.py")
    else:
        st.error("Could not fetch users from the backend.")
except requests.exceptions.ConnectionError:
    st.error("Connection Error: Could not connect to the backend. Is it running?")