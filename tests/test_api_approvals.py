"""
Tests for GET /approvals and POST /approvals/{request_id} endpoints.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from fastapi.testclient import TestClient


def _make_app():
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
    from fastapi import FastAPI
    from api.approvals import router
    app = FastAPI()
    app.include_router(router)
    return app


class TestListApprovalsEndpoint:
    def setup_method(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

    @patch("api.approvals.list_access_requests")
    def test_returns_pending_requests(self, mock_list, pending_access_request):
        mock_list.return_value = [pending_access_request]

        app = _make_app()
        with TestClient(app) as client:
            resp = client.get("/approvals")

        assert resp.status_code == 200
        body = resp.json()
        assert len(body) == 1
        assert body[0]["request_id"] == "AR-20240101120000"
        assert body[0]["requester_email"] == "alice@example.com"
        mock_list.assert_called_once_with(status="pending_approval")

    @patch("api.approvals.list_access_requests")
    def test_returns_empty_list(self, mock_list):
        mock_list.return_value = []
        app = _make_app()
        with TestClient(app) as client:
            resp = client.get("/approvals")
        assert resp.status_code == 200
        assert resp.json() == []

    @patch("api.approvals.list_access_requests")
    def test_db_error_returns_502(self, mock_list):
        mock_list.side_effect = RuntimeError("DB connection lost")
        app = _make_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.get("/approvals")
        assert resp.status_code == 502

    @patch("api.approvals.list_access_requests")
    def test_missing_package_id_handled(self, mock_list):
        request = {
            "request_id": "AR-001",
            "requester_email": "alice@example.com",
            "requester_name": "Alice",
            "package_id": None,
            "status": "pending_approval",
            "created_ts": "2024-01-01T12:00:00+00:00",
        }
        mock_list.return_value = [request]
        app = _make_app()
        with TestClient(app) as client:
            resp = client.get("/approvals")
        assert resp.status_code == 200
        body = resp.json()
        assert body[0]["packages"] == []


class TestDecideApprovalEndpoint:
    def setup_method(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

    @patch("api.approvals.run_fulfillment")
    @patch("api.approvals.approve_or_deny_request")
    def test_approve_triggers_fulfillment(self, mock_update, mock_fulfill):
        mock_update.return_value = {"request_id": "AR-001", "status": "approved"}
        mock_fulfill_coro = AsyncMock(return_value={"system": "gitea"})
        mock_fulfill.return_value = mock_fulfill_coro()

        app = _make_app()
        with TestClient(app) as client:
            resp = client.post("/approvals/AR-001", json={
                "decision": "approved",
                "approver_email": "manager@example.com",
            })

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "approved"
        mock_update.assert_called_once_with("AR-001", "approved", "manager@example.com")

    @patch("api.approvals.run_fulfillment")
    @patch("api.approvals.approve_or_deny_request")
    def test_deny_skips_fulfillment(self, mock_update, mock_fulfill):
        mock_update.return_value = {"request_id": "AR-001", "status": "denied"}
        app = _make_app()
        with TestClient(app) as client:
            resp = client.post("/approvals/AR-001", json={
                "decision": "denied",
                "approver_email": "manager@example.com",
            })

        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "denied"
        mock_fulfill.assert_not_called()

    @patch("api.approvals.approve_or_deny_request")
    def test_invalid_decision_returns_400(self, mock_update):
        app = _make_app()
        with TestClient(app) as client:
            resp = client.post("/approvals/AR-001", json={
                "decision": "maybe",
                "approver_email": "manager@example.com",
            })
        assert resp.status_code == 400

    @patch("api.approvals.approve_or_deny_request")
    def test_db_error_returns_502(self, mock_update):
        mock_update.side_effect = RuntimeError("DB error")
        app = _make_app()
        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post("/approvals/AR-001", json={
                "decision": "approved",
                "approver_email": "manager@example.com",
            })
        assert resp.status_code == 502

    @patch("api.approvals.run_fulfillment")
    @patch("api.approvals.approve_or_deny_request")
    def test_fulfillment_error_returns_approved_with_error(self, mock_update, mock_fulfill):
        mock_update.return_value = {"request_id": "AR-001", "status": "approved"}
        mock_fulfill.side_effect = Exception("Gitea unreachable")

        app = _make_app()
        with TestClient(app) as client:
            resp = client.post("/approvals/AR-001", json={
                "decision": "approved",
                "approver_email": "manager@example.com",
            })

        # Fulfillment error should not fail the whole request
        assert resp.status_code == 200
        body = resp.json()
        assert body["status"] == "approved"
        assert "fulfillment_error" in body

    def test_missing_decision_field_returns_422(self):
        app = _make_app()
        with TestClient(app) as client:
            resp = client.post("/approvals/AR-001", json={
                "approver_email": "manager@example.com",
            })
        assert resp.status_code == 422

    def test_missing_approver_email_returns_422(self):
        app = _make_app()
        with TestClient(app) as client:
            resp = client.post("/approvals/AR-001", json={
                "decision": "approved",
            })
        assert resp.status_code == 422
