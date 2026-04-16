"""
Streamlit entry point — page router.
Streamlit automatically discovers files in the pages/ directory as additional pages.
This file acts as the Home page (Chat view).
"""
import uuid
import streamlit as st

from config import PERSONAS, PAGE_TITLE
from api_client import send_message
from components.persona_selector import persona_selector
from components.message_bubble import message_bubble, status_badge

st.set_page_config(
    page_title=PAGE_TITLE,
    page_icon="💼",
    layout="wide",
    initial_sidebar_state="expanded",
)

st.title("Agentic HR Assistant")
st.caption("Ask questions about leave, HR policy, or request software access.")

# --- Sidebar ---
with st.sidebar:
    st.header("Employee Persona")
    persona = persona_selector(PERSONAS)
    st.divider()
    st.caption(f"Email: `{persona['email']}`")

    st.page_link("pages/chat.py", label="Chat", icon="💬")
    st.page_link("pages/approvals.py", label="Manager Approvals", icon="✅")

    if st.button("New conversation"):
        st.session_state.pop("chat_history", None)
        st.session_state.pop("session_id", None)
        st.rerun()

# --- Session state ---
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())
if "employee_email" not in st.session_state:
    st.session_state["employee_email"] = PERSONAS[0]["email"]

# --- Render history ---
for msg in st.session_state["chat_history"]:
    message_bubble(msg["role"], msg["content"], msg.get("citations"))
    if msg.get("status") and msg.get("request_id"):
        status_badge(msg["status"], msg.get("request_id"))

# --- Input ---
user_input = st.chat_input("Ask an HR question…")
if user_input:
    st.session_state["chat_history"].append({"role": "user", "content": user_input})
    message_bubble("user", user_input)

    with st.spinner("Thinking…"):
        try:
            response = send_message(
                employee_email=st.session_state["employee_email"],
                message=user_input,
                session_id=st.session_state["session_id"],
            )
            assistant_msg = {
                "role": "assistant",
                "content": response.get("response", ""),
                "citations": response.get("citations", []),
                "status": response.get("status"),
                "request_id": response.get("request_id"),
            }
            st.session_state["chat_history"].append(assistant_msg)
            message_bubble("assistant", assistant_msg["content"], assistant_msg["citations"])
            if assistant_msg.get("status") and assistant_msg.get("request_id"):
                status_badge(assistant_msg["status"], assistant_msg["request_id"])
        except Exception as e:
            st.error(f"Backend error: {e}")
