"""
Tests for MCP client classes: NocoDBMCPClient, GiteaMCPClient, MattermostMCPClient.
All HTTP calls are patched via requests.Session.
"""
import pytest
from unittest.mock import MagicMock, patch, call
import requests


# ---------------------------------------------------------------------------
# NocoDBMCPClient
# ---------------------------------------------------------------------------

class TestNocoDBMCPClient:
    def _client(self):
        from mcp.nocodb_client import NocoDBMCPClient
        client = NocoDBMCPClient("http://nocodb.local", "test-token", "base-123")
        return client

    def _mock_response(self, data, status=200):
        resp = MagicMock()
        resp.status_code = status
        resp.ok = status < 400
        resp.json.return_value = data
        resp.raise_for_status = MagicMock()
        if status >= 400:
            resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
        return resp

    def _mock_table_query(self, client, table_name, rows):
        client.session.get = MagicMock(side_effect=[
            self._mock_response({"list": [{"title": table_name, "id": f"tbl-{table_name}"}]}),
            self._mock_response({"list": rows}),
        ])

    def test_get_employee_profile_found(self):
        client = self._client()
        employee = {"employee_id": "EMP-001", "email": "alice@example.com"}
        self._mock_table_query(client, "employees", [employee])
        result = client.get_employee_profile("alice@example.com")
        assert result == employee

    def test_get_employee_profile_not_found(self):
        client = self._client()
        self._mock_table_query(client, "employees", [])
        result = client.get_employee_profile("ghost@example.com")
        assert result is None

    def test_get_leave_balance_returns_list(self):
        client = self._client()
        balances = [{"leave_type": "annual", "balance_hours": 80.0}]
        self._mock_table_query(client, "leave_balances", balances)
        result = client.get_leave_balance("EMP-001")
        assert result == balances

    def test_get_leave_balance_filtered_by_type(self):
        client = self._client()
        self._mock_table_query(client, "leave_balances", [])
        client.get_leave_balance("EMP-001", "sick")
        call_kwargs = client.session.get.call_args
        params = call_kwargs[1].get("params", {})
        assert "sick" in str(params)

    def test_list_access_packages(self):
        client = self._client()
        pkgs = [{"package_id": "PKG-GH-ENG-STD"}, {"package_id": "PKG-SL-ENG-STD"}]
        self._mock_table_query(client, "access_packages", pkgs)
        result = client.list_access_packages()
        assert len(result) == 2

    def test_get_access_package_not_found(self):
        client = self._client()
        self._mock_table_query(client, "access_packages", [])
        result = client.get_access_package("PKG-NONEXISTENT")
        assert result is None

    def test_approve_or_deny_raises_if_not_found(self):
        client = self._client()
        client.get_access_request = MagicMock(return_value=None)
        with pytest.raises(ValueError, match="not found"):
            client.approve_or_deny_request("AR-MISSING", "approved", "manager@example.com")

    def test_list_access_requests_with_status(self):
        client = self._client()
        reqs = [{"request_id": "AR-001", "status": "pending_approval"}]
        self._mock_table_query(client, "access_requests", reqs)
        result = client.list_access_requests(status="pending_approval")
        assert result[0]["request_id"] == "AR-001"


# ---------------------------------------------------------------------------
# GiteaMCPClient
# ---------------------------------------------------------------------------

class TestGiteaMCPClient:
    def _client(self):
        from mcp.gitea_client import GiteaMCPClient
        return GiteaMCPClient("http://gitea.local", "admin-token")

    def _mock_response(self, data, status=200):
        resp = MagicMock()
        resp.status_code = status
        resp.ok = status < 400
        resp.json.return_value = data
        resp.content = b"{}" if data else b""
        resp.raise_for_status = MagicMock()
        if status >= 400:
            error = requests.HTTPError(response=resp)
            resp.raise_for_status.side_effect = error
        return resp

    def test_create_user_if_missing_returns_existing(self):
        client = self._client()
        existing = {"id": 1, "login": "alice_smith"}
        client.session.request = MagicMock(return_value=self._mock_response(existing))
        result = client.create_user_if_missing("alice_smith", "alice@example.com")
        assert result == existing

    def test_create_user_if_missing_creates_new(self):
        client = self._client()
        not_found = self._mock_response({}, 404)
        new_user = {"id": 2, "login": "new_user"}
        new_user_resp = self._mock_response(new_user)
        client.session.request = MagicMock(side_effect=[not_found, new_user_resp])
        result = client.create_user_if_missing("new_user", "new@example.com", "New User")
        assert result == new_user

    def test_get_or_create_team_returns_existing(self):
        client = self._client()
        teams = [{"id": 10, "name": "engineering"}]
        client.session.request = MagicMock(return_value=self._mock_response(teams))
        result = client.get_or_create_team("agentic-hr", "engineering")
        assert result["id"] == 10
        assert result["name"] == "engineering"

    def test_get_or_create_team_creates_new(self):
        client = self._client()
        existing_teams = [{"id": 10, "name": "other-team"}]
        new_team = {"id": 11, "name": "engineering"}
        client.session.request = MagicMock(side_effect=[
            self._mock_response(existing_teams),
            self._mock_response(new_team),
        ])
        result = client.get_or_create_team("agentic-hr", "engineering")
        assert result["id"] == 11

    def test_is_user_in_team_true(self):
        client = self._client()
        client.session.request = MagicMock(return_value=self._mock_response({"login": "alice"}))
        assert client.is_user_in_team(10, "alice") is True

    def test_is_user_in_team_false(self):
        client = self._client()
        not_found = self._mock_response({}, 404)
        client.session.request = MagicMock(return_value=not_found)
        assert client.is_user_in_team(10, "ghost") is False

    def test_provision_skips_empty_username(self):
        client = self._client()
        result = client.provision("agentic-hr", "engineering", "", "alice@example.com")
        assert "error" in result

    def test_verify_access_returns_false_on_exception(self):
        client = self._client()
        client.session.request = MagicMock(side_effect=Exception("Network error"))
        assert client.verify_access("agentic-hr", "engineering", "alice") is False


# ---------------------------------------------------------------------------
# MattermostMCPClient
# ---------------------------------------------------------------------------

class TestMattermostMCPClient:
    def _client(self):
        from mcp.mattermost_client import MattermostMCPClient
        return MattermostMCPClient("http://mm.local", "admin-token")

    def _mock_response(self, data, status=200):
        resp = MagicMock()
        resp.status_code = status
        resp.ok = status < 400
        resp.json.return_value = data
        resp.content = b"{}" if data else b""
        resp.text = str(data)
        resp.raise_for_status = MagicMock()
        if status >= 400:
            resp.raise_for_status.side_effect = requests.HTTPError(response=resp)
        return resp

    def test_get_user_by_email_found(self):
        client = self._client()
        user = {"id": "user-1", "email": "alice@example.com"}
        client.session.request = MagicMock(return_value=self._mock_response(user))
        result = client.get_user_by_email("alice@example.com")
        assert result == user

    def test_get_user_by_email_not_found(self):
        client = self._client()
        not_found = self._mock_response({}, 404)
        client.session.request = MagicMock(return_value=not_found)
        result = client.get_user_by_email("ghost@example.com")
        assert result is None

    def test_get_team_by_name_found(self):
        client = self._client()
        team = {"id": "team-1", "name": "engineering"}
        client.session.request = MagicMock(return_value=self._mock_response(team))
        result = client.get_team_by_name("engineering")
        assert result["id"] == "team-1"

    def test_get_team_by_name_not_found(self):
        client = self._client()
        not_found = self._mock_response({}, 404)
        client.session.request = MagicMock(return_value=not_found)
        result = client.get_team_by_name("nonexistent")
        assert result is None

    def test_is_user_in_team_true(self):
        client = self._client()
        client.session.request = MagicMock(return_value=self._mock_response({"user_id": "u1"}))
        assert client.is_user_in_team("team-1", "user-1") is True

    def test_is_user_in_team_false(self):
        client = self._client()
        not_found = self._mock_response({}, 404)
        client.session.request = MagicMock(return_value=not_found)
        assert client.is_user_in_team("team-1", "ghost-user") is False

    def test_verify_access_returns_false_on_exception(self):
        client = self._client()
        client.session.request = MagicMock(side_effect=Exception("Network error"))
        assert client.verify_access("engineering", "alice@example.com") is False

    def test_create_user_uses_random_password(self):
        client = self._client()
        user = {"id": "new-user", "email": "new@example.com"}
        client.session.request = MagicMock(return_value=self._mock_response(user))
        result = client.create_user("new@example.com", "new_user")
        assert result["id"] == "new-user"
        call_json = client.session.request.call_args[1]["json"]
        assert len(call_json["password"]) == 16  # random 16-char password
