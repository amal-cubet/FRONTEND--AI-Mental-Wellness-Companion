import streamlit as st
import pandas as pd
import altair as alt
import time
# No third-party modal library needed

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

st.title("📊 Analytics Dashboard")


# --- MOCK DATA CREATION ---
def create_mock_data():
    mood_data = pd.DataFrame({
        'Date': pd.to_datetime(
            ['2023-10-01', '2023-10-02', '2023-10-03', '2023-10-04', '2023-10-05', '2023-10-06', '2023-10-07']),
        'Avg Mood': [0.5, 0.8, 0.2, -0.3, 0.0, 0.7, 0.9]
    })
    calls_data = {
        'id': [1, 2, 3, 4],
        'User': ['John Doe', 'Jane Smith', 'John Doe', 'Peter Jones'],
        'Date': ['2023-10-07', '2023-10-07', '2023-10-06', '2023-10-05'],
        'Duration': ['5m 32s', '7m 11s', '4m 50s', '8m 02s'],
        'Overall Mood': ['Positive', 'Positive', 'Neutral', 'Positive'],
        'Summary Tag': ['Talked about family', 'Discussed old songs', 'Felt a bit tired', 'Happy about daughter'],
    }
    calls_df = pd.DataFrame(calls_data)
    transcript = """
    **AI (Greeting):** Hello John, how are you feeling today?
    **John Doe (User):** I'm doing well, thank you. The weather is lovely. (Mood: Positive)
    ---
    **AI (Recall):** That's wonderful to hear. Last time, you mentioned your daughter Anu was visiting. How was that?
    **John Doe (User):** Oh, it was fantastic! She brought the grandkids. We had a great time. (Mood: Positive)
    ---
    **AI (Closing):** I'm so glad to hear that, John. I will check in with you tomorrow as scheduled. Have a great day!
    **John Doe (User):** You too, goodbye. (Mood: Neutral)
    """
    topics = ['Family', 'Grandkids', 'Old Songs', 'Health', 'Weather', 'Gardening', 'Neighbors', 'Books', 'Food', 'Movies']
    return mood_data, calls_df, topics, transcript

mood_df, calls_df, topics_list, mock_transcript = create_mock_data()

# --- LAYOUT: Top section with Chart and Topics Cloud ---
col1, col2 = st.columns([3, 1])
with col1:
    st.subheader("📈 Mood Over Time")
    chart = alt.Chart(mood_df).mark_line(
        point=alt.OverlayMarkDef(color="blue", size=50), color='red'
    ).encode(
        x=alt.X('Date:T', title='Date'),
        y=alt.Y('Avg Mood:Q', title='Average Mood Score', scale=alt.Scale(domain=[-1, 1])),
        tooltip=['Date', 'Avg Mood']
    ).properties(height=300).interactive()
    st.altair_chart(chart, use_container_width=True)
with col2:
    st.subheader("☁️ Top Topics")
    with st.container(border=True, height=350):
        for topic in topics_list:
            st.markdown(f"- <span style='background-color:#f0f2f6; border-radius:5px; padding: 5px;'>{topic}</span>", unsafe_allow_html=True)

st.markdown("---")
st.subheader("📞 Recent Calls")

# --- START OF MODIFIED SECTION ---

# STEP 1: Initialize session state for our custom dialog
if 'show_transcript_dialog' not in st.session_state:
    st.session_state.show_transcript_dialog = False
if 'selected_call_data' not in st.session_state:
    st.session_state.selected_call_data = None

# Create a placeholder that will be populated with the dialog if needed
dialog_placeholder = st.empty()

# STEP 2: Display the custom dialog IF the session state flag is True
if st.session_state.show_transcript_dialog:
    with dialog_placeholder.container(border=True):
        call_data = st.session_state.selected_call_data
        st.subheader(f"Call Transcript for {call_data['User']} on {call_data['Date']}")
        st.markdown(mock_transcript)
        if st.button("Close"):
            # When closed, reset the flag and rerun
            st.session_state.show_transcript_dialog = False
            st.rerun()

# --- LAYOUT: Recent Calls Table ---
calls_df_display = calls_df.copy()
calls_df_display['Action'] = ""
edited_df = st.data_editor(
    calls_df_display.drop(columns=['id']),
    hide_index=True,
    use_container_width=True,
    disabled=calls_df_display.columns.drop('Action'),
    column_config={
        "Action": st.column_config.SelectboxColumn("Action", options=["", "View Transcript"], width="small"),
    }
)

# STEP 3: Check if an action was selected in the table
action_row = edited_df[edited_df['Action'] == "View Transcript"]
if not action_row.empty:
    # If an action is selected, set the session state to show the dialog
    if not st.session_state.show_transcript_dialog:
        row_index = action_row.index[0]
        st.session_state.selected_call_data = calls_df.iloc[row_index]
        st.session_state.show_transcript_dialog = True
        # Rerun to display the dialog at the top of the page
        st.rerun()

# --- END OF MODIFIED SECTION ---