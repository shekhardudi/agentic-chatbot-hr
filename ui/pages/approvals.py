import streamlit as st

from config import MANAGERS, PAGE_TITLE
from api_client import get_pending_approvals
from components.persona_selector import manager_selector
from components.approval_card import approval_card

st.title("Manager Approval Queue")

# --- Sidebar: manager persona ---
with st.sidebar:
    st.header("Manager Persona")
    manager = manager_selector(MANAGERS)
    st.divider()
    st.caption(f"Acting as: `{manager['email']}`")
    if st.button("Refresh"):
        st.rerun()

approver_email = st.session_state.get("approver_email", MANAGERS[0]["email"])

# --- Load pending approvals ---
try:
    pending = get_pending_approvals()
except Exception as e:
    st.error(f"Could not load approvals: {e}")
    pending = []

if not pending:
    st.info("No pending approval requests.")
else:
    st.subheader(f"{len(pending)} pending request(s)")
    for req in pending:
        approval_card(req, approver_email)
