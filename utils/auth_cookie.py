# utils/auth_cookie.py
import streamlit as st
from datetime import datetime, timedelta
import streamlit.components.v1 as components
import json
import os
from pathlib import Path

SESSION_TIMEOUT = 480  # 8 hours in minutes
SESSION_FILE = Path(__file__).parent.parent / '.streamlit_session.json'


def _read_session_file():
    """Read session from file"""
    try:
        if SESSION_FILE.exists():
            with open(SESSION_FILE, 'r') as f:
                return json.load(f)
    except Exception as e:
        print(f"⚠️ Error reading session file: {e}")
    return None


def _write_session_file(data):
    """Write session to file"""
    try:
        with open(SESSION_FILE, 'w') as f:
            json.dump(data, f)
        return True
    except Exception as e:
        print(f"⚠️ Error writing session file: {e}")
        return False


def _delete_session_file():
    """Delete session file"""
    try:
        if SESSION_FILE.exists():
            SESSION_FILE.unlink()
            print("🗑️ Session file deleted")
    except Exception as e:
        print(f"⚠️ Error deleting session file: {e}")


def set_auth_cookie():
    """Set authentication in session state and file"""
    current_time = datetime.now()
    expire_time = current_time + timedelta(minutes=SESSION_TIMEOUT)

    # Store in session state
    st.session_state.authenticated = True
    st.session_state.login_time = current_time.isoformat()
    st.session_state.last_activity = current_time.isoformat()
    st.session_state.expire_time = expire_time.isoformat()
    st.session_state.logout_triggered = False

    # Store in file
    session_data = {
        'authenticated': True,
        'login_time': current_time.isoformat(),
        'last_activity': current_time.isoformat(),
        'expire_time': expire_time.isoformat()
    }

    _write_session_file(session_data)

    print(f"✅ Auth cookie set: {st.session_state.authenticated}")


def is_authenticated():
    """Check if user is authenticated"""

    # First check if we need to restore from file
    if 'authenticated' not in st.session_state or not st.session_state.authenticated:
        session_data = _read_session_file()

        if session_data and session_data.get('authenticated'):
            # Check if session is still valid
            try:
                expire_time = datetime.fromisoformat(session_data['expire_time'])

                if datetime.now() < expire_time:
                    # Restore session
                    st.session_state.authenticated = True
                    st.session_state.login_time = session_data['login_time']
                    st.session_state.last_activity = datetime.now().isoformat()
                    st.session_state.expire_time = session_data['expire_time']
                    st.session_state.logout_triggered = False

                    # Update last activity in file
                    session_data['last_activity'] = st.session_state.last_activity
                    _write_session_file(session_data)

                    print("✅ Session restored from file")
                    return True
                else:
                    # Session expired
                    print("⏰ Session expired")
                    _delete_session_file()
                    return False
            except Exception as e:
                print(f"⚠️ Error checking session expiration: {e}")
                return False

    # Check session state
    if 'authenticated' not in st.session_state:
        return False

    if not st.session_state.authenticated:
        return False

    # Check if user explicitly logged out
    if st.session_state.get('logout_triggered', False):
        return False

    # Check expiration
    if 'expire_time' in st.session_state:
        try:
            expire_time = datetime.fromisoformat(st.session_state.expire_time)
            if datetime.now() >= expire_time:
                print("⏰ Session expired")
                clear_auth()
                return False
        except Exception as e:
            print(f"⚠️ Error checking expiration: {e}")

    # Update last activity
    st.session_state.last_activity = datetime.now().isoformat()

    # Update file (non-blocking, don't wait for write)
    try:
        session_data = _read_session_file()
        if session_data:
            session_data['last_activity'] = st.session_state.last_activity
            _write_session_file(session_data)
    except:
        pass

    return True


def clear_auth():
    """Clear authentication state"""
    st.session_state.authenticated = False
    st.session_state.logout_triggered = True

    keys_to_clear = ['login_time', 'last_activity', 'expire_time']
    for key in keys_to_clear:
        if key in st.session_state:
            del st.session_state[key]

    # Delete session file
    _delete_session_file()

    print("🗑️ Auth cleared")


def inject_navigation_blocker():
    """Prevent forward navigation after logout"""
    if st.session_state.get('logout_triggered', False):
        components.html("""
        <script>
            history.pushState(null, null, location.href);
            window.onpopstate = function () {
                history.go(1);
                alert('⚠️ You have been logged out. Please login again.');
            };
        </script>
        """, height=0)


def inject_back_button_limiter():
    """Prevent back navigation to login page when authenticated"""
    if 'authenticated' in st.session_state and st.session_state.authenticated:
        components.html("""
        <script>
            if (!sessionStorage.getItem('entryPage')) {
                sessionStorage.setItem('entryPage', window.location.pathname);
            }

            window.addEventListener('popstate', function(e) {
                const currentPath = window.location.pathname;
                if (currentPath.includes('login')) {
                    const entryPage = sessionStorage.getItem('entryPage') || '/Users';
                    e.preventDefault();
                    window.location.replace(entryPage);
                }
            });
        </script>
        """, height=0)