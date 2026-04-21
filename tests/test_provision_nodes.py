"""
Tests for provisioning graph nodes:
  - provision_map_node
  - provision_eligibility_node
  - provision_request_node
  - access_request_status_node
  - _resolve_target_systems helper
"""
import pytest
from unittest.mock import MagicMock, patch


# ---------------------------------------------------------------------------
# provision_map_node
# ---------------------------------------------------------------------------

class TestProvisionMapNode:
    def _state(self, message="I need gitea access", systems=None):
        return {
            "employee_email": "alice@example.com",
            "message": message,
            "entities": {"systems": systems} if systems else {"systems": []},
            "matched_packages": None,
        }

    @patch("graph.nodes.provision_map.list_access_packages")
    def test_gitea_keyword_in_message(self, _mock_list):
        from graph.nodes.provision_map import provision_map_node
        state = self._state(message="I need gitea access")
        result = provision_map_node(state)
        assert "PKG-GH-ENG-STD" in result["matched_packages"]

    @patch("graph.nodes.provision_map.list_access_packages")
    def test_github_keyword_in_message(self, _mock_list):
        from graph.nodes.provision_map import provision_map_node
        state = self._state(message="Please give me github access")
        result = provision_map_node(state)
        assert "PKG-GH-ENG-STD" in result["matched_packages"]

    @patch("graph.nodes.provision_map.list_access_packages")
    def test_mattermost_keyword_in_message(self, _mock_list):
        from graph.nodes.provision_map import provision_map_node
        state = self._state(message="I need mattermost")
        result = provision_map_node(state)
        assert "PKG-SL-ENG-STD" in result["matched_packages"]

    @patch("graph.nodes.provision_map.list_access_packages")
    def test_slack_keyword_in_message(self, _mock_list):
        from graph.nodes.provision_map import provision_map_node
        state = self._state(message="set me up on slack")
        result = provision_map_node(state)
        assert "PKG-SL-ENG-STD" in result["matched_packages"]

    @patch("graph.nodes.provision_map.list_access_packages")
    def test_system_in_entities(self, _mock_list):
        from graph.nodes.provision_map import provision_map_node
        state = self._state(message="I need access", systems=["gitea"])
        result = provision_map_node(state)
        assert "PKG-GH-ENG-STD" in result["matched_packages"]

    @patch("graph.nodes.provision_map.list_access_packages")
    def test_no_match_falls_back_to_db(self, mock_list):
        mock_list.return_value = [
            {"package_id": "PKG-ALL-001"},
            {"package_id": "PKG-ALL-002"},
        ]
        from graph.nodes.provision_map import provision_map_node
        state = self._state(message="I need some access for a custom tool")
        result = provision_map_node(state)
        assert result["matched_packages"] == ["PKG-ALL-001", "PKG-ALL-002"]
        mock_list.assert_called_once()

    @patch("graph.nodes.provision_map.list_access_packages")
    def test_db_failure_returns_empty_list(self, mock_list):
        mock_list.side_effect = RuntimeError("DB error")
        from graph.nodes.provision_map import provision_map_node
        state = self._state(message="I need some custom tool access")
        result = provision_map_node(state)
        assert result["matched_packages"] == []

    @patch("graph.nodes.provision_map.list_access_packages")
    def test_multiple_systems_matched(self, _mock_list):
        from graph.nodes.provision_map import provision_map_node
        state = self._state(message="I need both gitea and mattermost")
        result = provision_map_node(state)
        assert "PKG-GH-ENG-STD" in result["matched_packages"]
        assert "PKG-SL-ENG-STD" in result["matched_packages"]


# ---------------------------------------------------------------------------
# provision_eligibility_node
# ---------------------------------------------------------------------------

class TestProvisionEligibilityNode:
    def _state(self, profile, packages=None):
        return {
            "employee_email": profile.get("email", "test@example.com"),
            "employee_profile": profile,
            "matched_packages": packages or ["PKG-GH-ENG-STD"],
            "eligible": None,
            "eligibility_reason": None,
        }

    def test_active_engineering_employee_eligible(self, active_employee):
        from graph.nodes.provision_eligibility import provision_eligibility_node
        state = self._state(active_employee)
        result = provision_eligibility_node(state)
        assert result["eligible"] is True

    def test_inactive_employee_ineligible(self, inactive_employee):
        from graph.nodes.provision_eligibility import provision_eligibility_node
        state = self._state(inactive_employee)
        result = provision_eligibility_node(state)
        assert result["eligible"] is False
        assert "active" in result["eligibility_reason"].lower()

    def test_no_manager_ineligible(self, employee_no_manager):
        from graph.nodes.provision_eligibility import provision_eligibility_node
        state = self._state(employee_no_manager)
        result = provision_eligibility_node(state)
        assert result["eligible"] is False
        assert "manager" in result["eligibility_reason"].lower()

    def test_contractor_ineligible_for_gitea(self, contractor_employee):
        from graph.nodes.provision_eligibility import provision_eligibility_node
        state = self._state(contractor_employee, packages=["PKG-GH-ENG-STD"])
        result = provision_eligibility_node(state)
        assert result["eligible"] is False
        assert "contractor" in result["eligibility_reason"].lower()

    def test_finance_employee_ineligible_for_gitea(self, finance_employee):
        from graph.nodes.provision_eligibility import provision_eligibility_node
        state = self._state(finance_employee, packages=["PKG-GH-ENG-STD"])
        result = provision_eligibility_node(state)
        assert result["eligible"] is False
        assert "Engineering" in result["eligibility_reason"]

    def test_finance_employee_eligible_for_mattermost(self, finance_employee):
        from graph.nodes.provision_eligibility import provision_eligibility_node
        state = self._state(finance_employee, packages=["PKG-SL-ENG-STD"])
        result = provision_eligibility_node(state)
        assert result["eligible"] is True

    def test_contractor_eligible_for_mattermost(self, contractor_employee):
        from graph.nodes.provision_eligibility import provision_eligibility_node
        state = self._state(contractor_employee, packages=["PKG-SL-ENG-STD"])
        result = provision_eligibility_node(state)
        assert result["eligible"] is True

    @patch("graph.nodes.provision_eligibility.get_employee_profile")
    def test_no_profile_in_state_fetches_from_db(self, mock_get, active_employee):
        mock_get.return_value = active_employee
        from graph.nodes.provision_eligibility import provision_eligibility_node
        state = self._state(active_employee)
        state["employee_profile"] = None
        result = provision_eligibility_node(state)
        mock_get.assert_called_once_with(active_employee["email"])
        assert result["eligible"] is True

    @patch("graph.nodes.provision_eligibility.get_employee_profile")
    def test_profile_not_found_ineligible(self, mock_get):
        mock_get.return_value = None
        from graph.nodes.provision_eligibility import provision_eligibility_node
        state = {
            "employee_email": "ghost@example.com",
            "employee_profile": None,
            "matched_packages": ["PKG-GH-ENG-STD"],
            "eligible": None,
            "eligibility_reason": None,
        }
        result = provision_eligibility_node(state)
        assert result["eligible"] is False

    @patch("graph.nodes.provision_eligibility.get_employee_profile")
    def test_db_error_sets_ineligible(self, mock_get):
        mock_get.side_effect = RuntimeError("DB down")
        from graph.nodes.provision_eligibility import provision_eligibility_node
        state = {
            "employee_email": "alice@example.com",
            "employee_profile": None,
            "matched_packages": ["PKG-GH-ENG-STD"],
            "eligible": None,
            "eligibility_reason": None,
        }
        result = provision_eligibility_node(state)
        assert result["eligible"] is False


# ---------------------------------------------------------------------------
# provision_request_node
# ---------------------------------------------------------------------------

class TestProvisionRequestNode:
    def _state(self, packages=None, profile=None):
        return {
            "employee_email": "alice@example.com",
            "employee_id": "EMP-001",
            "employee_profile": profile,
            "matched_packages": packages or ["PKG-GH-ENG-STD"],
            "request_id": None,
            "approval_status": None,
            "status": "complete",
            "response": None,
        }

    @patch("graph.nodes.provision_request.create_access_request")
    @patch("graph.nodes.provision_request.get_employee_profile")
    def test_creates_request(self, mock_get_profile, mock_create, active_employee):
        mock_get_profile.return_value = active_employee
        mock_create.return_value = {"request_id": "AR-001"}
        from graph.nodes.provision_request import provision_request_node
        state = self._state()
        result = provision_request_node(state)
        assert result["request_id"] == "AR-001"
        assert result["approval_status"] == "pending_approval"
        assert result["status"] == "pending_approval"

    @patch("graph.nodes.provision_request.create_access_request")
    def test_uses_profile_from_state(self, mock_create, active_employee):
        mock_create.return_value = {"request_id": "AR-002"}
        from graph.nodes.provision_request import provision_request_node
        state = self._state(profile=active_employee)
        provision_request_node(state)
        _, kwargs = mock_create.call_args
        assert kwargs["approver_id"] == active_employee["manager_id"]

    @patch("graph.nodes.provision_request.create_access_request")
    @patch("graph.nodes.provision_request.get_employee_profile")
    def test_failed_create_stores_error_id(self, mock_get_profile, mock_create, active_employee):
        mock_get_profile.return_value = active_employee
        mock_create.side_effect = RuntimeError("DB error")
        from graph.nodes.provision_request import provision_request_node
        state = self._state()
        result = provision_request_node(state)
        assert result["request_id"].startswith("ERROR:")


# ---------------------------------------------------------------------------
# _resolve_target_systems helper
# ---------------------------------------------------------------------------

class TestResolveTargetSystems:
    def setup_method(self):
        from graph.nodes.access_request_status import _resolve_target_systems
        self.resolve = _resolve_target_systems

    def test_github_in_message_maps_to_gitea(self):
        result = self.resolve({}, "what is my github access status")
        assert "gitea" in result

    def test_slack_in_message_maps_to_mattermost(self):
        result = self.resolve({}, "check my slack request")
        assert "mattermost" in result

    def test_entities_systems_mapped(self):
        result = self.resolve({"systems": ["gitea"]}, "")
        assert "gitea" in result

    def test_no_match_returns_none(self):
        result = self.resolve({}, "what are my requests")
        assert result is None

    def test_both_systems_detected(self):
        result = self.resolve({}, "I need gitea and mattermost")
        assert "gitea" in result
        assert "mattermost" in result

    def test_case_insensitive_entity_matching(self):
        result = self.resolve({"systems": ["GitHub"]}, "")
        assert "gitea" in result


# ---------------------------------------------------------------------------
# access_request_status_node
# ---------------------------------------------------------------------------

class TestAccessRequestStatusNode:
    def _state(self, employee_id="EMP-001", message="what is my gitea access status", entities=None):
        return {
            "employee_email": "alice@example.com",
            "employee_id": employee_id,
            "message": message,
            "entities": entities or {},
            "access_requests_data": None,
            "response": None,
        }

    @patch("graph.nodes.access_request_status.get_access_requests_by_employee")
    def test_fetches_requests(self, mock_get, pending_access_request):
        mock_get.return_value = [pending_access_request]
        from graph.nodes.access_request_status import access_request_status_node
        state = self._state()
        result = access_request_status_node(state)
        assert len(result["access_requests_data"]) == 1

    @patch("graph.nodes.access_request_status.get_access_requests_by_employee")
    def test_no_employee_id_sets_error(self, mock_get):
        from graph.nodes.access_request_status import access_request_status_node
        state = self._state(employee_id=None)
        result = access_request_status_node(state)
        assert result["access_requests_data"] is None
        assert result["response"] is not None
        mock_get.assert_not_called()

    @patch("graph.nodes.access_request_status.get_access_requests_by_employee")
    def test_passes_target_systems_filter(self, mock_get):
        mock_get.return_value = []
        from graph.nodes.access_request_status import access_request_status_node
        state = self._state(message="what is my gitea status")
        access_request_status_node(state)
        _, kwargs = mock_get.call_args
        assert "gitea" in kwargs["target_systems"]
