import pandas as pd
import streamlit as st
import time
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
st.title("User Management")

# --- Initialize session_state ---
if "show_add_user_form" not in st.session_state:
    st.session_state["show_add_user_form"] = False

if 'show_memory_dialog' not in st.session_state:
    st.session_state.show_memory_dialog = False
if 'selected_user_for_dialog' not in st.session_state:
    st.session_state.selected_user_for_dialog = None


# --- START OF NEW CODE: EDIT USER FORM LOGIC ---
# Function to display the edit form in a container
def display_edit_form(user_info):
    with st.container(border=True):
        st.subheader(f"✏️ Editing AI Settings for: {user_info['name']}")

        with st.form(key="edit_user_form"):
            # Persona and topics are the only editable fields, as per the POC
            edited_persona = st.selectbox("Persona", ["Friendly", "Calm", "Cheerful"],
                                          index=["Friendly", "Calm", "Cheerful"].index(
                                              user_info.get('persona', 'Friendly')))
            topics_str = ", ".join(user_info.get('topics', []))
            edited_topics_str = st.text_area("Preferred Topics (comma-separated)", value=topics_str)

            # Form submission buttons
            col1, col2 = st.columns(2)
            with col1:
                if st.form_submit_button("💾 Save Changes", type="primary", use_container_width=True):
                    updated_topics = [topic.strip() for topic in edited_topics_str.split(',') if topic.strip()]
                    update_payload = {"persona": edited_persona, "topics": updated_topics}

                    try:
                        user_id = user_info['id']
                        response = requests.put(f"{backend_url}/users/{user_id}", json=update_payload)
                        if response.status_code == 200:
                            st.toast("User updated successfully!", icon="✅")
                            del st.session_state['user_to_edit']
                            st.rerun()
                        else:
                            st.error(f"Failed to update user. Error: {response.text}")
                    except Exception as e:
                        st.error(f"An error occurred: {e}")

            with col2:
                if st.form_submit_button("❌ Cancel", use_container_width=True):
                    del st.session_state['user_to_edit']
                    st.rerun()


# --- END OF NEW CODE: EDIT USER FORM LOGIC ---


# --- MAIN PAGE LOGIC ---

# If we are in "edit" mode, show the edit form and nothing else.
if 'user_to_edit' in st.session_state:
    display_edit_form(st.session_state['user_to_edit'])

# Otherwise, show the normal page content.
else:
    # --- UI Controls ---
    col1, col2 = st.columns(2)
    if col1.button("Add User"):
        st.session_state["show_add_user_form"] = True
    if col2.button("Existing Users"):
        st.session_state["show_add_user_form"] = False

    # --- Add User Form ---
    if st.session_state["show_add_user_form"]:
        with st.spinner("Loading Form..."):
            time.sleep(1)
        with st.form("new_user_form", clear_on_submit=True):
            st.subheader("New User Details")
            name = st.text_input("Name")
            persona = st.selectbox("Persona", ["Friendly", "Calm", "Cheerful"])
            topics = st.text_input("Preferred Topics (comma-separated)")
            notes = st.text_area("Notes for Admin")
            submitted = st.form_submit_button("Save User")
            if submitted:
                endpoint = backend_url + "/users/"
                topics_list = [topic.strip() for topic in topics.split(',') if topic.strip()]
                user_data = {"name": name, "persona": persona, "topics": topics_list, "notes": notes}
                try:
                    response = requests.post(endpoint, json=user_data)
                    if response.status_code == 200:
                        st.success("User added successfully!")
                        st.session_state["show_add_user_form"] = False
                        st.rerun()
                    else:
                        st.error("Failed to add user. Backend returned an error:")
                        st.json(response.json())
                except requests.exceptions.ConnectionError:
                    st.error("Connection Error: Could not connect to the backend. Is it running?")
                except Exception as e:
                    st.error(f"An unexpected error occurred: {e}")

    # --- Existing Users Display ---
    if not st.session_state["show_add_user_form"]:
        st.subheader("Existing Users")

        dialog_placeholder = st.empty()
        if st.session_state.show_memory_dialog:
            with dialog_placeholder.container(border=True):
                user_info = st.session_state.selected_user_for_dialog
                st.subheader(f"Memory for {user_info['name']}")
                st.write("This will show key-value memory cards.")
                st.info("TODO: Fetch and display memory from the backend.")
                st.json({"last_mood": "Positive", "daughter_name": "Anu"})
                if st.button("Close"):
                    st.session_state.show_memory_dialog = False
                    st.rerun()

        try:
            response = requests.get(backend_url + "/users/")
            if response.status_code == 200:
                users_data = response.json()
                if users_data:
                    df = pd.DataFrame(users_data)
                    st.session_state['users_df'] = df
                    df_display = df[['name', 'persona', 'topics', 'notes']].copy()
                    df_display['Action'] = ""
                    edited_df = st.data_editor(
                        df_display, hide_index=True, use_container_width=True,
                        disabled=['name', 'persona', 'topics', 'notes'],
                        column_config={
                            "Action": st.column_config.SelectboxColumn(
                                "Action",
                                options=["", "📞 Start Call", "🧠 View Memory", "✏️ Edit", "🗑️ Archive"],
                                help="Choose an action for this user",
                            ),
                            "topics": st.column_config.ListColumn("Topics"),
                        }
                    )

                    action_row_index = edited_df[edited_df['Action'] != ""].index
                    if not action_row_index.empty:
                        idx = action_row_index[0]
                        selected_action = edited_df.loc[idx, "Action"]
                        user_info = st.session_state['users_df'].iloc[idx].to_dict()

                        if selected_action == "📞 Start Call":
                            st.session_state['user_for_call'] = user_info  # <-- This line is now fixed
                            st.success(f"Preparing call for {user_info['name']}...")
                            st.switch_page("pages/3_Call_Console.py")

                        elif selected_action == "🧠 View Memory":
                            if not st.session_state.show_memory_dialog:
                                st.session_state.selected_user_for_dialog = user_info
                                st.session_state.show_memory_dialog = True
                                st.rerun()

                        elif selected_action == "✏️ Edit":
                            st.session_state['user_to_edit'] = user_info
                            st.rerun()

                        elif selected_action == "🗑️ Archive":
                            try:
                                user_id_to_delete = user_info['id']
                                response = requests.delete(f"{backend_url}/users/{user_id_to_delete}")
                                if response.status_code == 200:
                                    st.toast(f"User {user_info['name']} archived successfully!", icon="✅")
                                    st.rerun()
                                else:
                                    # THIS BLOCK IS NOW FIXED
                                    try:
                                        error_details = response.json()
                                        st.error(f"Failed to archive user. Backend Error: {error_details}")
                                    except ValueError:
                                        st.error(
                                            f"Failed to archive user. Status Code: {response.status_code}. (No error details from backend)")
                            except Exception as e:
                                st.error(f"An error occurred: {e}")
                else:
                    st.info("No users found. Add a new user to see them here.")
            else:
                st.error("Failed to retrieve users from the backend.")
        except requests.exceptions.ConnectionError:
            st.error("Connection Error: Could not connect to the backend. Is it running?")