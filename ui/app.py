"""
Streamlit entry point — page router.
Uses st.navigation to show only Chat and Approvals pages (no extra 'App' page).
"""
import streamlit as st

chat = st.Page("pages/chat.py", title="Chat", icon="💬", default=True)
approvals = st.Page("pages/approvals.py", title="Manager Approvals", icon="✅")

pg = st.navigation([chat, approvals])
pg.run()
