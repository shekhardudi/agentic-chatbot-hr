"""
Tests for graph/edges.py — all five routing functions.
These are pure Python functions with no I/O, so no mocking needed.
"""
import pytest


# ---------------------------------------------------------------------------
# Helpers — build minimal state dicts
# ---------------------------------------------------------------------------

def _state(**kwargs):
    defaults = {
        "intent": None,
        "needs_clarification": False,
        "eligible": None,
        "leave_apply_status": None,
        "leave_apply_sufficient": None,
    }
    defaults.update(kwargs)
    return defaults


# ---------------------------------------------------------------------------
# route_intent
# ---------------------------------------------------------------------------

class TestRouteIntent:
    def setup_method(self):
        from graph.edges import route_intent
        self.route = route_intent

    def test_needs_clarification_returns_clarify(self):
        state = _state(needs_clarification=True, intent="unsupported")
        assert self.route(state) == "clarify"

    def test_clarification_overrides_valid_intent(self):
        state = _state(needs_clarification=True, intent="leave_balance")
        assert self.route(state) == "clarify"

    def test_leave_balance_routes_to_resolve_user(self):
        state = _state(intent="leave_balance")
        assert self.route(state) == "resolve_user"

    def test_leave_apply_routes_to_resolve_user(self):
        state = _state(intent="leave_apply")
        assert self.route(state) == "resolve_user"

    def test_software_provision_routes_to_resolve_user(self):
        state = _state(intent="software_provision")
        assert self.route(state) == "resolve_user"

    def test_access_request_status_routes_to_resolve_user(self):
        state = _state(intent="access_request_status")
        assert self.route(state) == "resolve_user"

    def test_policy_query_routes_to_policy_rewrite(self):
        state = _state(intent="policy_query")
        assert self.route(state) == "policy_rewrite"

    def test_unsupported_intent_routes_to_unsupported(self):
        state = _state(intent="unsupported")
        assert self.route(state) == "unsupported"

    def test_unknown_intent_routes_to_unsupported(self):
        state = _state(intent="random_gibberish")
        assert self.route(state) == "unsupported"

    def test_none_intent_routes_to_unsupported(self):
        state = _state(intent=None)
        assert self.route(state) == "unsupported"


# ---------------------------------------------------------------------------
# route_post_resolve
# ---------------------------------------------------------------------------

class TestRoutePostResolve:
    def setup_method(self):
        from graph.edges import route_post_resolve
        self.route = route_post_resolve

    def test_leave_balance(self):
        assert self.route(_state(intent="leave_balance")) == "leave_balance"

    def test_leave_apply(self):
        assert self.route(_state(intent="leave_apply")) == "leave_apply_gather"

    def test_software_provision(self):
        assert self.route(_state(intent="software_provision")) == "provision_map"

    def test_access_request_status(self):
        assert self.route(_state(intent="access_request_status")) == "access_request_status"

    def test_unknown_intent_falls_back_to_unsupported(self):
        assert self.route(_state(intent="unknown")) == "unsupported"

    def test_none_intent_falls_back_to_unsupported(self):
        assert self.route(_state(intent=None)) == "unsupported"


# ---------------------------------------------------------------------------
# route_eligibility
# ---------------------------------------------------------------------------

class TestRouteEligibility:
    def setup_method(self):
        from graph.edges import route_eligibility
        self.route = route_eligibility

    def test_eligible_true_routes_to_eligible(self):
        assert self.route(_state(eligible=True)) == "eligible"

    def test_eligible_false_routes_to_ineligible(self):
        assert self.route(_state(eligible=False)) == "ineligible"

    def test_eligible_none_routes_to_ineligible(self):
        assert self.route(_state(eligible=None)) == "ineligible"


# ---------------------------------------------------------------------------
# route_leave_apply_gather
# ---------------------------------------------------------------------------

class TestRouteLeaveApplyGather:
    def setup_method(self):
        from graph.edges import route_leave_apply_gather
        self.route = route_leave_apply_gather

    def test_ready_routes_to_calculate(self):
        assert self.route(_state(leave_apply_status="ready")) == "calculate"

    def test_missing_info_routes_to_compose(self):
        assert self.route(_state(leave_apply_status="missing_info")) == "compose"

    def test_none_status_routes_to_compose(self):
        assert self.route(_state(leave_apply_status=None)) == "compose"

    def test_unknown_status_routes_to_compose(self):
        assert self.route(_state(leave_apply_status="other")) == "compose"


# ---------------------------------------------------------------------------
# route_leave_apply_calculate
# ---------------------------------------------------------------------------

class TestRouteLeaveApplyCalculate:
    def setup_method(self):
        from graph.edges import route_leave_apply_calculate
        self.route = route_leave_apply_calculate

    def test_sufficient_true_routes_to_update(self):
        assert self.route(_state(leave_apply_sufficient=True)) == "update"

    def test_sufficient_false_routes_to_compose(self):
        assert self.route(_state(leave_apply_sufficient=False)) == "compose"

    def test_sufficient_none_routes_to_compose(self):
        assert self.route(_state(leave_apply_sufficient=None)) == "compose"
