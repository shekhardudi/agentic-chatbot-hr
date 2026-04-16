import streamlit as st


def message_bubble(role: str, content: str, citations: list[dict] | None = None) -> None:
    """Renders a chat message. Citations appear in an expander below the answer."""
    with st.chat_message(role):
        st.markdown(content)
        if citations:
            with st.expander("Sources"):
                for c in citations:
                    doc = c.get("document", "")
                    section = c.get("section", "")
                    st.caption(f"**{doc}** — {section}")


def status_badge(status: str, request_id: str | None = None) -> None:
    """Shows a coloured status badge for provisioning requests."""
    if status == "pending_approval":
        msg = f"Awaiting manager approval"
        if request_id:
            msg += f" (Request `{request_id}`)"
        st.info(msg)
    elif status == "complete":
        pass  # no badge needed
    elif status == "needs_clarification":
        st.warning("Clarification needed")
