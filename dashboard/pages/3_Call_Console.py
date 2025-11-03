# In Frontend/pages/3_Call_Console.py

import streamlit as st
from datetime import datetime, UTC
import requests
import streamlit.components.v1 as components
import asyncio
import re
import traceback
import time
from datetime import datetime
from dateutil import parser

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

    # Display the transcript component with proper height
    transcript_display = """
    <style>
        * {
            box-sizing: border-box;
        }

        body, html {
            margin: 0;
            padding: 0;
            height: 100%;
            width: 100%;
            overflow-x: hidden !important;
            overflow-y: hidden !important;
            max-width: 100vw !important;
        }

        #streamlit-transcript-mirror {
            width: 100%;
            height: 100%;
            overflow-x: hidden;
            overflow-y: auto;
            border: 2px solid #e0e0e0;
            border-radius: 12px;
            padding: 20px;
            background: linear-gradient(to bottom, #fafafa 0%, #f5f5f5 100%);
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            box-shadow: 0 2px 8px rgba(0,0,0,0.08);
            box-sizing: border-box;
        }

        #transcript-mirror-content {
            min-height: 100%;
            width: 100%;
        }

        /* Custom scrollbar */
        #streamlit-transcript-mirror::-webkit-scrollbar {
            width: 12px;
        }

        #streamlit-transcript-mirror::-webkit-scrollbar-track {
            background: #f1f1f1;
            border-radius: 10px;
        }

        #streamlit-transcript-mirror::-webkit-scrollbar-thumb {
            background: #888;
            border-radius: 10px;
            border: 2px solid #f1f1f1;
        }

        #streamlit-transcript-mirror::-webkit-scrollbar-thumb:hover {
            background: #555;
        }

        /* Transcript items */
        .transcript-item {
            margin-bottom: 16px;
            padding: 12px 16px;
            border-radius: 8px;
            animation: fadeIn 0.3s ease-in;
        }

        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }

        .transcript-item.user {
            background-color: #e3f2fd;
            border-left: 4px solid #2196F3;
            margin-right: 40px;
        }

        .transcript-item.ai {
            background-color: #f5f5f5;
            border-left: 4px solid #757575;
            margin-left: 40px;
        }

        .transcript-item.streaming {
            background: linear-gradient(90deg, #e8f4ff 0%, #d1e7ff 100%);
            border-left: 4px solid #0088ff;
            box-shadow: 0 2px 6px rgba(0, 136, 255, 0.2);
            animation: pulseGlow 2s ease-in-out infinite;
        }

        @keyframes pulseGlow {
            0%, 100% { box-shadow: 0 2px 6px rgba(0, 136, 255, 0.2); }
            50% { box-shadow: 0 4px 12px rgba(0, 136, 255, 0.4); }
        }

        .speaker {
            font-weight: 700;
            font-size: 0.85em;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 6px;
            display: flex;
            align-items: center;
            gap: 8px;
        }

        .speaker.user { color: #1976D2; }
        .speaker.user::before { content: "👤"; font-size: 1.2em; }
        .speaker.ai { color: #616161; }
        .speaker.ai::before { content: "🤖"; font-size: 1.2em; }

        .typing-indicator {
            color: #0088ff;
            font-weight: bold;
            animation: blink 1s infinite;
            margin-left: 4px;
        }

        @keyframes blink {
            0%, 50% { opacity: 1; }
            51%, 100% { opacity: 0; }
        }

        /* SPACE PRESERVATION WITH PROPER WRAPPING */
        .streaming-text {
            font-family: 'Courier New', Monaco, Consolas, monospace;
            line-height: 1.6;
            font-size: 0.95em;
            padding: 6px;
            border-radius: 4px;
            background-color: rgba(0, 102, 204, 0.03);
            word-wrap: break-word;
            overflow-wrap: break-word;
            white-space: pre-wrap !important;
        }

        .streaming-text .token {
            color: #1565C0;
            font-weight: 500;
            white-space: pre-wrap !important;
            display: inline !important;
        }

        .streaming-text .new-token {
            color: #0D47A1;
            font-weight: 700;
            background-color: rgba(33, 150, 243, 0.15);
            padding: 2px 4px;
            border-radius: 3px;
            animation: popIn 0.3s ease-out;
        }

        @keyframes popIn {
            0% { transform: scale(0.7); opacity: 0; }
            50% { transform: scale(1.05); }
            100% { transform: scale(1); opacity: 1; }
        }

        .transcript-item > div:last-child {
            color: #212121;
            line-height: 1.5;
            font-size: 0.95em;
            white-space: pre-wrap !important;
            word-wrap: break-word;
            overflow-wrap: break-word;
        }

        .transcript-empty {
            color: #999;
            text-align: center;
            padding: 40px 20px;
            font-style: italic;
        }

        .transcript-empty::before {
            content: "💬";
            display: block;
            font-size: 3em;
            margin-bottom: 10px;
            opacity: 0.3;
        }

        /* PROPER TEXT WRAPPING FOR ALL ELEMENTS */
        .transcript-item, .transcript-item * {
            word-wrap: break-word !important;
            overflow-wrap: break-word !important;
        }
    </style>

    <div id="streamlit-transcript-mirror">
        <div id="transcript-mirror-content">
            <div class="transcript-empty">
                Transcript will appear here once connected...
            </div>
        </div>
    </div>

    <script>
        let lastTranscriptHTML = '';

        function updateTranscript() {
            try {
                let livekitTranscript = null;

                // Try to find transcriptContent in parent
                if (parent && parent.document) {
                    livekitTranscript = parent.document.getElementById('transcriptContent');
                }

                // If not found in parent, search all iframes
                if (!livekitTranscript) {
                    const iframes = parent.document.getElementsByTagName('iframe');
                    for (let i = 0; i < iframes.length; i++) {
                        try {
                            const doc = iframes[i].contentDocument || iframes[i].contentWindow.document;
                            const content = doc.getElementById('transcriptContent');
                            if (content) {  // Remove the children.length check to always find it
                                livekitTranscript = content;
                                break;
                            }
                        } catch (e) {
                            // Cross-origin or other errors, skip
                        }
                    }
                }

                const mirrorContent = document.getElementById('transcript-mirror-content');

                if (livekitTranscript && mirrorContent) {
                    // Check if content has actually changed to avoid unnecessary updates
                    const currentHTML = livekitTranscript.innerHTML;

                    if (currentHTML !== lastTranscriptHTML) {
                        lastTranscriptHTML = currentHTML;

                        // Clear existing content
                        mirrorContent.innerHTML = '';

                        // Clone all child nodes deeply to preserve structure and text
                        if (livekitTranscript.children.length > 0) {
                            Array.from(livekitTranscript.children).forEach(child => {
                                const clonedNode = child.cloneNode(true);
                                mirrorContent.appendChild(clonedNode);
                            });
                        } else {
                            // Show empty state if no messages
                            mirrorContent.innerHTML = '<div class="transcript-empty">Waiting for conversation...</div>';
                        }

                        // Auto-scroll to bottom
                        const container = document.getElementById('streamlit-transcript-mirror');
                        if (container) {
                            container.scrollTop = container.scrollHeight;
                        }
                    }
                }
            } catch (e) {
                console.error('Transcript update error:', e);
            }
        }

        function scheduleUpdate() {
            updateTranscript();
            requestAnimationFrame(scheduleUpdate);
        }

        requestAnimationFrame(scheduleUpdate);
    </script>
    """

    # Render with increased height (scrolling=False to prevent iframe scroll, content handles its own scroll)
    components.html(transcript_display, height=500, scrolling=False)

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
            with st.spinner("Ending call and signaling agent..."):
                try:
                    stop_payload = {"room_name": st.session_state.call_room_name}
                    response = requests.post(f"{backend_url}/calls/stop", json=stop_payload)

                    if response.status_code == 200:
                        st.toast("Agent signaled to end call.")
                    else:
                        st.warning(f"Could not signal agent, but ending call anyway: {response.text}")

                except Exception as e:
                    st.warning(f"Error signaling agent: {e}")

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

# --- SUMMARY SECTION ---
if st.session_state.call_status == "Ended":
    st.session_state.livekit_token = None
    st.session_state.livekit_url = None

    with st.container(border=True):
        st.subheader("Retrieving Call Summary...")
        summary_placeholder = st.empty()

        with st.spinner("Waiting for agent to save summary..."):
            try:
                user_id_to_find = user_info.get('id') or user_info.get('_id') or user_info.get('user_id')

                # ✅ FIX: Store call end time to filter summaries
                call_end_time = datetime.now(UTC).isoformat()

                print("=" * 80)
                print("🔍 FRONTEND DEBUG INFO:")
                print(f"   user_id: {user_id_to_find}")
                print(f"   call_end_time: {call_end_time}")
                print(f"   room_name: {st.session_state.call_room_name}")
                print("=" * 80)

                st.info(f"🔍 Looking for NEW summary for user: `{user_id_to_find}`")

                latest_call = None

                # ✅ FIX: Increase polling to 20 attempts (80 seconds total)
                for attempt in range(20):
                    print(f"📡 Polling attempt {attempt + 1}/20")

                    # Show progress to user
                    progress_msg = f"⏳ Waiting for AI to finish analyzing conversation... ({attempt + 1}/20)"
                    summary_placeholder.info(progress_msg)

                    response = requests.get(f"{backend_url}/calls/")

                    if response.status_code == 200:
                        all_calls = response.json()
                        print(f"📊 Got {len(all_calls)} total calls")

                        # ✅ FIX: Filter for this user AND calls created AFTER this call started
                        user_calls = [
                            c for c in all_calls
                            if c.get('user_id') == user_id_to_find
                               and c.get('end_time', '') >= call_end_time  # NEW: Only recent calls
                        ]

                        print(f"🎯 Found {len(user_calls)} NEW calls for user_id={user_id_to_find}")

                        if user_calls:
                            # Sort by end_time to get most recent
                            user_calls_sorted = sorted(
                                user_calls,
                                key=lambda x: x.get('end_time', ''),
                                reverse=True
                            )

                            latest = user_calls_sorted[0]
                            print(f"📞 Latest NEW call: {latest.get('id')}")
                            print(f"   Has summary: {bool(latest.get('summary'))}")

                            if latest.get("summary"):
                                latest_call = latest
                                print("✅ Summary found!")
                                break
                            else:
                                print("⏳ Summary not ready yet...")
                        else:
                            print(f"⏳ No NEW calls found yet for user_id={user_id_to_find}")
                    else:
                        print(f"⚠️ Backend returned status {response.status_code}")

                    if attempt < 19:
                        time.sleep(4)  # 4 seconds between polls

                if latest_call:
                    summary_placeholder.empty()

                    st.session_state.ai_analysis = {
                        "call_id": latest_call.get('id'),
                        "summary": latest_call.get('summary', 'N/A'),
                        "mood": latest_call.get('mood', 'neutral').capitalize(),
                        "topics": latest_call.get('topics', [])
                    }

                    st.session_state.call_status = "Summary_Retrieved"
                    st.session_state.call_room_name = None
                    st.rerun()
                else:
                    print(f"❌ TIMEOUT: Could not find summary after 20 attempts (80 seconds)")
                    summary_placeholder.error(
                        f"⏱️ Summary is taking longer than expected. "
                        f"Please check Analytics page in 1-2 minutes to view the summary."
                    )

                    # Allow user to continue anyway
                    if st.button("Continue to Analytics", key="timeout_continue"):
                        st.session_state.call_status = "Not Connected"
                        st.switch_page("pages/4_Analytics.py")

            except Exception as e:
                summary_placeholder.error(f"Error: {e}")
                traceback.print_exc()

if st.session_state.call_status == "Summary_Retrieved":
    with st.container(border=True):
        with st.form("summary_form"):
            st.subheader("Review Call Summary")
            analysis = st.session_state.ai_analysis

            summary_text = st.text_area(
                "Summary",
                value=analysis.get("summary", "N/A"),
                height=150
            )

            detected_mood = analysis.get("mood", "neutral").lower()
            mood_display = {
                'happy': '😊 Happy',
                'sad': '😔 Sad',
                'neutral': '😐 Neutral'
            }.get(detected_mood, '😐 Neutral')

            st.text_input(
                "Overall Mood (AI Detected)",
                value=mood_display,
                disabled=True
            )

            topics_list = analysis.get("topics", [])
            topics_text = ", ".join(topics_list) if topics_list else ""
            topics_discussed = st.text_input(
                "Topics Discussed",
                value=topics_text
            )

            if st.form_submit_button("Save & Go to Analytics", use_container_width=True):
                print("Frontend: Save & Go button clicked.")

                # ✅ ENHANCED: Save to memory with follow-up tracking
                try:
                    # Parse edited topics
                    final_topics = [t.strip() for t in topics_discussed.split(",") if t.strip()]

                    # Get call details
                    user_info = st.session_state.get('user_for_call')
                    call_id = analysis.get("call_id")

                    # ✅ NEW: Get discussed vs new follow-ups from the call
                    # For now, we'll extract from the latest call log
                    response = requests.get(f"{backend_url}/calls/")
                    all_calls = response.json()

                    # Find this specific call
                    this_call = next((c for c in all_calls if c.get('id') == call_id), None)

                    new_followups = []
                    if this_call and this_call.get('new_followups'):
                        new_followups = this_call['new_followups']

                    memory_payload = {
                        "user_id": user_info.get("id"),
                        "user_name": user_info.get("name"),
                        "call_id": call_id,
                        "summary": summary_text,
                        "mood": detected_mood,
                        "topics": final_topics,
                        "date": datetime.now(UTC).isoformat(),
                        # ✅ NEW FIELDS for smart follow-ups
                        "discussed_topics": [],  # Topics from memory that were addressed
                        "new_followups": new_followups  # New things mentioned this call
                    }

                    # ✅ SMART LOGIC: Check if this call addressed any pending follow-ups
                    # Get user's memory to see what was pending
                    try:
                        memory_response = requests.get(
                            f"{backend_url}/memory/{user_info.get('id')}",
                            timeout=5
                        )
                        if memory_response.status_code == 200:
                            user_memory = memory_response.json()
                            old_pending = user_memory.get("pending_followups", [])

                            # Check which pending topics were mentioned in this call's summary
                            discussed = []
                            for pending_topic in old_pending:
                                # Simple keyword matching - check if topic was mentioned
                                if any(keyword.lower() in summary_text.lower()
                                       for keyword in pending_topic.split()[:3]):  # Check first 3 words
                                    discussed.append(pending_topic)

                            memory_payload["discussed_topics"] = discussed

                            if discussed:
                                st.success(f"✅ Addressed {len(discussed)} pending topic(s) from last time!")
                                for topic in discussed:
                                    st.caption(f"  • {topic}")

                    except Exception as mem_err:
                        print(f"⚠️ Could not check previous memory: {mem_err}")

                    response = requests.post(
                        f"{backend_url}/memory/update",
                        json=memory_payload,
                        timeout=5
                    )

                    if response.status_code == 200:
                        result = response.json()
                        st.toast("✅ Memory updated!", icon="🧠")
                        print("✅ Memory saved to database")

                        # ✅ SHOW WHAT'S PENDING FOR NEXT CALL
                        pending_for_next = result.get("pending_followups", [])
                        if pending_for_next:
                            st.info(f"📌 {len(pending_for_next)} topic(s) to follow up on next time:")
                            for topic in pending_for_next[:3]:  # Show first 3
                                st.caption(f"  • {topic}")
                        else:
                            st.success("✅ All topics addressed - next call starts fresh!")
                    else:
                        st.warning("Could not update memory, but continuing...")
                        print(f"⚠️ Memory update failed: {response.text}")

                except Exception as e:
                    st.warning(f"Error updating memory: {e}")
                    print(f"❌ Memory update error: {e}")

                st.toast("Call log reviewed.", icon="✅")

                # Clear session state
                keys_to_clear = [
                    "call_status", "start_time", "ai_analysis",
                    "user_for_call", "call_room_name",
                    "livekit_token", "livekit_url"
                ]
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]

                st.switch_page("pages/4_Analytics.py")