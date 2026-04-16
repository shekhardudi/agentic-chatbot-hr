"""
compose_response node — formats the final user-facing response.
"""
from datetime import date

from logger import get_logger
from models.state import AgentState
from llm.client import fast_chat
from llm.prompts import COMPOSE_PROMPT

log = get_logger(__name__)


def compose_response_node(state: AgentState) -> AgentState:
    intent = state.get("intent")
    log.info("Composing response | intent=%s | session=%s", intent, state.get("session_id"))

    if state.get("response") and intent not in ("leave_balance",):
        raw = state["response"]
        state["response"] = fast_chat(COMPOSE_PROMPT.format(answer=raw))
        log.debug("Response composed via LLM")
        return state

    # --- Leave balance ---
    if intent == "leave_balance":
        leave_data = state.get("leave_data")
        if not leave_data or not leave_data.get("balances"):
            log.warning("No leave balance data to compose")
            state["response"] = "I couldn't find your leave balance. Please contact HR."
            return state

        balances = leave_data["balances"]
        today = date.today().isoformat()
        lines = [f"Here is your leave balance as of {today}:\n"]
        for b in balances:
            lt = b.get("leave_type", "").replace("_", " ").title()
            bal = b.get("balance_hours", 0)
            accrued = b.get("accrued_ytd_hours", 0)
            used = b.get("used_ytd_hours", 0)
            lines.append(
                f"- **{lt}**: {bal:.1f} hrs available "
                f"(accrued {accrued:.1f} YTD, used {used:.1f} YTD)"
            )
        state["response"] = "\n".join(lines)
        log.debug("Leave balance response composed | %d leave type(s)", len(balances))
        return state

    # --- Provisioning pending ---
    if intent == "software_provision" and state.get("approval_status") == "pending_approval":
        pkgs = state.get("matched_packages") or []
        pkg_str = ", ".join(pkgs) if pkgs else "the requested system(s)"
        state["response"] = (
            f"Your access request for **{pkg_str}** has been submitted "
            f"(Request ID: `{state.get('request_id')}`). "
            "It is now awaiting manager approval. You'll be notified once it's processed."
        )
        log.info("Provisioning response: pending_approval | request_id=%s", state.get("request_id"))
        return state

    # --- Provisioning fulfilled ---
    if intent == "software_provision" and state.get("approval_status") == "fulfilled":
        result = state.get("fulfillment_result") or {}
        parts = []
        if "gitea" in result:
            g = result["gitea"]
            parts.append(f"Gitea: added to **{g.get('org')}/{g.get('team')}** team ✓")
        if "mattermost" in result:
            m = result["mattermost"]
            chs = ", ".join(f"`#{c}`" for c in m.get("channels_joined", []))
            parts.append(f"Mattermost: joined {chs} ✓")
        state["response"] = ("Provisioning complete!\n" + "\n".join(parts)) if parts else "Access provisioning completed."
        log.info("Provisioning response: fulfilled")
        return state

    # --- Ineligible ---
    if intent == "software_provision" and state.get("eligible") is False:
        reason = state.get("eligibility_reason", "You are not eligible for this access.")
        state["response"] = f"Access request denied: {reason}"
        log.info("Provisioning response: ineligible | reason=%r", reason)
        return state

    # --- Unsupported ---
    if intent == "unsupported":
        state["response"] = (
            "I can help with leave balance queries, HR policy questions, "
            "and software access provisioning. "
            "This request falls outside those areas — please contact HR directly."
        )
        log.info("Unsupported intent — fallback response")
        return state

    if not state.get("response"):
        log.warning("No response set — using fallback")
        state["response"] = "I'm sorry, I wasn't able to process your request."

    return state
