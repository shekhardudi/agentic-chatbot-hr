"""
Routing functions for LangGraph conditional edges.
"""
from models.state import AgentState


def route_intent(state: AgentState) -> str:
    """Route from classify_intent to the appropriate worker or clarify."""
    if state.get("needs_clarification"):
        return "clarify"
    intent = state.get("intent", "unsupported")
    if intent == "leave_balance":
        return "leave_balance"
    if intent == "policy_query":
        return "policy_rewrite"
    if intent == "software_provision":
        return "provision_map"
    return "unsupported"


def route_eligibility(state: AgentState) -> str:
    """Route from provision_eligibility: eligible → request, ineligible → compose."""
    if state.get("eligible"):
        return "eligible"
    return "ineligible"
