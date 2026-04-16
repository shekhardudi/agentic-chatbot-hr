"""
LangGraph state machine builder.
Constructs and compiles the full agent graph.
"""
from functools import lru_cache

from langgraph.graph import StateGraph, END

from models.state import AgentState
from graph.edges import route_intent, route_post_resolve, route_eligibility

from graph.nodes.resolve_user import resolve_user
from graph.nodes.classify_intent import classify_intent
from graph.nodes.clarify import clarify
from graph.nodes.leave_balance import leave_balance_node
from graph.nodes.policy_rewrite import policy_rewrite_node
from graph.nodes.policy_retrieve import policy_retrieve_node
from graph.nodes.policy_expand import policy_expand_node
from graph.nodes.policy_grade import policy_grade_node
from graph.nodes.policy_answer import policy_answer_node
from graph.nodes.provision_map import provision_map_node
from graph.nodes.provision_eligibility import provision_eligibility_node
from graph.nodes.provision_request import provision_request_node
from graph.nodes.provision_fulfill import provision_fulfill_node
from graph.nodes.provision_verify import provision_verify_node
from graph.nodes.compose_response import compose_response_node
from graph.nodes.audit import audit_node


def _build_graph():
    g = StateGraph(AgentState)

    # Register all nodes
    g.add_node("resolve_user", resolve_user)
    g.add_node("classify_intent", classify_intent)
    g.add_node("clarify", clarify)
    g.add_node("leave_balance", leave_balance_node)
    g.add_node("policy_rewrite", policy_rewrite_node)
    g.add_node("policy_retrieve", policy_retrieve_node)
    g.add_node("policy_expand", policy_expand_node)
    g.add_node("policy_grade", policy_grade_node)
    g.add_node("policy_answer", policy_answer_node)
    g.add_node("provision_map", provision_map_node)
    g.add_node("provision_eligibility", provision_eligibility_node)
    g.add_node("provision_request", provision_request_node)
    g.add_node("provision_fulfill", provision_fulfill_node)
    g.add_node("provision_verify", provision_verify_node)
    g.add_node("compose_response", compose_response_node)
    g.add_node("audit", audit_node)

    # Entry point — classify first, resolve_user only for paths that need employee_id
    g.set_entry_point("classify_intent")

    # Intent routing
    g.add_conditional_edges(
        "classify_intent",
        route_intent,
        {
            "clarify": "clarify",
            "leave_balance": "resolve_user",
            "policy_rewrite": "policy_rewrite",
            "provision_map": "resolve_user",
            "unsupported": "compose_response",
        },
    )

    # resolve_user → dispatch to the correct worker
    g.add_conditional_edges(
        "resolve_user",
        route_post_resolve,
        {
            "leave_balance": "leave_balance",
            "provision_map": "provision_map",
            "unsupported": "compose_response",
        },
    )

    # Clarify → done
    g.add_edge("clarify", "compose_response")

    # HR worker
    g.add_edge("leave_balance", "compose_response")

    # Policy RAG pipeline
    g.add_edge("policy_rewrite", "policy_retrieve")
    g.add_edge("policy_retrieve", "policy_expand")
    g.add_edge("policy_expand", "policy_grade")
    g.add_edge("policy_grade", "policy_answer")
    g.add_edge("policy_answer", "compose_response")

    # Provisioning pipeline
    g.add_edge("provision_map", "provision_eligibility")
    g.add_conditional_edges(
        "provision_eligibility",
        route_eligibility,
        {
            "eligible": "provision_request",
            "ineligible": "compose_response",
        },
    )
    # provision_request → compose_response (fulfillment is triggered externally after approval)
    g.add_edge("provision_request", "compose_response")

    # Fulfillment path (triggered by approval API, not the main chat flow)
    g.add_edge("provision_fulfill", "provision_verify")
    g.add_edge("provision_verify", "compose_response")

    # All paths converge here
    g.add_edge("compose_response", "audit")
    g.add_edge("audit", END)

    return g.compile()


@lru_cache(maxsize=1)
def get_compiled_graph():
    return _build_graph()
