import streamlit as st
from api_client import submit_decision

_STATUS_STYLE = {
    "pending_approval": ("🟡", "Pending Approval"),
    "approved": ("🟢", "Approved"),
    "denied": ("🔴", "Denied"),
}


def approval_card(request: dict, approver_email: str) -> None:
    """Renders one pending access request with Approve / Deny buttons."""
    rid = request["request_id"]
    name = request.get("requester_name", "")
    email = request.get("requester_email", "Unknown")
    packages = request.get("packages", [])
    status = request.get("status", "pending_approval")
    created = request.get("created_ts", "")
    icon, label = _STATUS_STYLE.get(status, ("⚪", status))

    with st.container(border=True):
        # Header row: name + status badge
        head_left, head_right = st.columns([3, 1])
        with head_left:
            display = f"**{name}**  \n{email}" if name else f"**{email}**"
            st.markdown(display)
        with head_right:
            st.markdown(
                f"<span style='padding:2px 8px;border-radius:10px;"
                f"background:#444;color:#fff;font-size:0.85em'>{icon} {label}</span>",
                unsafe_allow_html=True,
            )

        # Packages
        if packages:
            pkg_tags = " ".join(f"`{p}`" for p in packages)
            st.markdown(f"📦 **Packages:** {pkg_tags}")

        # Metadata row
        meta_parts = [f"**ID:** `{rid}`"]
        if created:
            meta_parts.append(f"**Created:** {created}")
        st.caption(" · ".join(meta_parts))

        # Action buttons
        col1, col2, _ = st.columns([1, 1, 3])
        with col1:
            if st.button("✅ Approve", key=f"approve_{rid}", type="primary"):
                try:
                    submit_decision(rid, "approved", approver_email)
                    st.success("Approved — provisioning triggered.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        with col2:
            if st.button("❌ Deny", key=f"deny_{rid}"):
                try:
                    submit_decision(rid, "denied", approver_email)
                    st.warning("Request denied.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
