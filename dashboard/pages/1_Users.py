import sys
import os

# --- Ensure root directory is in sys.path ---
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from utils.auth_cookie import is_authenticated, inject_back_button_limiter, clear_auth, inject_navigation_blocker

# ===== NOW CONTINUE WITH REGULAR IMPORTS =====
import pandas as pd
import streamlit as st
import time
import requests
import re
import html

# --- Streamlit Page Config ---
st.set_page_config(page_title="Users", page_icon="👥", layout="wide")
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


# --- VALIDATION FUNCTIONS ---
def sanitize_phone_number(phone):
    """
    Sanitizes phone number by removing all non-numeric characters except + at the start.
    Returns: sanitized_phone_number
    """
    if not phone:
        return ""

    # Keep + if it's at the beginning
    has_plus = phone.strip().startswith('+')

    # Remove all non-numeric characters
    cleaned = re.sub(r'[^0-9]', '', phone)

    # Add back the + if it was there
    if has_plus:
        cleaned = '+' + cleaned

    return cleaned


def validate_phone_number(phone, raw_phone=""):
    """
    Validates phone number with comprehensive checks.
    Returns: (is_valid, error_message, sanitized_phone)
    """
    if not phone:
        return False, "Phone number is required", ""

    # Store raw input for potential re-display
    if not raw_phone:
        raw_phone = phone

    # Sanitize the phone number
    sanitized = sanitize_phone_number(phone)

    if not sanitized:
        return False, "Please enter a valid phone number", ""

    # Check if it contains only + (at start) and digits
    if sanitized.startswith('+'):
        digits_only = sanitized[1:]
    else:
        digits_only = sanitized

    if not digits_only.isdigit():
        return False, "Phone number must contain only digits", ""

    # Check length (8-15 digits, not counting the +)
    if len(digits_only) < 8:
        return False, "Phone number must be at least 8 digits long", ""

    if len(digits_only) > 15:
        return False, "Phone number cannot exceed 15 digits", ""

    # Check for invalid patterns (repeated digits, sequential patterns)
    # Pattern 1: All same digits (e.g., 1111111111)
    if re.match(r'^(\d)\1+$', digits_only):
        return False, "Phone number cannot contain only repeated digits (e.g., 111111)", ""

    # Pattern 2: Simple repeating patterns (e.g., 121212, 123123)
    if len(digits_only) >= 6:
        # Check for patterns like 121212
        if re.match(r'^(\d{2})\1{2,}$', digits_only) or re.match(r'^(\d{3})\1{2,}$', digits_only):
            return False, "Phone number contains an invalid repeating pattern", ""

    return True, "", sanitized


def validate_name(name):
    """
    Validates the name field with comprehensive checks.
    Returns: (is_valid, error_message)
    """
    if not name:
        return False, "Name is required"

    # Check for leading or trailing whitespace BEFORE trimming
    if name != name.strip():
        return False, "Name cannot have leading or trailing spaces"

    # Trim whitespace for further checks
    name = name.strip()

    if not name:
        return False, "Name cannot be only whitespace"

    # Check length (min 2, max 100)
    if len(name) < 2:
        return False, "Name must be at least 2 characters long"

    if len(name) > 100:
        return False, "Name cannot exceed 100 characters"

    # Check for consecutive repeated characters (e.g., "aaaaaaa")
    if re.search(r'(.)\1{9,}', name):  # 10 or more same characters in a row
        return False, "Name contains too many repeated characters"

    # Allow: letters (including accented), spaces, dots, hyphens, apostrophes
    pattern = r"^[a-zA-ZÀ-ÿ\s.\-']+$"

    if not re.match(pattern, name):
        return False, "Name can only contain letters, spaces, dots, hyphens, and apostrophes. No numbers or special characters."

    # Check for multiple consecutive spaces
    if '  ' in name:
        return False, "Name cannot contain multiple consecutive spaces"

    # XSS check - detect HTML/script tags
    if re.search(r'<[^>]*>', name):
        return False, "Name cannot contain HTML tags"

    return True, ""


def validate_topics(topics_str):
    """
    Validates and sanitizes the topics field.
    Returns: (is_valid, error_message, cleaned_topics_list)
    """
    if not topics_str or not topics_str.strip():
        return False, "At least one topic is required", []

    # Split by comma
    topics_list = [topic.strip() for topic in topics_str.split(',')]

    # Remove empty strings
    topics_list = [topic for topic in topics_list if topic]

    if not topics_list:
        return False, "Please provide at least one valid topic", []

    # Check for XSS in topics
    for topic in topics_list:
        if re.search(r'<[^>]*>', topic):
            return False, "Topics cannot contain HTML tags", []

    # Normalize: convert to lowercase and remove duplicates
    topics_list = list(set([topic.lower() for topic in topics_list]))

    # Check max topics limit (e.g., 10)
    if len(topics_list) > 10:
        return False, "Maximum 10 topics allowed", []

    # Check individual topic length
    for topic in topics_list:
        if len(topic) > 50:
            return False, "Each topic must be 50 characters or less", []
        if len(topic) < 2:
            return False, "Each topic must be at least 2 characters", []
        # Check for repeated characters in topics
        if re.search(r'(.)\1{9,}', topic):
            return False, "Topic contains too many repeated characters", []

    return True, "", topics_list


def validate_notes(notes):
    """
    Validates the notes field for security and length.
    Returns: (is_valid, error_message, sanitized_notes)
    """
    if not notes:
        return True, "", ""  # Notes are optional

    # Trim
    notes = notes.strip()

    # Check length (max 1000 characters)
    if len(notes) > 1000:
        return False, f"Notes cannot exceed 1000 characters (current: {len(notes)})", notes

    # Check for repeated characters
    if re.search(r'(.)\1{49,}', notes):  # 50 or more same characters
        return False, "Notes contain too many repeated characters", notes

    # XSS Protection: Escape HTML entities
    sanitized_notes = html.escape(notes)

    # Check if HTML was detected
    if sanitized_notes != notes:
        return False, "Notes cannot contain HTML tags or special characters like <, >, &", notes

    return True, "", sanitized_notes


def check_phone_exists(phone, backend_url):
    """
    Checks if a user with the same phone number already exists in the database.
    CRITICAL: Compares SANITIZED phone numbers.
    Returns: (exists: bool, error_message: str)
    """
    try:
        # Sanitize the input phone number first
        sanitized_input = sanitize_phone_number(phone)

        response = requests.get(f"{backend_url}/users/")
        if response.status_code == 200:
            users = response.json()
            # Compare SANITIZED phone numbers
            for user in users:
                existing_phone = user.get('phone', '')
                sanitized_existing = sanitize_phone_number(existing_phone)

                if sanitized_input == sanitized_existing:
                    return True, f"This phone number is already registered to another user: {user.get('name', 'Unknown')}"
            return False, ""
        return False, "Could not verify if phone number exists"
    except Exception as e:
        return False, f"Connection error while checking phone number: {str(e)}"


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

# Form validation states
if 'form_name' not in st.session_state:
    st.session_state.form_name = ""
if 'form_phone' not in st.session_state:
    st.session_state.form_phone = ""
if 'form_topics' not in st.session_state:
    st.session_state.form_topics = ""
if 'form_notes' not in st.session_state:
    st.session_state.form_notes = ""


# --- EDIT USER FORM LOGIC ---
def display_edit_form(user_info):
    with st.container(border=True):
        st.subheader(f"✏️ Editing AI Settings for: {user_info['name']}")
        st.info(f"📱 Phone: {user_info.get('phone', 'N/A')}")

        st.markdown("---")

        # Persona field
        edited_persona = st.selectbox("Persona *", ["Friendly", "Calm", "Cheerful"],
                                      index=["Friendly", "Calm", "Cheerful"].index(
                                          user_info.get('persona', 'Friendly')))

        # Topics field with validation
        topics_str = ", ".join(user_info.get('topics', []))
        edited_topics_str = st.text_area("Preferred Topics (comma-separated) *",
                                         value=topics_str,
                                         height=100,
                                         help="Enter topics separated by commas (max 10 topics, each 2-50 characters)")

        # Real-time validation for topics
        topics_valid = True
        topics_error = ""
        cleaned_topics = []

        if edited_topics_str:
            topics_valid, topics_error, cleaned_topics = validate_topics(edited_topics_str)
            if not topics_valid:
                st.error(topics_error)
            else:
                st.success(f"✓ {len(cleaned_topics)} valid topic(s) detected: {', '.join(cleaned_topics)}")
        else:
            topics_valid = False
            st.error("At least one topic is required")

        st.markdown("---")

        # Action buttons
        col1, col2 = st.columns(2)
        with col1:
            if st.button("💾 Save Changes",
                         type="primary",
                         use_container_width=True,
                         disabled=not topics_valid):
                if topics_valid:
                    update_payload = {"persona": edited_persona, "topics": cleaned_topics}

                    try:
                        user_id = user_info['id']
                        response = requests.put(f"{backend_url}/users/{user_id}", json=update_payload)
                        if response.status_code == 200:
                            st.toast("User updated successfully!", icon="✅")
                            del st.session_state['user_to_edit']
                            time.sleep(0.5)
                            st.rerun()
                        else:
                            st.error(f"Failed to update user. Error: {response.text}")
                    except Exception as e:
                        st.error(f"An error occurred: {e}")
                else:
                    st.error("Please fix validation errors before saving")

        with col2:
            if st.button("❌ Cancel", use_container_width=True):
                del st.session_state['user_to_edit']
                st.rerun()


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
        # Reset form fields
        st.session_state.form_name = ""
        st.session_state.form_phone = ""
        st.session_state.form_topics = ""
        st.session_state.form_notes = ""
    if col2.button("Existing Users"):
        st.session_state["show_add_user_form"] = False

    # --- Add User Form ---
    if st.session_state["show_add_user_form"]:
        with st.spinner("Loading Form..."):
            time.sleep(0.5)

        st.subheader("New User Details")

        # Name field with validation
        name = st.text_input("Name *",
                             value=st.session_state.form_name,
                             max_chars=100,
                             help="Enter full name (2-100 characters). Multiple users can have the same name.")

        # Real-time name validation
        name_valid = False
        name_error = ""

        if name:
            name_valid, name_error = validate_name(name)
            if not name_valid:
                st.error(name_error)
            else:
                st.success("✓ Valid name")

        # Phone Number field with validation
        phone = st.text_input("Phone Number * (Unique Identifier)",
                              value=st.session_state.form_phone,
                              max_chars=20,
                              help="Enter phone number with country code (e.g., +1 234-567-8900). Allowed: digits, +, -, (), spaces")

        # Real-time phone validation
        phone_valid = False
        phone_error = ""
        sanitized_phone = ""
        phone_exists = False

        if phone:
            phone_valid, phone_error, sanitized_phone = validate_phone_number(phone)
            if not phone_valid:
                st.error(phone_error)
            else:
                # Show sanitized version
                st.info(f"📱 Sanitized format: {sanitized_phone}")

                # Check if phone already exists
                phone_exists, exists_error = check_phone_exists(phone, backend_url)
                if phone_exists:
                    st.error(f"❌ {exists_error}")
                    phone_valid = False
                else:
                    st.success("✓ Valid and unique phone number")

        # Persona field
        persona = st.selectbox("Persona *", ["Friendly", "Calm", "Cheerful"])

        # Topics field with validation
        topics = st.text_area("Preferred Topics (comma-separated) *",
                              value=st.session_state.form_topics,
                              height=100,
                              help="Enter topics separated by commas (max 10 topics, each 2-50 characters)")

        topics_valid = False
        cleaned_topics = []

        if topics:
            topics_valid, topics_error, cleaned_topics = validate_topics(topics)
            if not topics_valid:
                st.error(topics_error)
            else:
                st.success(f"✓ {len(cleaned_topics)} valid topic(s) detected: {', '.join(cleaned_topics)}")

        # Notes field with validation
        notes = st.text_area("Notes for Admin",
                             value=st.session_state.form_notes,
                             height=150,
                             max_chars=1000,
                             help="Optional notes for admin reference (max 1000 characters)")

        # Character counter for notes
        if notes:
            char_count = len(notes)
            color = "green" if char_count <= 800 else "orange" if char_count <= 950 else "red"
            st.markdown(f"<p style='color:{color}; font-size:12px;'>Character count: {char_count}/1000</p>",
                        unsafe_allow_html=True)

        notes_valid = True
        sanitized_notes = ""

        if notes:
            notes_valid, notes_error, sanitized_notes = validate_notes(notes)
            if not notes_valid:
                st.error(notes_error)

        # Check if all required fields are valid
        all_valid = name_valid and phone_valid and topics_valid and notes_valid and not phone_exists

        st.markdown("---")

        # Action buttons
        col1, col2 = st.columns(2)

        with col1:
            # Save button - disabled until all fields are valid
            if st.button("💾 Save User",
                         type="primary",
                         disabled=not all_valid,
                         use_container_width=True):

                if all_valid:
                    # Proceed with user creation using SANITIZED phone number
                    endpoint = backend_url + "/users/"
                    user_data = {
                        "name": name.strip(),
                        "phone": sanitized_phone,  # Store sanitized phone
                        "persona": persona,
                        "topics": cleaned_topics,
                        "notes": sanitized_notes if sanitized_notes else ""
                    }

                    try:
                        response = requests.post(endpoint, json=user_data)
                        if response.status_code == 200:
                            st.success("✅ User added successfully!")
                            st.session_state["show_add_user_form"] = False
                            # Clear form fields
                            st.session_state.form_name = ""
                            st.session_state.form_phone = ""
                            st.session_state.form_topics = ""
                            st.session_state.form_notes = ""
                            time.sleep(1)
                            st.rerun()
                        else:
                            st.error("Failed to add user. Backend returned an error:")
                            try:
                                st.json(response.json())
                            except:
                                st.error(f"Status code: {response.status_code}")
                    except requests.exceptions.ConnectionError:
                        st.error("Connection Error: Could not connect to the backend. Is it running?")
                    except Exception as e:
                        st.error(f"An unexpected error occurred: {e}")
                else:
                    st.error("Please fix all validation errors before submitting")

        with col2:
            # Cancel button
            if st.button("❌ Cancel", use_container_width=True):
                st.session_state["show_add_user_form"] = False
                st.session_state.form_name = ""
                st.session_state.form_phone = ""
                st.session_state.form_topics = ""
                st.session_state.form_notes = ""
                st.rerun()

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

                    # Include phone in display
                    display_columns = ['name', 'phone', 'persona', 'topics', 'notes']
                    df_display = df[display_columns].copy()
                    df_display['Action'] = ""

                    edited_df = st.data_editor(
                        df_display, hide_index=True, use_container_width=True,
                        disabled=['name', 'phone', 'persona', 'topics', 'notes'],
                        column_config={
                            "phone": st.column_config.TextColumn("Phone Number"),
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
                            st.session_state['user_for_call'] = user_info
                            print("🔍 USER OBJECT DEBUG:")
                            print(f"   Full user object: {st.session_state['user_for_call']}")
                            print(f"   Keys: {list(st.session_state['user_for_call'].keys())}")
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
                                    try:
                                        error_details = response.json()
                                        st.error(f"Failed to archive user. Backend Error: {error_details}")
                                    except ValueError:
                                        st.error(f"Failed to archive user. Status Code: {response.status_code}")
                            except Exception as e:
                                st.error(f"An error occurred: {e}")
                else:
                    st.info("No users found. Add a new user to see them here.")
            else:
                st.error("Failed to retrieve users from the backend.")
        except requests.exceptions.ConnectionError:
            st.error("Connection Error: Could not connect to the backend. Is it running?")