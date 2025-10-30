# In Frontend/pages/3_Call_Console.py

import streamlit as st
from datetime import datetime, UTC
import requests
import streamlit.components.v1 as components
import asyncio
import re
import traceback
import time

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


# --- HELPER FUNCTION (UNCHANGED) ---
def parse_summary_report(report_text: str) -> dict:
    try:
        summary_match = re.search(r"\*\*Summary:\*\*\s*(.*?)\*\*Overall Mood:\*\*", report_text, re.DOTALL)
        if summary_match:
            summary = summary_match.group(1).strip()
        else:
            # Fallback if mood isn't present (adjust regex slightly)
            summary_fallback_match = re.search(r"\*\*Summary:\*\*\s*(.*)", report_text, re.DOTALL)
            summary = summary_fallback_match.group(
                1).strip() if summary_fallback_match else report_text  # Use full text if even basic summary fails

        mood_match = re.search(r"\*\*Overall Mood:\*\*\s*(.*)", report_text)
        mood = mood_match.group(1).strip() if mood_match else "Neutral"  # Default mood

        topics_section_match = re.search(r"\*\*Topics Discussed:\*\*(.*)", report_text, re.DOTALL)
        if topics_section_match:
            topics_section = topics_section_match.group(1)
            # Find list items more robustly
            topics = [topic.strip().lstrip('- ') for topic in topics_section.splitlines() if
                      topic.strip().startswith('-')]
        else:
            topics = []

        return {"summary": summary, "mood": mood, "topics": topics}
    except Exception as e:
        print(f"Error parsing summary report: {e}")  # Log error
        traceback.print_exc()
        # Fallback for any parsing error
        return {"summary": report_text, "mood": "Neutral", "topics": []}


# --- SESSION STATE INITIALIZATION (UNCHANGED) ---
def initialize_call_state():
    if "call_status" not in st.session_state:
        st.session_state.call_status = "Not Connected"
    if "livekit_token" not in st.session_state:
        st.session_state.livekit_token = None
    if "livekit_url" not in st.session_state:
        st.session_state.livekit_url = None
    if "start_time" not in st.session_state:
        st.session_state.start_time = None
    if "ai_analysis" not in st.session_state:
        st.session_state.ai_analysis = {}
    if "call_room_name" not in st.session_state:
        st.session_state.call_room_name = None


initialize_call_state()

# --- PAGE TITLE AND USER INFO (UNCHANGED) ---
st.title("📞 Call Console")
user_info = st.session_state.get('user_for_call')
if not user_info:
    st.warning("No user selected. Please start a call from the Users page.")
    st.stop()
st.info(f"Preparing call for: **{user_info.get('name', 'N/A')}** | Persona: **{user_info.get('persona', 'Friendly')}**")

# --- MAIN LAYOUT (UNCHANGED) ---
col_transcript, col_controls = st.columns([2, 1])

# --- TRANSCRIPT PANEL ---
with col_transcript:
    st.subheader("Live Transcript")

    # Status info
    if st.session_state.call_status == "Not Connected":
        st.info("📝 Connect to the call to see the real-time transcript here")
    elif st.session_state.call_status == "Ended":
        st.info("Call has ended. Retrieving summary...")
    else:
        st.success("✅ **Live Transcript** - Conversation appears below")

    # Display the LiveKit transcript component (synced from the HTML component)
    transcript_display = """
    <div id="streamlit-transcript-mirror" style="
        height: 400px;
        overflow-y: auto;
        border: 1px solid #ddd;
        border-radius: 10px;
        padding: 15px;
        background-color: #fafafa;
        font-family: sans-serif;
    ">
        <div id="transcript-mirror-content">
            <p style="color: #999; text-align: center; padding: 20px;">Transcript will appear here once the call is connected...</p>
        </div>
    </div>
    <script>
        // Poll for transcript updates from the LiveKit component
        setInterval(() => {
            const livekitTranscript = parent.document.getElementById('transcriptContent');
            const mirrorContent = document.getElementById('transcript-mirror-content');

            if (livekitTranscript && mirrorContent) {
                // Clone the transcript content
                mirrorContent.innerHTML = livekitTranscript.innerHTML;
                // Auto-scroll to bottom
                const container = document.getElementById('streamlit-transcript-mirror');
                if (container) container.scrollTop = container.scrollHeight;
            }
        }, 500); // Update every 500ms
    </script>
    """
    components.html(transcript_display, height=420)

    # --- Text input for sending messages ---
    st.markdown("---")
    st.markdown("### 💬 Send Text Message")

    # Initialize message counter for unique keys
    if "message_counter" not in st.session_state:
        st.session_state.message_counter = 0

    # Only show input if connected
    if st.session_state.call_status == "Connected":
        user_input = st.text_area(
            "Type your message...",
            key=f"message_input_{st.session_state.message_counter}",
            height=70,
            placeholder="Type a message to send to the AI..."
        )
        send_button = st.button("📤 Send Message", use_container_width=True)

        if send_button and user_input.strip():
            message_text = user_input.strip()

            # Send message via JavaScript to LiveKit data channel
            send_js = f"""
            <script>
                (function() {{
                    const message = {repr(message_text)};
                    console.log('📤 Attempting to send message:', message);

                    // Wait a bit for the function to be available
                    function attemptSend(retries = 5) {{
                        if (typeof parent.sendTextMessageToLiveKit === 'function') {{
                            try {{
                                const success = parent.sendTextMessageToLiveKit(message);
                                console.log('✅ Message sent successfully:', success);
                            }} catch (error) {{
                                console.error('❌ Error sending message:', error);
                            }}
                        }} else if (retries > 0) {{
                            console.log('⏳ Function not ready, retrying... (' + retries + ' left)');
                            setTimeout(() => attemptSend(retries - 1), 200);
                        }} else {{
                            console.error('❌ sendTextMessageToLiveKit function not found after retries');
                        }}
                    }}

                    attemptSend();
                }})();
            </script>
            """
            components.html(send_js, height=0)

            # Clear input
            st.session_state.message_counter += 1
            st.rerun()
    else:
        st.info("💡 Connect to the call to send text messages")

# --- CONTROLS PANEL (UNCHANGED) ---
with col_controls:
    st.subheader("Call Controls")

    if st.session_state.call_status == "Not Connected":
        if st.button("📞 Connect", type="primary", use_container_width=True):
            with st.spinner("Starting call and dispatching agent..."):
                try:
                    start_call_payload = {
                        "user_id": user_info.get("id"),
                        "user_name": user_info.get("name"),
                        "persona": user_info.get("persona")
                    }
                    response = requests.post(f"{backend_url}/calls/start", json=start_call_payload)

                    if response.status_code == 200:
                        call_data = response.json()
                        st.session_state.livekit_url = call_data["livekit_url"]
                        st.session_state.livekit_token = call_data["user_token"]
                        st.session_state.call_room_name = call_data["room_name"]
                        st.session_state.start_time = datetime.now(UTC)
                        st.session_state.call_status = "Connected"
                        st.rerun()
                    else:
                        st.error(f"Failed to start call: {response.text}")
                except requests.exceptions.ConnectionError:
                    st.error(f"Connection Error: Could not connect to backend at {backend_url}. Is it running?")
                except Exception as e:
                    st.error(f"Error starting call: {e}")
                    traceback.print_exc()

    # --- THIS SECTION IS MODIFIED ---
    elif st.session_state.call_status == "Connected":
        # Read the HTML template from file
        import os

        html_file_path = os.path.join(os.path.dirname(__file__), '..', 'livekit_component_utf8.html')

        with open(html_file_path, 'r', encoding='utf-8') as file:
            livekit_html = file.read()

        # Replace placeholders with actual values
        # livekit_html = livekit_html.replace('wss://ai-mwc-jjlgi6ly.livekit.cloud', st.session_state.livekit_url)
        livekit_html = livekit_html.replace('LIVEKIT_URL_PLACEHOLDER', st.session_state.livekit_url)
        livekit_html = livekit_html.replace('LIVEKIT_TOKEN_PLACEHOLDER', st.session_state.livekit_token)
        livekit_html = livekit_html.replace('/*STREAMLIT_FLAG*/', 'false; //')
        # Render the HTML
        st.code(st.session_state.livekit_url, language="bash")
        st.code(st.session_state.livekit_token, language="bash")

        components.html(livekit_html, height=300)

        if st.button("☎️ End Call", use_container_width=True):
            print("Frontend: End Call button clicked.")
            st.session_state.call_status = "Ended"
            st.rerun()
    # --- END OF MODIFIED SECTION ---

    st.markdown("---")
    st.write(f"**Status:** {st.session_state.call_status}")
    if st.session_state.start_time:
        # Ensure start_time is offset-aware UTC
        start_time_utc = st.session_state.start_time.replace(tzinfo=UTC)
        now_utc = datetime.now(UTC)
        duration = now_utc - start_time_utc
        st.write(f"**Duration:** {str(duration).split('.')[0]}")

# --- SUMMARY SECTION (UNCHANGED) ---
if st.session_state.call_status == "Ended":
    st.session_state.livekit_token = None  # Clear token
    st.session_state.livekit_url = None  # Clear URL

    with st.container(border=True):
        st.subheader("Retrieving Call Summary...")
        summary_placeholder = st.empty()

        with st.spinner("Waiting for agent to save summary... This can take up to 10 seconds."):
            try:
                latest_call = None
                room_name = st.session_state.call_room_name
                user_id_to_find = user_info.get('id')

                # Poll backend for summary
                for attempt in range(5):
                    print(f"Frontend: Attempt {attempt + 1}/5 to fetch summary for user {user_id_to_find}")
                    response = requests.get(f"{backend_url}/calls/")
                    if response.status_code == 200:
                        all_calls = response.json()
                        # Filter calls for the specific user and sort by end_time (most recent first)
                        user_calls = sorted(
                            [c for c in all_calls if c.get('user_id') == user_id_to_find],
                            key=lambda x: x.get('end_time', '1970-01-01T00:00:00Z'),
                            reverse=True
                        )

                        if user_calls and user_calls[0].get("summary"):
                            latest_call = user_calls[0]
                            print(f"Frontend: Found summary in call log {latest_call.get('id')}")
                            break
                        else:
                            print(
                                f"Frontend: No summary found yet for user {user_id_to_find}. Most recent call (if any): {user_calls[0].get('id') if user_calls else 'None'}")
                    else:
                        print(f"Frontend: Failed to fetch calls from backend (Status: {response.status_code})")

                    if attempt < 4:
                        time.sleep(2)  # Wait before retrying

                if latest_call:
                    summary_placeholder.empty()
                    st.session_state.ai_analysis = parse_summary_report(latest_call['summary'])
                    st.session_state.call_status = "Summary_Retrieved"
                    st.session_state.call_room_name = None
                    print("Frontend: Summary retrieved, rerunning.")
                    st.rerun()
                else:
                    print(f"Frontend: Could not find summary after polling for user {user_id_to_find}.")
                    summary_placeholder.error(
                        "Could not find the summary for this call. The agent might have failed or the call was too short.")

            except requests.exceptions.ConnectionError:
                summary_placeholder.error(
                    f"Connection Error fetching summary: Could not connect to backend at {backend_url}.")
            except Exception as e:
                summary_placeholder.error(f"An error occurred fetching summary: {e}")
                traceback.print_exc()

if st.session_state.call_status == "Summary_Retrieved":
    # --- Form for Reviewing Summary (UNCHANGED) ---
    with st.container(border=True):
        with st.form("summary_form"):
            st.subheader("Review Call Summary")
            analysis = st.session_state.ai_analysis

            summary_text = st.text_area("Summary", value=analysis.get("summary", "N/A"), height=150)
            mood_options = ["Positive", "Neutral", "Negative"]
            detected_mood = analysis.get("mood", "Neutral").capitalize()
            try:
                mood_index = [m.lower() for m in mood_options].index(detected_mood.lower())
            except ValueError:
                mood_index = 1
            overall_mood = st.selectbox("Overall Mood", mood_options, index=mood_index)
            topics_text = ", ".join(analysis.get("topics", []))
            topics_discussed = st.text_input("Topics Discussed", value=topics_text)

            if st.form_submit_button("Save & Go to Analytics", use_container_width=True):
                print("Frontend: Save & Go button clicked.")
                st.toast("Call log reviewed.", icon="✅")
                keys_to_clear = ["call_status", "start_time", "ai_analysis", "user_for_call", "call_room_name",
                                 "livekit_token", "livekit_url"]
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]
                st.switch_page("pages/4_Analytics.py")