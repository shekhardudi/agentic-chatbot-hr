"""
Routing functions for LangGraph conditional edges.
"""
from models.state import AgentState


def route_intent(state: AgentState) -> str:
    """Route from classify_intent to the appropriate worker or clarify."""
    if state.get("needs_clarification"):
        return "clarify"
    intent = state.get("intent", "unsupported")
    if intent in ("leave_balance", "leave_apply", "software_provision", "access_request_status"):
        return "resolve_user"
    if intent == "policy_query":
        return "policy_rewrite"
    return "unsupported"


def route_post_resolve(state: AgentState) -> str:
    """Route from resolve_user to the correct worker based on already-classified intent."""
    intent = state.get("intent", "unsupported")
    if intent == "leave_balance":
        return "leave_balance"
    if intent == "leave_apply":
        return "leave_apply_gather"
    if intent == "software_provision":
        return "provision_map"
    if intent == "access_request_status":
        return "access_request_status"
    return "unsupported"


def route_eligibility(state: AgentState) -> str:
    """Route from provision_eligibility: eligible → request, ineligible → compose."""
    if state.get("eligible"):
        return "eligible"
    return "ineligible"


def route_leave_apply_gather(state: AgentState) -> str:
    """Route after gathering leave details."""
    if state.get("leave_apply_status") == "ready":
        return "calculate"
    return "compose"  # missing_info — ask user


def route_leave_apply_calculate(state: AgentState) -> str:
    """Route after calculating leave hours."""
    if state.get("leave_apply_sufficient"):
        return "update"
    return "compose"  # insufficient balance or no record — tell user
