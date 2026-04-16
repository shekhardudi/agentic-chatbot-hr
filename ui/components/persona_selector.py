import streamlit as st


def persona_selector(personas: list[dict], key: str = "persona") -> dict:
    """Dropdown that sets employee_email in session_state."""
    selected = st.selectbox(
        "Employee Persona",
        options=personas,
        format_func=lambda p: f"{p['full_name']} — {p.get('role', p['email'])}",
        key=key,
    )
    st.session_state["employee_email"] = selected["email"]
    return selected


def manager_selector(managers: list[dict], key: str = "manager_persona") -> dict:
    """Dropdown for manager persona on the approvals page."""
    selected = st.selectbox(
        "Approving as",
        options=managers,
        format_func=lambda m: f"{m['full_name']} ({m['email']})",
        key=key,
    )
    st.session_state["approver_email"] = selected["email"]
    return selected
