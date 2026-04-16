import streamlit as st
from api_client import submit_decision


def approval_card(request: dict, approver_email: str) -> None:
    """Renders one pending access request with Approve / Deny buttons."""
    with st.container(border=True):
        st.markdown(
            f"**{request.get('requester_email', 'Unknown')}** "
            f"requests `{', '.join(request.get('packages', []))}`"
        )
        st.caption(f"Request ID: `{request['request_id']}` · Created: {request.get('created_ts', '')}")

        col1, col2 = st.columns(2)
        with col1:
            if st.button("Approve", key=f"approve_{request['request_id']}", type="primary"):
                try:
                    submit_decision(request["request_id"], "approved", approver_email)
                    st.success("Approved — provisioning triggered.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
        with col2:
            if st.button("Deny", key=f"deny_{request['request_id']}"):
                try:
                    submit_decision(request["request_id"], "denied", approver_email)
                    st.warning("Request denied.")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {e}")
