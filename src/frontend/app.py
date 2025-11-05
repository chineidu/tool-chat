"""Streamlit app for Smart RAG chat interface with streaming support."""

import asyncio
import json
import re
from collections import Counter
from typing import Any

import httpx
import plotly.graph_objects as go
import streamlit as st

from src.config import app_config
from src.schemas.types import Events, FeedbackType

# Configuration
API_BASE_URL: str = (
    f"http://{app_config.api_config.server.host}:{app_config.api_config.server.port}"
)
CHAT_STREAM_ENDPOINT: str = f"{API_BASE_URL}/api/v1/chat_stream"
FEEDBACK_ENDPOINT: str = f"{API_BASE_URL}/api/v1/feedback"
CHAT_HISTORY_ENDPOINT: str = f"{API_BASE_URL}/api/v1/chat_history"
REGISTER_ENDPOINT: str = f"{API_BASE_URL}/api/v1/auth/register"
LOGIN_ENDPOINT: str = f"{API_BASE_URL}/api/v1/auth/token"
USER_ME_ENDPOINT: str = f"{API_BASE_URL}/api/v1/auth/users/me"


def initialize_session_state() -> None:
    """Initialize session state variables."""
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "checkpoint_id" not in st.session_state:
        st.session_state.checkpoint_id = None
    if "message_count" not in st.session_state:
        st.session_state.message_count = 0
    if "feedback" not in st.session_state:
        st.session_state.feedback = {}
    # Authentication state
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "access_token" not in st.session_state:
        st.session_state.access_token = None
    if "user_info" not in st.session_state:
        st.session_state.user_info = None


def parse_sse_event(line: str) -> dict[str, Any] | None:
    """Parse a Server-Sent Event line."""
    if line.startswith("data: "):
        try:
            return json.loads(line[6:])
        except json.JSONDecodeError:
            return None
    return None


def clean_content(content: str) -> str:
    """Clean up content by removing HTML artifacts and citation brackets."""
    content = content.replace("[object Object]", "").strip()
    content = re.sub(r"\n\s*\n\s*\n+", "\n\n", content)
    content = re.sub(r"<details>\s*<summary>([^<]+)</summary>", r"**\1**", content)
    content = re.sub(r"</details>|<details>", "", content)
    content = content.replace("<summary>", "**").replace("</summary>", "**")
    # Remove source citations like [5T1-L1] or [5T1-L5-L10] but preserve markdown
    content = re.sub(r"\s*\[\d+[A-Z0-9\-]*\]\s*", " ", content)
    return re.sub(r"<[^>]+>", "", content)


async def send_feedback_to_api(message_index: int, feedback_type: str | None) -> None:
    """Send feedback data to FastAPI endpoint."""
    try:
        if message_index >= len(st.session_state.messages):
            st.toast("⚠️ Invalid message index", icon="⚠️")
            return

        message_data = st.session_state.messages[message_index]
        if message_data["role"] != "assistant":
            st.toast("⚠️ Can only provide feedback on assistant messages", icon="⚠️")
            return

        user_message = ""
        if (
            message_index > 0
            and st.session_state.messages[message_index - 1]["role"] == "user"
        ):
            user_message = st.session_state.messages[message_index - 1]["content"]

        # Ensure feedback is null for neutral, not the string 'None'
        feedback_value = feedback_type
        if feedback_value in ("neutral", "None", None):
            feedback_value = FeedbackType.NEUTRAL.value

        payload: dict[str, Any] = {
            "session_id": st.session_state.checkpoint_id or "no_session",
            "message_index": message_index,
            "user_message": user_message,
            "assistant_message": message_data["content"],
            "sources": message_data.get("sources", []) or [],
            "feedback": feedback_value,
        }

        headers = {}
        if st.session_state.access_token:
            headers["Authorization"] = f"Bearer {st.session_state.access_token}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                FEEDBACK_ENDPOINT, json=payload, headers=headers
            )
            response.raise_for_status()
            st.toast("✅ Feedback saved!", icon="✅")

    except httpx.HTTPStatusError as e:
        st.toast(f"⚠️ Server error: {e.response.status_code}", icon="⚠️")
    except Exception as e:
        st.toast(f"⚠️ Error: {str(e)}", icon="⚠️")


async def load_chat_history(checkpoint_id: str) -> bool:
    """Load chat history from a checkpoint ID."""
    try:
        headers = {}
        if st.session_state.access_token:
            headers["Authorization"] = f"Bearer {st.session_state.access_token}"

        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(
                CHAT_HISTORY_ENDPOINT,
                params={"checkpoint_id": checkpoint_id},
                headers=headers,
            )
            response.raise_for_status()
            data = response.json()

            loaded_messages = []
            for msg in data.get("messages", []):
                role = (
                    "user"
                    if msg["role"] == "human"
                    else "assistant"
                    if msg["role"] == "ai"
                    else msg["role"]
                )
                loaded_messages.append(
                    {"role": role, "content": msg["content"], "sources": None}
                )

            st.session_state.messages = loaded_messages
            st.session_state.checkpoint_id = checkpoint_id
            st.session_state.message_count = len(
                [m for m in loaded_messages if m["role"] == "assistant"]
            )
            st.session_state.feedback = {}
            return True

    except httpx.HTTPStatusError as e:
        if e.response.status_code == 404:
            st.toast(f"⚠️ Checkpoint '{checkpoint_id}' not found", icon="⚠️")
        else:
            st.toast(f"⚠️ Server error: {e.response.status_code}", icon="⚠️")
        return False
    except Exception as e:
        st.toast(f"⚠️ Error: {str(e)}", icon="⚠️")
        return False


def render_sources(sources: list[str]) -> None:
    """Render sources section."""
    if not sources:
        return

    with st.expander(
        f"📚 **{len(sources)} Source{'s' if len(sources) != 1 else ''} Referenced**",
        expanded=False,
    ):
        for idx, url in enumerate(sources, 1):
            try:
                parts = url.split("/")
                domain = parts[2] if len(parts) > 2 else url
                path = "/" + "/".join(parts[3:]) if len(parts) > 3 else ""
                display_path = (path[:50] + "...") if len(path) > 50 else path
            except Exception:
                domain = url
                display_path = ""

            st.markdown(f"**{idx}.** [{domain}]({url})")
            if display_path:
                st.caption(display_path)


def render_feedback_buttons(message_index: int) -> None:
    """Render feedback buttons."""
    feedback_key = f"msg_{message_index}"
    anim_key = f"anim_{message_index}"
    current_feedback = st.session_state.feedback.get(feedback_key)
    anim_state = st.session_state.get(anim_key, None)

    col1, col2, col3 = st.columns([0.1, 0.1, 0.8])

    with col1:
        btn_label = "👍"
        if anim_state == "positive":
            btn_label = "🔄"
        elif current_feedback == FeedbackType.POSITIVE:
            btn_label = "✅"
        if st.button(
            btn_label,
            key=f"up_{message_index}",
            help="Helpful",
            use_container_width=True,
        ):
            if current_feedback == FeedbackType.POSITIVE:
                # Toggle to neutral, do NOT send feedback
                st.session_state.feedback[feedback_key] = FeedbackType.NEUTRAL.value
                st.rerun()
                return
            # Start animation for positive feedback
            st.session_state[anim_key] = "positive"
            st.rerun()
            return

    with col2:
        btn_label = "👎"
        if anim_state == "negative":
            btn_label = "🔄"
        elif current_feedback == FeedbackType.NEGATIVE:
            btn_label = "❌"
        if st.button(
            btn_label,
            key=f"down_{message_index}",
            help="Not helpful",
            use_container_width=True,
        ):
            if current_feedback == FeedbackType.NEGATIVE:
                # Toggle to neutral, do NOT send feedback
                st.session_state.feedback[feedback_key] = FeedbackType.NEUTRAL.value
                st.rerun()
                return
            # Start animation for negative feedback
            st.session_state[anim_key] = "negative"
            st.rerun()
            return

    # Animation handler: if anim_state is set, immediately set feedback and clear anim
    if anim_state in ("positive", "negative"):
        # Remove the sleep that can cause rendering issues
        if anim_state == "positive":
            st.session_state.feedback[feedback_key] = FeedbackType.POSITIVE
        else:
            st.session_state.feedback[feedback_key] = FeedbackType.NEGATIVE
        st.session_state[anim_key] = None

        # Send feedback asynchronously without blocking
        try:
            asyncio.run(
                send_feedback_to_api(
                    message_index, st.session_state.feedback[feedback_key]
                )
            )
        except Exception as e:
            st.error(f"Failed to send feedback: {str(e)}")
        st.rerun()


def render_message(
    role: str,
    content: str,
    sources: list[str] | None = None,
    message_index: int | None = None,
) -> None:
    """Render a message."""
    with st.chat_message(role, avatar="👤" if role == "user" else "🤖"):
        st.markdown(clean_content(content))

        if sources:
            render_sources(sources)

        if message_index is not None and role == "assistant":
            render_feedback_buttons(message_index)


async def stream_chat_response(message: str, checkpoint_id: str | None = None) -> None:
    """Stream chat response from the API."""
    params: dict[str, str] = {"message": message}
    if checkpoint_id:
        params["checkpoint_id"] = checkpoint_id

    headers = {}
    if st.session_state.access_token:
        headers["Authorization"] = f"Bearer {st.session_state.access_token}"

    st.session_state.messages.append({"role": "user", "content": message})
    render_message("user", message)

    with st.chat_message("assistant", avatar="🤖"):
        status_container = st.empty()
        message_placeholder = st.empty()
        sources_container = st.container()

        full_response: str = ""
        sources: list[str] = []

        try:
            async with httpx.AsyncClient(timeout=60.0) as client:
                async with client.stream(
                    "GET", CHAT_STREAM_ENDPOINT, params=params, headers=headers
                ) as response:
                    response.raise_for_status()

                    async for line in response.aiter_lines():
                        if not line:
                            continue

                        event = parse_sse_event(line)
                        if not event:
                            continue

                        event_type = event.get("type")

                        if event_type == Events.CHECKPOINT:
                            st.session_state.checkpoint_id = event.get("checkpoint_id")

                        elif event_type == Events.SEARCH_START:
                            status_container.info(
                                f"🔍 Searching: **{event.get('query', '')}**"
                            )

                        elif event_type == Events.SEARCH_RESULT:
                            sources = event.get("urls", [])
                            if sources:
                                status_container.success(
                                    f"✅ Found **{len(sources)}** sources"
                                )

                        elif event_type == Events.DATE_RESULT:
                            status_container.info(f"📅 {event.get('result', '')}")

                        elif event_type == Events.CONTENT:
                            content_chunk = event.get("content", "")
                            if content_chunk:  # Only update if there's actual content
                                full_response += content_chunk
                                message_placeholder.markdown(
                                    clean_content(full_response) + " ▌"
                                )

                        elif event_type == Events.COMPLETION_END:
                            status_container.empty()
                            message_placeholder.markdown(clean_content(full_response))

                            if sources:
                                with sources_container:
                                    render_sources(sources)
                            break

                    # Ensure we always clear status and finalize response
                    status_container.empty()
                    if full_response:
                        message_placeholder.markdown(clean_content(full_response))
                    elif not full_response.strip():
                        # Handle case where no content was received
                        message_placeholder.info(
                            "🤔 I didn't receive any content. Please try asking again."
                        )
                        # Add fallback message to session state
                        fallback_content = "I didn't receive a proper response. Please try asking again."
                        full_response = fallback_content

        except httpx.HTTPError as e:
            status_container.empty()
            message_placeholder.error(f"❌ Connection Error: {str(e)}")
            st.info("💡 Make sure the FastAPI server is running")
            # Set error content for later handling
            full_response = f"❌ Connection Error: {str(e)}"
            return
        except Exception as e:
            status_container.empty()
            message_placeholder.error(f"❌ Error: {str(e)}")
            # Set error content for later handling
            full_response = f"❌ Error: {str(e)}"
            return

        # Add to session state (feedback buttons will be rendered when displaying messages)
        if full_response.strip():
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": full_response,
                    "sources": sources if sources else None,
                }
            )
            st.session_state.message_count += 1
            # Trigger rerun to display feedback buttons
            st.rerun()


async def authenticate_user(username: str, password: str) -> bool:
    """Authenticate user with the API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                LOGIN_ENDPOINT, data={"username": username, "password": password}
            )
            response.raise_for_status()
            data = response.json()
            st.session_state.access_token = data.get("access_token")
            st.session_state.authenticated = True
            # Get user info
            await get_user_info()
            return True
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 401:
            st.error("❌ Invalid username or password")
        else:
            st.error(f"❌ Login failed: {e.response.status_code}")
        return False
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return False


async def register_user(
    username: str, email: str, password: str, firstname: str, lastname: str
) -> bool:
    """Register a new user with the API."""
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(
                REGISTER_ENDPOINT,
                json={
                    "username": username,
                    "email": email,
                    "password": password,
                    "firstname": firstname,
                    "lastname": lastname,
                },
            )
            response.raise_for_status()
            st.success("✅ Registration successful! Please login.")
            return True
    except httpx.HTTPStatusError as e:
        if e.response.status_code == 400:
            error_detail = e.response.json().get("detail", "Registration failed")
            st.error(f"❌ {error_detail}")
        else:
            st.error(f"❌ Registration failed: {e.response.status_code}")
        return False
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        return False


async def get_user_info() -> None:
    """Get current user information."""
    if not st.session_state.access_token:
        return

    try:
        headers = {"Authorization": f"Bearer {st.session_state.access_token}"}
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.get(USER_ME_ENDPOINT, headers=headers)
            response.raise_for_status()
            st.session_state.user_info = response.json()
    except Exception as e:
        st.error(f"❌ Failed to get user info: {str(e)}")


def logout() -> None:
    """Logout user and clear session state."""
    st.session_state.authenticated = False
    st.session_state.access_token = None
    st.session_state.user_info = None
    st.session_state.messages = []
    st.session_state.checkpoint_id = None
    st.session_state.message_count = 0
    st.session_state.feedback = {}
    st.rerun()


def show_login_page() -> None:
    """Display the login page."""
    st.title("🔐 Login to AI Chat Assistant")

    with st.form("login_form"):
        username = st.text_input("Username", placeholder="Enter your username")
        password = st.text_input(
            "Password", type="password", placeholder="Enter your password"
        )

        col1, col2 = st.columns(2)
        with col1:
            login_submitted = st.form_submit_button(
                "🔑 Login", use_container_width=True
            )
        with col2:
            register_submitted = st.form_submit_button(
                "📝 Register", use_container_width=True
            )

        if login_submitted:
            if not username or not password:
                st.error("❌ Please fill in all fields")
            else:
                with st.spinner("Logging in..."):
                    if asyncio.run(authenticate_user(username, password)):
                        st.success("✅ Login successful!")
                        st.rerun()

        if register_submitted:
            st.session_state.show_register = True
            st.rerun()


def show_register_page() -> None:
    """Display the registration page."""
    st.title("📝 Register for AI Chat Assistant")

    with st.form("register_form"):
        col1, col2 = st.columns(2)
        with col1:
            firstname = st.text_input("First Name", placeholder="Enter your first name")
        with col2:
            lastname = st.text_input("Last Name", placeholder="Enter your last name")

        username = st.text_input("Username", placeholder="Choose a username")
        email = st.text_input("Email", placeholder="Enter your email")
        password = st.text_input(
            "Password", type="password", placeholder="Choose a password"
        )
        confirm_password = st.text_input(
            "Confirm Password", type="password", placeholder="Confirm your password"
        )

        col1, col2 = st.columns(2)
        with col1:
            register_submitted = st.form_submit_button(
                "📝 Register", use_container_width=True
            )
        with col2:
            back_submitted = st.form_submit_button(
                "⬅️ Back to Login", use_container_width=True
            )

        if register_submitted:
            if not all(
                [firstname, lastname, username, email, password, confirm_password]
            ):
                st.error("❌ Please fill in all fields")
            elif password != confirm_password:
                st.error("❌ Passwords do not match")
            elif len(password) < 6:
                st.error("❌ Password must be at least 6 characters long")
            else:
                with st.spinner("Registering..."):
                    if asyncio.run(
                        register_user(username, email, password, firstname, lastname)
                    ):
                        st.session_state.show_register = False
                        st.rerun()

        if back_submitted:
            st.session_state.show_register = False
            st.rerun()


def main() -> None:
    """Main Streamlit app."""
    st.set_page_config(
        page_title="AI Chat Assistant",
        page_icon="🤖",
        layout="wide",
        initial_sidebar_state="expanded",
    )

    # Force light theme
    st.markdown(
        """
        <script>
        var elements = window.parent.document.querySelectorAll('.stApp');
        elements[0].classList.remove('dark');
        </script>
        """,
        unsafe_allow_html=True,
    )

    st.markdown(
        """
        <style>
        /* Force light theme with soft colors */
        .stApp {
            background-color: #B9D9EB;
            color: #000000;
        }

        /* Main content area - soft light gray */
        .main {
            background-color: #B9D9EB;
            color: #000000;
        }

        /* All text black on white */
        .main * {
            color: #000000;
        }

        .main h1, .main h2, .main h3, .main h4, .main h5, .main h6 {
            color: #000000;
            font-weight: 600;
        }

        .main p, .main div, .main span, .main li {
            color: #000000;
        }

        /* Sidebar - light gray with dark text */
        [data-testid="stSidebar"] {
            background-color: #B9D9EB;
            border-right: 1px solid #cbd5e0;
        }

        [data-testid="stSidebar"] * {
            color: #000000 !important;
        }

        /* Buttons inside the sidebar may inherit global text color; force high-contrast
           styling so dark button backgrounds keep readable text and icons. */
        [data-testid="stSidebar"] .stButton > button,
        [data-testid="stSidebar"] .stButton button,
        [data-testid="stSidebar"] button.stButton,
        [data-testid="stSidebar"] .stButton {
            background-color: #23272f !important;
            color: #ffffff !important; /* force white text for legibility */
            -webkit-text-fill-color: #ffffff !important;
            border: 2px solid #23272f !important;
            box-shadow: none !important;
            font-weight: 600 !important;
        }

        /* Ensure any nested spans, icons or children also inherit the white color */
        [data-testid="stSidebar"] .stButton * {
            color: #ffffff !important;
            -webkit-text-fill-color: #ffffff !important;
        }

        /* Force SVG/icon fills to white so emoji-like icons or svg icons are legible */
        [data-testid="stSidebar"] .stButton svg path,
        [data-testid="stSidebar"] .stButton svg {
            fill: #ffffff !important;
            stroke: #ffffff !important;
        }

        [data-testid="stSidebar"] .stButton > button:hover,
        [data-testid="stSidebar"] .stButton:hover {
            background-color: #343843 !important;
            border-color: #343843 !important;
            color: #ffffff !important;
        }

        [data-testid="stSidebar"] .stButton > button:focus,
        [data-testid="stSidebar"] .stButton:focus {
            outline: none !important;
            box-shadow: 0 0 0 4px rgba(44,82,130,0.08) !important;
        }

        [data-testid="stSidebar"] .stMarkdown {
            color: #000000 !important;
        }

        [data-testid="stSidebar"] hr {
            border-color: rgba(0, 0, 0, 0.1) !important;
        }

        [data-testid="stSidebar"] h1,
        [data-testid="stSidebar"] h2,
        [data-testid="stSidebar"] h3,
        [data-testid="stSidebar"] h4 {
            color: #000000 !important;
        }

        /* Chat message containers */
        [data-testid="stChatMessageContainer"] {
            background-color: transparent;
        }

        /* ALL chat messages default to black text */
        [data-testid="stChatMessage"] {
            padding: 1rem;
            border-radius: 12px;
            margin: 0.5rem 0;
        }

        [data-testid="stChatMessage"] p,
        [data-testid="stChatMessage"] div,
        [data-testid="stChatMessage"] span,
        [data-testid="stChatMessage"] li,
        [data-testid="stChatMessage"] h1,
        [data-testid="stChatMessage"] h2,
        [data-testid="stChatMessage"] h3 {
            color: #000000 !important;
        }

        /* User messages - dark blue background with white text */
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-👤"]) {
            background-color: #2c5282;
            border: 2px solid #2c5282;
        }

        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-👤"]) p,
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-👤"]) div,
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-👤"]) span,
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-👤"]) li {
            color: #ffffff !important;
        }

        /* Assistant messages - light cream/white with black text */
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-🤖"]) {
            background-color: #ffffff;
            border: 2px solid #cbd5e0;
        }

        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-🤖"]) p,
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-🤖"]) div,
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-🤖"]) span,
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-🤖"]) li,
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-🤖"]) h1,
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-🤖"]) h2,
        [data-testid="stChatMessage"]:has([data-testid="chatAvatarIcon-🤖"]) h3 {
            color: #000000 !important;
        }

        /* Assistant avatar background - light gray for visibility */
        [data-testid="chatAvatarIcon-🤖"] {
            background-color: #B9D9EB !important;
            color: #23272f !important;
        }

        /* Feedback buttons - lighter dark gray */
        .stButton > button {
            background-color: #23272f;
            color: #ffd700;
            border: 2px solid #23272f;
            border-radius: 12px;
            font-weight: 500;
            font-size: 2rem;
            transition: all 0.2s ease;
        }

        .stButton > button:hover {
            background-color: #343843;
            border-color: #343843;
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(44, 82, 130, 0.15);
        }

        /* Info/Success messages - soft gray with black text */
        .stAlert {
            background-color: #B9D9EB;
            border-radius: 8px;
            border-left: 4px solid #2c5282;
            color: #000000;
        }

        .stAlert * {
            color: #000000 !important;
        }

        /* Text input - simple rectangular design */
        .stTextInput input {
            border: 2px solid #cbd5e0;
            border-radius: 0px;
            color: #000000;
            background-color: #ffffff;
            /* Ensure the caret is visible */
            caret-color: #2c5282 !important;
            -webkit-text-fill-color: #000000 !important;
        }

        .stTextInput input:focus {
            border-color: #2c5282;
            background-color: #ffffff;
            outline: none !important;
            box-shadow: 0 0 0 3px rgba(44, 82, 130, 0.08) !important;
        }

        /* Chat input container - simple design */
        [data-testid="stChatInput"] {
            border-top: 2px solid #cbd5e0;
            background-color: #B9D9EB !important;
        }

        /* Force bottom container background */
        [data-testid="stBottom"] {
            background-color: #B9D9EB !important;
        }

        /* Chat input wrapper */
        [data-testid="stChatInput"] > div {
            background-color: #B9D9EB !important;
        }

        [data-testid="stChatInput"] textarea {
            color: #000000 !important;
            background-color: #ffffff !important;
            border: 2px solid #cbd5e0 !important;
            border-radius: 0px !important;
            /* Make caret visible and ensure webkit text fill is set */
            caret-color: #2c5282 !important;
            -webkit-text-fill-color: #000000 !important;
        }

        [data-testid="stChatInput"] textarea:focus {
            border-color: #4C516D !important;
            outline: none !important;
            box-shadow: 0 0 0 3px rgba(76, 81, 109, 0.08) !important;
        }

        /* Bottom bar and all its children */
        .stChatFloatingInputContainer {
            background-color: #B9D9EB !important;
        }

        [data-testid="stChatInputContainer"] {
            background-color: #B9D9EB !important;
        }

        /* Footer area */
        footer {
            background-color: #B9D9EB !important;
        }

        footer * {
            background-color: #B9D9EB !important;
        }

        /* Expander (for sources) */
        .streamlit-expanderHeader {
            background-color: #B9D9EB;
            border: 1px solid #e0e0e0;
            border-radius: 8px;
            color: #000000;
        }

        .streamlit-expanderContent {
            border: 1px solid #e0e0e0;
            background-color: white;
        }

        /* Code blocks - light background with dark text */
        code {
            background-color: #ffffff;
            padding: 0.2rem 0.4rem;
            border-radius: 4px;
            color: #000000;
            border: 1px solid #cbd5e0;
        }

        pre {
            background-color: #ffffff !important;
            border: 2px solid #cbd5e0 !important;
            border-radius: 8px !important;
            padding: 1rem !important;
        }

        pre code {
            background-color: transparent !important;
            color: #000000 !important;
            border: none !important;
        }

        /* Streamlit code blocks */
        [data-testid="stCode"] {
            background-color: #ffffff !important;
            border: 2px solid #cbd5e0 !important;
        }

        [data-testid="stCode"] code {
            color: #000000 !important;
            background-color: transparent !important;
        }

        /* Metrics */
        [data-testid="stMetricValue"] {
            color: #000000 !important;
        }

        /* Links */
        a {
            color: #000000;
            text-decoration: underline;
        }

        a:hover {
            color: #333333;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )

    # Header
    st.title("🤖 AI Chat Assistant")
    st.caption("Powered by Agentic RAG • Real-time Web Search • Smart Responses")

    initialize_session_state()

    # Check authentication
    if not st.session_state.authenticated:
        if st.session_state.get("show_register", False):
            show_register_page()
        else:
            show_login_page()
        return

    # Authenticated user - show main chat interface

    # Sidebar
    with st.sidebar:
        # User info
        if st.session_state.user_info:
            st.header(f"👤 {st.session_state.user_info.get('username', 'User')}")
            st.caption(
                f"{st.session_state.user_info.get('firstname', '')} {st.session_state.user_info.get('lastname', '')}"
            )
            st.caption(st.session_state.user_info.get("email", ""))

        st.divider()

        st.header("⚙️ Settings")

        if st.button("🚪 Logout", use_container_width=True):
            logout()

        if st.button("🗑️ Clear Chat History", use_container_width=True):
            st.session_state.messages = []
            st.session_state.checkpoint_id = None
            st.session_state.message_count = 0
            st.session_state.feedback = {}
            st.rerun()

        st.divider()

        st.header("🔄 Continue Chat")
        checkpoint_input = st.text_input(
            "Checkpoint ID",
            placeholder="Enter checkpoint ID...",
            help="Load a previous conversation",
        )
        if st.button(
            "📥 Load", use_container_width=True, disabled=not checkpoint_input
        ):
            with st.spinner("Loading..."):
                if asyncio.run(load_chat_history(checkpoint_input)):
                    st.success(f"✅ Loaded {st.session_state.message_count} messages")
                    st.rerun()

        st.divider()

        st.header("📊 Stats")
        col1, col2 = st.columns(2)
        with col1:
            st.metric("Messages", st.session_state.message_count)
        with col2:
            st.metric(
                "Status", "🟢 Active" if st.session_state.checkpoint_id else "⚪ New"
            )

        if st.session_state.feedback:
            feedback_counter = Counter(st.session_state.feedback.values())
            positive = feedback_counter.get("positive", 0)
            negative = feedback_counter.get("negative", 0)
            neutral = feedback_counter.get("neutral", 0)
            total = positive + negative + neutral

            st.subheader("💭 Feedback Summary")
            col1, col2 = st.columns(2)
            col1.metric("👍 Positive", positive)
            col2.metric("👎 Negative", negative)
            st.caption(f"😐 Neutral: {neutral}")

            if total > 0:
                labels = ["Positive", "Negative", "Neutral"]
                values = [positive, negative, neutral]
                colors = ["#4CAF50", "#F44336", "#BDBDBD"]
                fig = go.Figure(
                    data=[
                        go.Pie(
                            labels=labels,
                            values=values,
                            marker={"colors": colors},
                            hole=0.5,
                        )
                    ]
                )
                fig.update_layout(
                    margin={"l": 0, "r": 0, "t": 0, "b": 0}, showlegend=True, height=200
                )
                st.plotly_chart(fig, use_container_width=True)

                if positive + negative > 0:
                    satisfaction = (positive / (positive + negative)) * 100
                    st.progress(positive / (positive + negative))
                    st.caption(f"{satisfaction:.0f}% satisfaction (of rated feedback)")
                else:
                    st.caption("No rated feedback yet.")

        st.divider()

        st.header("💡 About")
        st.markdown("""
        **🧠 LangGraph** - Workflow orchestration
        **🔍 Tavily** - Web search
        **🗓️ Date Tool** - Time operations
        **⚡ FastAPI** - Streaming backend
        **🎨 Streamlit** - UI interface
        """)

        if st.session_state.checkpoint_id:
            st.divider()
            st.subheader("🔑 Checkpoint ID")
            st.code(st.session_state.checkpoint_id)
            st.info("💡 Save this ID to resume later")

    # Main chat area
    if not st.session_state.messages:
        st.info(
            "👋 Welcome! Ask me anything - I can search the web and provide detailed answers."
        )
    else:
        assistant_count = 0
        for msg in st.session_state.messages:
            if msg["role"] == "assistant":
                message_index = assistant_count
                assistant_count += 1
            else:
                message_index = None
            render_message(
                msg["role"], msg["content"], msg.get("sources"), message_index
            )

    # Chat input
    if prompt := st.chat_input("💬 Type your message here..."):
        asyncio.run(stream_chat_response(prompt, st.session_state.checkpoint_id))


if __name__ == "__main__":
    main()
