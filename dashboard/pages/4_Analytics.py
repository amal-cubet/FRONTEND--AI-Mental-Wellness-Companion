import streamlit as st
import pandas as pd
import altair as alt
import requests
from datetime import datetime, timedelta
from collections import Counter

# --- HIDE DEFAULT NAVIGATION ---
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

st.title("📊 Analytics Dashboard")


# --- FETCH DATA ---
@st.cache_data(ttl=60)
def fetch_call_logs():
    try:
        response = requests.get(f"{backend_url}/calls/", timeout=5)
        if response.status_code == 200:
            return response.json()
        return []
    except Exception as e:
        st.error(f"Error fetching call logs: {e}")
        return []


call_logs = fetch_call_logs()

if not call_logs:
    st.warning("🔭 No call data available yet. Make some calls to see analytics!")
    st.stop()

# Convert to DataFrame
df = pd.DataFrame(call_logs)

# Parse dates
df['start_time'] = pd.to_datetime(df['start_time'])
df['end_time'] = pd.to_datetime(df['end_time'])
df['date'] = df['end_time'].dt.date
df['duration_seconds'] = (df['end_time'] - df['start_time']).dt.total_seconds()


def format_duration(seconds):
    minutes = int(seconds // 60)
    secs = int(seconds % 60)
    return f"{minutes}m {secs}s"


df['duration_display'] = df['duration_seconds'].apply(format_duration)

# Map moods to scores
mood_scores = {'happy': 1, 'neutral': 0, 'sad': -1}
df['mood_score'] = df['mood'].map(mood_scores).fillna(0)

# --- MAIN LAYOUT: LEFT CONTENT + RIGHT SIDEBAR ---
col_main, col_topics = st.columns([3, 1])

with col_main:
    # --- MOOD GRAPH ---
    st.subheader("📈 Mood Over Time")

    mood_by_date = df.groupby('date').agg({
        'mood_score': 'mean',
        'id': 'count'
    }).reset_index()
    mood_by_date.columns = ['date', 'avg_mood', 'call_count']
    mood_by_date['date'] = pd.to_datetime(mood_by_date['date'])

    if len(mood_by_date) > 0:
        chart = alt.Chart(mood_by_date).mark_line(
            point=alt.OverlayMarkDef(filled=True, size=100, color='#FF6B6B'),
            color='#4ECDC4',
            strokeWidth=3
        ).encode(
            x=alt.X('date:T', title='Date', axis=alt.Axis(format='%b %d')),
            y=alt.Y('avg_mood:Q', title='Average Mood Score',
                    scale=alt.Scale(domain=[-1, 1]),
                    axis=alt.Axis(grid=True)),
            tooltip=[
                alt.Tooltip('date:T', title='Date', format='%B %d, %Y'),
                alt.Tooltip('avg_mood:Q', title='Avg Mood', format='.2f'),
                alt.Tooltip('call_count:Q', title='Calls')
            ]
        ).properties(height=300).interactive()

        st.altair_chart(chart, use_container_width=True)

        # Metrics below chart
        col1, col2, col3 = st.columns(3)
        with col1:
            st.metric("Total Calls", len(df))
        with col2:
            overall_avg = df['mood_score'].mean()
            mood_label = "😊 Positive" if overall_avg > 0.3 else "😢 Negative" if overall_avg < -0.3 else "😐 Neutral"
            st.metric("Overall Mood", mood_label)
        with col3:
            mood_counts = df['mood'].value_counts()
            most_common_mood = mood_counts.index[0] if len(mood_counts) > 0 else "neutral"
            emoji = {'happy': '😊', 'sad': '😢', 'neutral': '😐'}.get(most_common_mood, '😐')
            st.metric("Most Common", f"{emoji} {most_common_mood.title()}")
    else:
        st.info("Not enough data for mood trends")

    st.markdown("---")

    # --- RECENT CALLS TABLE ---
    st.subheader("📞 Recent Calls")

    display_df = df.sort_values('end_time', ascending=False).head(20).copy()

    # Format for display
    display_df['date_display'] = display_df['end_time'].dt.strftime('%b %d, %Y %H:%M')
    display_df['summary_preview'] = display_df['summary'].apply(
        lambda x: x[:60] + "..." if len(x) > 60 else x
    )
    display_df['mood_display'] = display_df['mood'].map({
        'happy': '😊 Happy',
        'sad': '😢 Sad',
        'neutral': '😐 Neutral'
    })

    # Create table with Action column
    table_df = display_df[[
        'id', 'user_name', 'date_display', 'duration_display',
        'mood_display', 'summary_preview'
    ]].copy()

    # Add Action column - reset to empty if transcript is showing
    if st.session_state.get('show_transcript', False):
        table_df['Action'] = ""
    else:
        table_df['Action'] = ""

    table_df.columns = ['id', 'User', 'Date', 'Duration', 'Mood', 'Summary', 'Action']

    # Display as interactive table with action column
    event = st.data_editor(
        table_df,
        hide_index=True,
        use_container_width=True,
        key="calls_table",
        column_config={
            "id": None,
            "Action": st.column_config.SelectboxColumn(
                "Action",
                options=["", "📄 View Transcript"],
                help="Choose an action for this call",
            ),
            "User": st.column_config.TextColumn("User", disabled=True),
            "Date": st.column_config.TextColumn("Date", disabled=True),
            "Duration": st.column_config.TextColumn("Duration", disabled=True),
            "Mood": st.column_config.TextColumn("Mood", disabled=True),
            "Summary": st.column_config.TextColumn("Summary", disabled=True),
        },
        disabled=["User", "Date", "Duration", "Mood", "Summary"]
    )

    # Handle action selection
    if event is not None and not st.session_state.get('show_transcript', False):
        # Check for changes in the Action column
        for idx, row in event.iterrows():
            if row['Action'] == "📄 View Transcript":
                selected_call_id = row['id']
                print(f"\n{'=' * 80}")
                print(f"🎯 TRANSCRIPT VIEW REQUESTED")
                print(f"   Selected call_id: {selected_call_id}")
                print(f"   Row index: {idx}")
                print(f"   Available columns: {list(row.index)}")
                print(f"{'=' * 80}\n")

                st.session_state.selected_call_id = selected_call_id
                st.session_state.show_transcript = True
                st.rerun()
                break

with col_topics:
    st.subheader("☁️ Top Topics")

    # Collect all topics
    all_topics = []
    for topics in df['topics']:
        if isinstance(topics, list):
            all_topics.extend(topics)

    topic_counts = Counter(all_topics)
    top_topics = topic_counts.most_common(15)

    if top_topics:
        # Display as styled chips
        st.markdown("""
        <style>
        .topic-chip {
            display: inline-block;
            background: linear-gradient(135deg, #535353 0%, #1e1c20 100%);
            color: white;
            padding: 8px 16px;
            margin: 5px;
            border-radius: 20px;
            font-size: 14px;
            font-weight: 500;
            box-shadow: 0 2px 5px rgba(0,0,0,0.1);
            transition: transform 0.2s;
        }
        .topic-chip:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 8px rgba(0,0,0,0.2);
        }
        .topic-count {
            background: rgba(255,255,255,0.3);
            padding: 2px 8px;
            border-radius: 10px;
            margin-left: 8px;
            font-size: 12px;
        }
        .topics-container {
            max-height: 800px;
            overflow-y: auto;
            padding: 10px;
            background: rgba(255,255,255,0.02);
            border-radius: 12px;
        }
        .topics-container::-webkit-scrollbar {
            width: 8px;
        }
        .topics-container::-webkit-scrollbar-track {
            background: rgba(255,255,255,0.05);
            border-radius: 10px;
        }
        .topics-container::-webkit-scrollbar-thumb {
            background: rgba(102, 126, 234, 0.6);
            border-radius: 10px;
        }
        </style>
        """, unsafe_allow_html=True)

        topics_html = '<div class="topics-container">'
        for topic, count in top_topics:
            topics_html += f'<div class="topic-chip">{topic} <span class="topic-count">{count}x</span></div>'
        topics_html += '</div>'

        st.markdown(topics_html, unsafe_allow_html=True)
    else:
        st.info("No topics discussed yet")

# --- TRANSCRIPT VIEWER (FULL WIDTH OUTSIDE COLUMNS) ---
if st.session_state.get('show_transcript', False):
    call_id = st.session_state.selected_call_id
    call = df[df['id'] == call_id].iloc[0]

    # st.markdown("---")
    st.markdown("---")

    # Create full-width modal container
    with st.container():
        # Header
        col_header, col_close = st.columns([5, 1])
        with col_header:
            st.markdown(f"### 💬 {call['user_name']}'s Conversation")
            st.caption(f"📅 {pd.to_datetime(call['end_time']).strftime('%B %d, %Y at %H:%M')}")
        with col_close:
            if st.button("✕ Close", key="close_transcript_top", use_container_width=True, type="secondary"):
                st.session_state.show_transcript = False
                st.rerun()

        st.markdown("---")

        # Metadata cards
        col1, col2, col3, col4 = st.columns(4)
        with col1:
            st.metric("⏱️ Duration", call['duration_display'])
        with col2:
            mood_emoji = {'happy': '😊', 'sad': '😢', 'neutral': '😐'}.get(call['mood'], '😐')
            st.metric("Mood", f"{mood_emoji} {call['mood'].title()}")
        with col3:
            st.metric("💬 Messages", len(call.get('transcript', [])))

        # Topics badges
        # if call['topics']:
        #     st.markdown("**🏷️ Topics:**")
        #     topics_html = " ".join([
        #         f"<span style='background: linear-gradient(135deg, #667eea 0%, #764ba2 100%); "
        #         f"color: white; padding: 6px 14px; border-radius: 20px; margin: 4px; "
        #         f"display: inline-block; font-size: 13px; font-weight: 500; "
        #         f"box-shadow: 0 2px 8px rgba(102, 126, 234, 0.3);'>{topic}</span>"
        #         for topic in call['topics']
        #     ])
        #     st.markdown(topics_html, unsafe_allow_html=True)

        st.markdown("### 💬 Conversation")

        # ✅ FIXED: Handle both formats (old string format and new dict format)
        if call.get('transcript'):
            transcript_data = call['transcript']

            st.markdown("""
            <style>
            .chat-window {
                background: linear-gradient(to bottom, #e8eaf6 0%, #f5f5f5 100%);
                border-radius: 16px;
                padding: 25px;
                max-height: 500px;
                overflow-y: auto;
                border: 2px solid #e0e0e0;
                box-shadow: inset 0 2px 10px rgba(0,0,0,0.05);
            }
            .chat-window::-webkit-scrollbar {
                width: 12px;
            }
            .chat-window::-webkit-scrollbar-track {
                background: rgba(0,0,0,0.05);
                border-radius: 10px;
                margin: 10px;
            }
            .chat-window::-webkit-scrollbar-thumb {
                background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
                border-radius: 10px;
                border: 2px solid rgba(255,255,255,0.3);
            }
            .message-bubble {
                margin: 15px 0;
                padding: 15px 20px;
                border-radius: 18px;
                max-width: 75%; 
                animation: fadeIn 0.3s ease-in;
                box-shadow: 0 2px 8px rgba(0,0,0,0.1);
                line-height: 1.6;
            }
            @keyframes fadeIn {
                from { opacity: 0; transform: translateY(10px); }
                to { opacity: 1; transform: translateY(0); }
            }
            .user-bubble {
                background: linear-gradient(135deg, #212226 0%, #4a4251 100%);
                color: white;
                margin-left: auto;
                text-align: right;
                border-bottom-right-radius: 4px;
            }
            .ai-bubble {
                background: white;
                color: #333;
                margin-right: auto;
                border-bottom-left-radius: 4px;
                border-left: 4px solid #667eea;
            }
            .message-sender {
                font-size: 11px;
                font-weight: 700;
                text-transform: uppercase;
                letter-spacing: 1px;
                margin-bottom: 8px;
                opacity: 0.8;
            }
            .user-bubble .message-sender {
                color: rgba(255,255,255,0.9);
            }
            .ai-bubble .message-sender {
                color: #667eea;
            }
            .message-text {
                font-size: 15px;
                line-height: 1.6;
            }
            </style>
            """, unsafe_allow_html=True)

            # ✅ Build chat HTML with format detection
            chat_html = '<div class="chat-window">'

            for i, entry in enumerate(transcript_data):
                # ✅ Handle new dict format: {"speaker": "user", "text": "..."}
                if isinstance(entry, dict):
                    speaker = entry.get('speaker', 'unknown')
                    text = entry.get('text', '')

                    # Escape HTML to prevent injection
                    text = text.replace('<', '&lt;').replace('>', '&gt;')

                    if speaker.lower() == 'user':
                        chat_html += f'''<div style="display: flex; justify-content: flex-end;">
                            <div class="message-bubble user-bubble">
                                <div class="message-sender">👤 {call['user_name']}</div>
                                <div class="message-text">{text}</div>
                            </div>
                        </div>'''
                    else:  # AI
                        chat_html += f'''<div style="display: flex; justify-content: flex-start;">
                            <div class="message-bubble ai-bubble">
                                <div class="message-sender">🤖 AI Companion</div>
                                <div class="message-text">{text}</div>
                            </div>
                        </div>'''

                # ✅ Handle legacy string format: "User: text" or "AI: text"
                elif isinstance(entry, str):
                    if entry.startswith("User:"):
                        text = entry.replace("User:", "").strip()
                        text = text.replace('<', '&lt;').replace('>', '&gt;')
                        chat_html += f'''<div style="display: flex; justify-content: flex-end;">
                            <div class="message-bubble user-bubble">
                                <div class="message-sender">👤 {call['user_name']}</div>
                                <div class="message-text">{text}</div>
                            </div>
                        </div>'''
                    elif entry.startswith("AI:") or entry.startswith("Assistant:"):
                        text = entry.replace("AI:", "").replace("Assistant:", "").strip()
                        text = text.replace('<', '&lt;').replace('>', '&gt;')
                        chat_html += f'''<div style="display: flex; justify-content: flex-start;">
                            <div class="message-bubble ai-bubble">
                                <div class="message-sender">🤖 AI Companion</div>
                                <div class="message-text">{text}</div>
                            </div>
                        </div>'''

            chat_html += '</div>'

            st.markdown(chat_html, unsafe_allow_html=True)
        else:
            st.warning("🔭 No transcript available for this call")

        st.markdown("---")

        # # Bottom actions
        # col_action1, col_action2, col_action3 = st.columns([1, 1, 1])
        # with col_action2:
        #     if st.button("Close Transcript", key="close_bottom", use_container_width=True, type="primary"):
        #         st.session_state.show_transcript = False
        #         st.rerun()

# --- REFRESH BUTTON ---

col1, col2, col3 = st.columns([1, 1, 1])
with col2:
    if st.button("🔄 Refresh Data", use_container_width=True):
        st.cache_data.clear()
        st.rerun()