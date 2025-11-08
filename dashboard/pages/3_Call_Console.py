# In Frontend/pages/3_Call_Console.py

import streamlit as st
from datetime import datetime, UTC, timedelta, timezone
import requests
import streamlit.components.v1 as components
import asyncio
import re
import traceback
import time
from datetime import datetime
from dateutil import parser
from requests.exceptions import Timeout, ConnectionError
import os
import dotenv

dotenv.load_dotenv()
print("🔍 Deepgram Key (first 8 chars):", (os.getenv("DEEPGRAM_API_KEY") or "❌ Missing")[:8])

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

# === ADDED: Deepgram key fetch ===
DEEPGRAM_API_KEY = os.getenv("DEEPGRAM_API_KEY", "")


# --- HELPER FUNCTION (UNCHANGED) ---
def parse_summary_report(report_text: str) -> dict:
    try:
        summary_match = re.search(r"\*\*Summary:\*\*\s*(.*?)\*\*Overall Mood:\*\*", report_text, re.DOTALL)
        if summary_match:
            summary = summary_match.group(1).strip()
        else:
            summary_fallback_match = re.search(r"\*\*Summary:\*\*\s*(.*)", report_text, re.DOTALL)
            summary = summary_fallback_match.group(1).strip() if summary_fallback_match else report_text
        mood_match = re.search(r"\*\*Overall Mood:\*\*\s*(.*)", report_text)
        mood = mood_match.group(1).strip() if mood_match else "Neutral"
        topics_section_match = re.search(r"\*\*Topics Discussed:\*\*(.*)", report_text, re.DOTALL)
        if topics_section_match:
            topics_section = topics_section_match.group(1)
            topics = [topic.strip().lstrip('- ') for topic in topics_section.splitlines() if
                      topic.strip().startswith('-')]
        else:
            topics = []
        return {"summary": summary, "mood": mood, "topics": topics}
    except Exception as e:
        print(f"Error parsing summary report: {e}")
        traceback.print_exc()
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
    if "call_end_timestamp" not in st.session_state:
        st.session_state.call_end_timestamp = None
    if "summary_poll_start" not in st.session_state:
        st.session_state.summary_poll_start = None
    if "summary_attempts" not in st.session_state:
        st.session_state.summary_attempts = 0


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

    # =========================
    # FLICKER-FREE TRANSCRIPT MIRROR (UNCHANGED)
    # =========================
    transcript_display = """
    <style>
        * { box-sizing: border-box; }
        body, html {
            margin: 0; padding: 0; height: 100%; width: 100%;
            overflow-x: hidden !important; overflow-y: hidden !important; max-width: 100vw !important;
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
        }
        #transcript-mirror-content { min-height: 100%; width: 100%; }
        #streamlit-transcript-mirror::-webkit-scrollbar { width: 12px; }
        #streamlit-transcript-mirror::-webkit-scrollbar-track { background: #f1f1f1; border-radius: 10px; }
        #streamlit-transcript-mirror::-webkit-scrollbar-thumb { background: #888; border-radius: 10px; border: 2px solid #f1f1f1; }
        #streamlit-transcript-mirror::-webkit-scrollbar-thumb:hover { background: #555; }

        .transcript-item {
            margin-bottom: 16px; padding: 12px 16px; border-radius: 8px; animation: fadeIn 0.3s ease-in;
        }
        @keyframes fadeIn { from { opacity: 0; transform: translateY(10px); } to { opacity: 1; transform: translateY(0); } }

        .transcript-item.user {
            background-color: #e3f2fd; border-left: 4px solid #2196F3; margin-right: 40px;
        }
        .transcript-item.ai {
            background-color: #f5f5f5; border-left: 4px solid #757575; margin-left: 40px;
        }

        .speaker { font-weight: 700; font-size: 0.85em; text-transform: uppercase; letter-spacing: 0.5px; margin-bottom: 6px; display: flex; align-items: center; gap: 8px; }
        .speaker.user { color: #1976D2; }
        .speaker.user::before { content: "👤"; font-size: 1.2em; }
        .speaker.ai { color: #616161; }
        .speaker.ai::before { content: "🤖"; font-size: 1.2em; }

        .streaming-text {
            font-family: 'Courier New', Monaco, Consolas, monospace;
            line-height: 1.6; font-size: 0.95em; padding: 6px; border-radius: 4px;
            background-color: rgba(0, 102, 204, 0.03);
            word-wrap: break-word; overflow-wrap: break-word; white-space: pre-wrap !important;
        }

        .transcript-empty {
            color: #999; text-align: center; padding: 40px 20px; font-style: italic;
        }
        .transcript-empty::before { content: "💬"; display: block; font-size: 3em; margin-bottom: 10px; opacity: 0.3; }
    </style>

    <div id="streamlit-transcript-mirror">
        <div id="transcript-mirror-content">
            <div class="transcript-empty">Transcript will appear here once connected...</div>
        </div>
    </div>

    <script>
        // === Butter-smooth, word-by-word syncing without flicker ===
        // We DO NOT clear mirror content anymore. We only append deltas per message bubble.
        // The LiveKit iframe builds items inside #transcriptContent. We mirror incrementally.

        let lkTranscriptRef = null;
        let mirrorContent = null;
        let lastChildCount = 0;
        let lastLengths = []; // per-child text length to detect word-by-word growth

        function findLivekitTranscript() {
            try {
                // Prefer parent DOM (Streamlit > components)
                if (parent && parent.document) {
                    const fromParent = parent.document.getElementById('transcriptContent');
                    if (fromParent) return fromParent;
                }
            } catch (e) {}
            try {
                // Otherwise scan iframes in parent
                if (parent && parent.document) {
                    const iframes = parent.document.getElementsByTagName('iframe');
                    for (let i = 0; i < iframes.length; i++) {
                        try {
                            const doc = iframes[i].contentDocument || iframes[i].contentWindow.document;
                            const content = doc.getElementById('transcriptContent');
                            if (content) return content;
                        } catch (err) {}
                    }
                }
            } catch (e) {}
            return null;
        }

        function ensureMirrorRefs() {
            if (!mirrorContent) {
                mirrorContent = document.getElementById('transcript-mirror-content');
            }
            if (!lkTranscriptRef) {
                lkTranscriptRef = findLivekitTranscript();
            }
            return mirrorContent && lkTranscriptRef;
        }

        function cloneBaseStyles(src, dest) {
            // ensure structural classnames exist on mirror items for styling
            if (src.classList.contains('user')) dest.classList.add('user');
            if (src.classList.contains('ai')) dest.classList.add('ai');
            if (src.classList.contains('streaming')) dest.classList.add('streaming');
        }

        function incrementalMirrorUpdate() {
            if (!ensureMirrorRefs()) {
                requestAnimationFrame(incrementalMirrorUpdate);
                return;
            }

            const src = lkTranscriptRef; // #transcriptContent in LiveKit component
            const dst = mirrorContent;

            // Hide "empty" placeholder on first content
            if (src.children.length > 0) {
                const empty = dst.querySelector('.transcript-empty');
                if (empty) empty.remove();
            }

            const srcCount = src.children.length;
            const dstCount = dst.children.length;
            const minCount = Math.min(srcCount, dstCount);

            // 1) Update existing bubbles' text incrementally (no clear)
            for (let i = 0; i < minCount; i++) {
                const srcChild = src.children[i];
                const dstChild = dst.children[i];

                // Copy class state (user/ai/streaming markers for style)
                dstChild.className = srcChild.className;

                // We only update the inner message text area to avoid full node reflow.
                // Find the last <div> inside bubble which holds content (matches your LiveKit HTML)
                const srcMsg = srcChild.querySelector('.streaming-text') || srcChild.children[srcChild.children.length - 1];
                const dstMsg = dstChild.querySelector('.streaming-text') || dstChild.children[dstChild.children.length - 1];

                if (srcMsg && dstMsg) {
                    // Compare lengths and append only the delta text content when growing
                    const srcText = srcMsg.textContent || '';
                    const prevLen = lastLengths[i] || 0;

                    if (srcText.length > prevLen) {
                        // Append only new substring to keep animation buttery-smooth
                        const delta = srcText.substring(prevLen);
                        // Text node append (preserves spaces exactly)
                        dstMsg.appendChild(document.createTextNode(delta));
                        lastLengths[i] = srcText.length;
                        // Auto-scroll
                        const container = document.getElementById('streamlit-transcript-mirror');
                        if (container) container.scrollTop = container.scrollHeight;
                    } else if (srcText.length < prevLen) {
                        // Reset (e.g., message finalized/edited). Set full text once.
                        dstMsg.textContent = srcText;
                        lastLengths[i] = srcText.length;
                    }
                }
            }

            // 2) Append any NEW bubbles that appeared on source since last iteration
            if (srcCount > dstCount) {
                for (let i = dstCount; i < srcCount; i++) {
                    const srcChild = src.children[i];
                    const newBubble = document.createElement('div');
                    newBubble.className = srcChild.className.includes('transcript-item') ? srcChild.className : ('transcript-item ' + (srcChild.classList.contains('user') ? 'user' : 'ai'));

                    // Speaker header (clone visually)
                    const srcSpeaker = srcChild.querySelector('.speaker');
                    if (srcSpeaker) {
                        const speaker = document.createElement('div');
                        speaker.className = srcSpeaker.className;
                        speaker.textContent = srcSpeaker.textContent;
                        newBubble.appendChild(speaker);
                    }

                    // Message container
                    const srcMsg = srcChild.querySelector('.streaming-text') || srcChild.children[srcChild.children.length - 1];
                    const msg = document.createElement('div');
                    msg.className = (srcMsg && srcMsg.classList.contains('streaming-text')) ? 'streaming-text' : '';
                    msg.textContent = srcMsg ? (srcMsg.textContent || '') : '';
                    newBubble.appendChild(msg);

                    dst.appendChild(newBubble);
                    lastLengths[i] = msg.textContent.length;

                    // Auto-scroll
                    const container = document.getElementById('streamlit-transcript-mirror');
                    if (container) container.scrollTop = container.scrollHeight;
                }
            }

            // Track current number to avoid regressions
            lastChildCount = srcCount;

            requestAnimationFrame(incrementalMirrorUpdate);
        }

        // Kick off the butter-smooth incremental mirroring
        requestAnimationFrame(incrementalMirrorUpdate);
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

        # =========================================================
        # ========= 💡 BEGIN CRITICAL FIX 💡 ======================
        #
        # We are making the "sender" script more patient.
        # The main LiveKit iframe (livekit_component_utf8.html)
        # needs time to load and attach its 'sendTextMessageToLiveKit'
        # function to the parent window.
        #
        # Old: retries = 5, timeout = 200ms (1 second total)
        # New: retries = 20, timeout = 500ms (10 seconds total)
        #
        # =========================================================
        send_js = f"""
        <script>
            (function() {{
                const message = {repr(message_text)};
                console.log('📤 [Streamlit] Attempting to send message:', message);

                function attemptSend(retries = 20) {{
                    const parentReady = typeof parent !== 'undefined' && typeof parent.sendTextMessageToLiveKit === 'function';

                    if (parentReady) {{
                        try {{
                            const success = parent.sendTextMessageToLiveKit(message);
                            console.log('✅ [Streamlit] Message sent successfully:', success);

                            // ✅ Clear the textarea after sending
                            if (success) {{
                                const textarea = document.querySelector('textarea[placeholder="Type a message to send to the AI..."]');
                                if (textarea) textarea.value = '';
                            }}
                        }} catch (error) {{
                            console.error('❌ [Streamlit] Error calling sendTextMessageToLiveKit:', error);
                        }}
                    }} else if (retries > 0) {{
                        console.log('⏳ [Streamlit] sendTextMessageToLiveKit not ready, retrying... (' + retries + ' left)');
                        setTimeout(() => attemptSend(retries - 1), 500); // retry every 500ms
                    }} else {{
                        console.error('❌ [Streamlit] sendTextMessageToLiveKit function not found after all retries.');
                        alert('Error: Could not send text message. Please check the console (F12) for errors.');
                    }}
                }}

                attemptSend();
            }})();
        </script>
        """
        # =========================================================
        # ========= 💡 END CRITICAL FIX 💡 ========================
        # =========================================================

        components.html(send_js, height=0)
        st.toast("✅ Message sent to AI!", icon="💬")

        # Clear input
        st.session_state.message_counter += 1
        # st.rerun()
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

    # --- THIS SECTION IS UNCHANGED ---
    elif st.session_state.call_status == "Connected":
        # Read the HTML template from file
        import os

        st.write("🔑 Deepgram key detected:", bool(DEEPGRAM_API_KEY), DEEPGRAM_API_KEY[:8] + "...")

        html_file_path = os.path.join(os.path.dirname(__file__), '..', 'livekit_component_utf8.html')

        with open(html_file_path, 'r', encoding='utf-8') as file:
            livekit_html = file.read()

        # Replace placeholders with actual values
        # livekit_html = livekit_html.replace('wss://ai-mwc-jjlgi6ly.livekit.cloud', st.session_state.livekit_url)
        livekit_html = livekit_html.replace('LIVEKIT_URL_PLACEHOLDER', st.session_state.livekit_url)
        livekit_html = livekit_html.replace('LIVEKIT_TOKEN_PLACEHOLDER', st.session_state.livekit_token)
        livekit_html = livekit_html.replace('/*STREAMLIT_FLAG*/', 'false; //')
        livekit_html = livekit_html.replace('"DEEPGRAM_API_KEY_PLACEHOLDER"', f'"{DEEPGRAM_API_KEY}"')

        # Render the HTML
        # st.code(st.session_state.livekit_url, language="bash")
        # st.code(st.session_state.livekit_token, language="bash")

        components.html(livekit_html, height=300)

        if 'DEEPGRAM_API_KEY_PLACEHOLDER' in livekit_html:
            st.error("❌ Key replacement FAILED - placeholder still present!")
        else:
            st.success(f"✅ Key replaced successfully ({len(DEEPGRAM_API_KEY)} chars)")
        # Auto-start Deepgram STT after LiveKit component loads
        auto_stt_js = """
<script>
window.addEventListener('load', () => {
  function tryStart(retries = 10) {
    if (typeof parent.startDeepgramSTT === 'function') {
      console.log('🎙️ Auto-starting Deepgram STT...');
      parent.startDeepgramSTT();
    } else if (retries > 0) {
      console.log('⏳ Waiting for Deepgram STT initialization... attempts left:', retries);
      setTimeout(() => tryStart(retries - 1), 400);
    } else {
      console.error('❌ Deepgram STT failed to initialize.');
    }
  }
  tryStart();
});
</script>
"""
        components.html(auto_stt_js, height=0)

        # if "call_end_timestamp" not in st.session_state:
        #     st.session_state.call_end_timestamp = None

        if st.button("☎️ End Call", use_container_width=True):
            print("\n" + "=" * 80)
            print("🛑 END CALL BUTTON CLICKED")
            print("=" * 80)

            st.session_state.call_end_timestamp = datetime.now(UTC).isoformat()
            print("Call End timestamp:", st.session_state.call_end_timestamp)

            disconnect_js = """

            <script>
(function() {
    console.log('🔴 [Streamlit] Attempting to disconnect LiveKit room...');

    let disconnected = false;

    // Method 1: Try parent's exposed function
    if (typeof parent.livekitDisconnect === 'function') {
        console.log('✅ [Method 1] Found parent.livekitDisconnect()');
        try {
            disconnected = parent.livekitDisconnect();
            console.log('✅ [Method 1] Disconnect result:', disconnected);
        } catch (e) {
            console.error('❌ [Method 1] Error:', e);
        }
    }

    // Method 2: Try finding iframe directly
    if (!disconnected && parent.document) {
        console.log('🔍 [Method 2] Searching iframes...');
        const iframes = parent.document.querySelectorAll('iframe');
        console.log(`   Found ${iframes.length} iframes`);

        for (let iframe of iframes) {
            try {
                const win = iframe.contentWindow;
                if (win && typeof win.disconnectRoom === 'function') {
                    console.log('✅ [Method 2] Found iframe with disconnectRoom()');
                    disconnected = win.disconnectRoom();
                    console.log('✅ [Method 2] Disconnect result:', disconnected);
                    break;
                }
            } catch (e) {
                // Cross-origin iframe, skip
            }
        }
    }

    if (!disconnected) {
        console.error('❌ Could not disconnect room - function not found');
        alert('Warning: Could not disconnect room properly. Check console (F12).');
    } else {
        console.log('✅✅✅ ROOM DISCONNECTED SUCCESSFULLY ✅✅✅');
    }
})();
</script>
"""

            components.html(disconnect_js, height=0)

            time.sleep(0.5)

            with st.spinner("Ending call and signaling agent..."):
                try:
                    stop_payload = {"room_name": st.session_state.call_room_name}
                    response = requests.post(f"{backend_url}/calls/stop", json=stop_payload, timeout=2)

                    if response.status_code == 200:
                        st.toast("Agent signaled to end call.")
                        print("✅ Backend stop signal sent")
                except Exception as e:
                    print(f"⚠️ Error signaling agent: {e}")

            # Step 4: Immediately transition to "Ended" state
            st.session_state.call_status = "Ended"
            st.session_state.summary_poll_start = time.time()  # ✅ Start timer
            st.session_state.summary_attempts = 0

            print("✅Call DISCONNECTED - Starting 60s summary poll")
            print("=" * 80 + "\n")

            st.rerun()

    # --- END OF SECTION ---

    # st.markdown("---")
    # st.write(f"**Status:** {st.session_state.call_status}")
    # if st.session_state.start_time:
    #     # Ensure start_time is offset-aware UTC
    #     start_time_utc = st.session_state.start_time.replace(tzinfo=UTC)
    #     now_utc = datetime.now(UTC)
    #     duration = now_utc - start_time_utc
    #     st.write(f"**Duration:** {str(duration).split('.')[0]}")

# =========================================================
# ✅ NEW: NON-BLOCKING SUMMARY RETRIEVAL WITH COUNTDOWN
# =========================================================
if st.session_state.call_status == "Ended":
    print("\n" + "=" * 80)
    print("📊 POLLING FOR SUMMARY (Call already ended)")
    print("=" * 80)

    with st.container(border=True):
        st.subheader("🧠 Generating Call Summary...")

        # Calculate time remaining
        elapsed = time.time() - st.session_state.summary_poll_start
        remaining = max(0, 60 - int(elapsed))

        # Create placeholders for dynamic updates
        status_placeholder = st.empty()
        progress_placeholder = st.empty()

        # Show countdown timer
        if remaining > 0:
            status_placeholder.info(f"⏳ Waiting for AI to analyze conversation... **{remaining}s remaining**")
            progress_placeholder.progress((60 - remaining) / 60)
        else:
            status_placeholder.warning("⏱️ 60 seconds elapsed - finalizing...")

        # ✅ Poll for summary (non-blocking check)
        try:
            user_id_to_find = user_info.get('id') or user_info.get('_id') or user_info.get('user_id')
            current_room = st.session_state.call_room_name

            print(f"🔍 Polling attempt #{st.session_state.summary_attempts + 1}")
            print(f"   Looking for room: {current_room}")

            response = requests.get(f"{backend_url}/calls/", timeout=3)

            if response.status_code == 200:
                all_calls = response.json()
                print(f"📊 Got {len(all_calls)} total calls from backend")

                # Look for exact room match with summary
                if current_room:
                    room_matches = [c for c in all_calls if c.get("room_name") == current_room]
                    print(f"🎯 Found {len(room_matches)} call(s) with room_name={current_room}")

                    if room_matches:
                        latest_call = room_matches[0]  # Should only be one

                        if latest_call.get("summary"):
                            print("✅ SUMMARY FOUND!")
                            print(f"   Call ID: {latest_call.get('id')}")

                            # Store and transition to review
                            st.session_state.ai_analysis = {
                                "call_id": latest_call.get('id'),
                                "summary": latest_call.get('summary', 'N/A'),
                                "mood": latest_call.get('mood', 'neutral').capitalize(),
                                "topics": latest_call.get('topics', []),
                                "new_followups": latest_call.get('new_followups', [])
                            }
                            st.session_state.call_status = "Summary_Retrieved"
                            st.session_state.livekit_token = None
                            st.session_state.livekit_url = None
                            st.session_state.call_room_name = None
                            st.session_state.call_end_timestamp = None
                            st.session_state.summary_poll_start = None
                            st.session_state.summary_attempts = 0

                            status_placeholder.empty()
                            progress_placeholder.empty()
                            st.rerun()
                        else:
                            print("⏳ Room found but summary not ready yet")

            # Increment counter
            st.session_state.summary_attempts += 1

            # Check if we've exceeded 60 seconds
            if elapsed > 90:
                print("⏱️ 90-second timeout reached")
                status_placeholder.error(
                    "⏱️ Summary generation is taking longer than expected. "
                    "The backend may still be processing."
                )

                col1, col2 = st.columns(2)
                with col1:
                    if st.button("🔄 Keep Waiting", key="retry_summary"):
                        st.session_state.summary_poll_start = time.time()  # Reset timer
                        st.session_state.summary_attempts = 0
                        st.rerun()
                with col2:
                    if st.button("⏭️ Skip to Analytics", key="skip_to_analytics"):
                        st.session_state.call_status = "Not Connected"
                        st.session_state.call_room_name = None
                        st.session_state.call_end_timestamp = None
                        st.session_state.summary_poll_start = None
                        st.switch_page("pages/4_Analytics.py")
            else:
                # Auto-refresh every 2 seconds to update countdown
                time.sleep(2)
                st.rerun()

        except Exception as e:
            status_placeholder.error(f"Error: {e}")
            print(f"❌ Polling error: {e}")
            traceback.print_exc()

            if st.button("Continue to Analytics (Error Override)", key="error_continue"):
                st.session_state.call_status = "Not Connected"
                st.switch_page("pages/4_Analytics.py")

# =========================================================
# SUMMARY REVIEW FORM (UNCHANGED)
# =========================================================
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
                'sad': '😢 Sad',
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

            new_followups = analysis.get("new_followups", [])
            if new_followups:
                st.markdown("### 📌 New Follow-ups for Next Call")
                for followup in new_followups:
                    st.caption(f"• {followup}")

            if st.form_submit_button("Save & Go to Analytics", use_container_width=True):
                print("\n" + "=" * 80)
                print("💾 SAVING TO MEMORY")
                print("=" * 80)

                try:
                    final_topics = [t.strip() for t in topics_discussed.split(",") if t.strip()]

                    memory_payload = {
                        "user_id": user_info.get("id"),
                        "user_name": user_info.get("name"),
                        "call_id": analysis.get("call_id"),
                        "summary": summary_text,
                        "mood": detected_mood,
                        "topics": final_topics,
                        "date": datetime.now(UTC).isoformat(),
                    }

                    print(f"📦 Memory payload: {memory_payload}")

                    response = requests.post(
                        f"{backend_url}/memory/update",
                        json=memory_payload,
                        timeout=5
                    )

                    if response.status_code == 200:
                        result = response.json()
                        st.toast("✅ Memory updated!", icon="🧠")
                        print("✅ Memory saved to database")
                        print(f"   Result: {result}")
                    else:
                        st.warning("Could not update memory, but continuing...")
                        print(f"⚠️ Memory update failed: {response.text}")

                except Exception as e:
                    st.warning(f"Error updating memory: {e}")
                    print(f"❌ Memory update error: {e}")

                st.toast("Call log reviewed.", icon="✅")

                # ✅ Clear ALL call-related session state
                keys_to_clear = [
                    "call_status", "start_time", "ai_analysis",
                    "user_for_call", "call_room_name",
                    "livekit_token", "livekit_url", "call_end_timestamp",
                    "summary_poll_start", "summary_attempts"
                ]
                for key in keys_to_clear:
                    if key in st.session_state:
                        del st.session_state[key]

                print("=" * 80)
                print("✅ MEMORY SAVED - Redirecting to Analytics")
                print("=" * 80 + "\n")

                st.switch_page("pages/4_Analytics.py")