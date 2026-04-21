"""
Tests for db/hr.py — HR database access functions.
All tests mock ManagedConn to avoid requiring a live database.
"""
import pytest
from unittest.mock import MagicMock, patch, call
from datetime import datetime, timezone


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _make_cursor(rows, columns):
    """Build a mock cursor that returns the given rows and column names."""
    cur = MagicMock()
    cur.fetchall.return_value = rows
    cur.fetchone.return_value = rows[0] if rows else None
    cur.description = [(c,) for c in columns]
    cur.__enter__ = lambda s: s
    cur.__exit__ = MagicMock(return_value=False)
    return cur


def _make_conn(cursor):
    conn = MagicMock()
    conn.cursor.return_value = cursor
    conn.__enter__ = lambda s: conn
    conn.__exit__ = MagicMock(return_value=False)
    return conn


# ---------------------------------------------------------------------------
# _rows_to_dicts / _row_to_dict helpers
# ---------------------------------------------------------------------------

class TestRowHelpers:
    def test_rows_to_dicts(self):
        from db.hr import _rows_to_dicts
        cur = _make_cursor(
            [("EMP-001", "alice@example.com"), ("EMP-002", "bob@example.com")],
            ["employee_id", "email"],
        )
        result = _rows_to_dicts(cur)
        assert result == [
            {"employee_id": "EMP-001", "email": "alice@example.com"},
            {"employee_id": "EMP-002", "email": "bob@example.com"},
        ]

    def test_rows_to_dicts_empty(self):
        from db.hr import _rows_to_dicts
        cur = _make_cursor([], ["employee_id", "email"])
        result = _rows_to_dicts(cur)
        assert result == []

    def test_row_to_dict_returns_first_row(self):
        from db.hr import _row_to_dict
        cur = _make_cursor([("EMP-001", "alice@example.com")], ["employee_id", "email"])
        result = _row_to_dict(cur)
        assert result == {"employee_id": "EMP-001", "email": "alice@example.com"}

    def test_row_to_dict_returns_none_on_empty(self):
        from db.hr import _row_to_dict
        cur = _make_cursor([], ["employee_id", "email"])
        cur.fetchone.return_value = None
        result = _row_to_dict(cur)
        assert result is None


# ---------------------------------------------------------------------------
# get_employee_profile
# ---------------------------------------------------------------------------

class TestGetEmployeeProfile:
    @patch("db.hr.ManagedConn")
    def test_returns_employee_dict(self, mock_managed_conn, active_employee):
        row = tuple(active_employee.values())
        cols = list(active_employee.keys())
        cur = _make_cursor([row], cols)
        conn = _make_conn(cur)
        mock_managed_conn.return_value.__enter__ = lambda s: conn
        mock_managed_conn.return_value.__exit__ = MagicMock(return_value=False)

        from db.hr import get_employee_profile
        result = get_employee_profile("alice@example.com")
        assert result["employee_id"] == "EMP-001"
        assert result["email"] == "alice@example.com"

    @patch("db.hr.ManagedConn")
    def test_returns_none_when_not_found(self, mock_managed_conn):
        cur = _make_cursor([], ["employee_id", "email"])
        cur.fetchone.return_value = None
        conn = _make_conn(cur)
        mock_managed_conn.return_value.__enter__ = lambda s: conn
        mock_managed_conn.return_value.__exit__ = MagicMock(return_value=False)

        from db.hr import get_employee_profile
        result = get_employee_profile("unknown@example.com")
        assert result is None


# ---------------------------------------------------------------------------
# list_access_packages
# ---------------------------------------------------------------------------

class TestListAccessPackages:
    @patch("db.hr.ManagedConn")
    def test_returns_all_packages(self, mock_managed_conn):
        rows = [("PKG-GH-ENG-STD", "Gitea", "gitea", "{}"), ("PKG-SL-ENG-STD", "MM", "mattermost", "{}")]
        cols = ["package_id", "package_name", "target_system", "payload"]
        cur = _make_cursor(rows, cols)
        conn = _make_conn(cur)
        mock_managed_conn.return_value.__enter__ = lambda s: conn
        mock_managed_conn.return_value.__exit__ = MagicMock(return_value=False)

        from db.hr import list_access_packages
        result = list_access_packages()
        assert len(result) == 2
        assert result[0]["package_id"] == "PKG-GH-ENG-STD"

    @patch("db.hr.ManagedConn")
    def test_returns_empty_list(self, mock_managed_conn):
        cur = _make_cursor([], ["package_id"])
        conn = _make_conn(cur)
        mock_managed_conn.return_value.__enter__ = lambda s: conn
        mock_managed_conn.return_value.__exit__ = MagicMock(return_value=False)

        from db.hr import list_access_packages
        result = list_access_packages()
        assert result == []


# ---------------------------------------------------------------------------
# create_access_request
# ---------------------------------------------------------------------------

class TestCreateAccessRequest:
    @patch("db.hr.ManagedConn")
    def test_creates_and_returns_request(self, mock_managed_conn):
        row = ("AR-001", "EMP-001", "PKG-GH-ENG-STD", "EMP-100", "pending_approval", datetime.now(timezone.utc))
        cols = ["request_id", "requester_id", "package_id", "approver_id", "status", "created_ts"]
        cur = _make_cursor([row], cols)
        conn = _make_conn(cur)
        mock_managed_conn.return_value.__enter__ = lambda s: conn
        mock_managed_conn.return_value.__exit__ = MagicMock(return_value=False)

        from db.hr import create_access_request
        result = create_access_request("EMP-001", "alice@example.com", "PKG-GH-ENG-STD", "EMP-100")
        assert result["status"] == "pending_approval"
        conn.commit.assert_called_once()


# ---------------------------------------------------------------------------
# approve_or_deny_request
# ---------------------------------------------------------------------------

class TestApproveOrDenyRequest:
    @patch("db.hr.ManagedConn")
    def test_approve_updates_status(self, mock_managed_conn):
        row = ("AR-001", "approved", datetime.now(timezone.utc))
        cols = ["request_id", "status", "decided_ts"]
        cur = _make_cursor([row], cols)
        conn = _make_conn(cur)
        mock_managed_conn.return_value.__enter__ = lambda s: conn
        mock_managed_conn.return_value.__exit__ = MagicMock(return_value=False)

        from db.hr import approve_or_deny_request
        result = approve_or_deny_request("AR-001", "approved", "manager@example.com")
        assert result["status"] == "approved"
        conn.commit.assert_called_once()

    @patch("db.hr.ManagedConn")
    def test_raises_if_not_found(self, mock_managed_conn):
        cur = _make_cursor([], ["request_id", "status"])
        cur.fetchone.return_value = None
        conn = _make_conn(cur)
        mock_managed_conn.return_value.__enter__ = lambda s: conn
        mock_managed_conn.return_value.__exit__ = MagicMock(return_value=False)

        from db.hr import approve_or_deny_request
        with pytest.raises(ValueError, match="not found"):
            approve_or_deny_request("AR-MISSING", "approved", "manager@example.com")


# ---------------------------------------------------------------------------
# list_access_requests
# ---------------------------------------------------------------------------

class TestListAccessRequests:
    @patch("db.hr.ManagedConn")
    def test_filters_by_status(self, mock_managed_conn):
        rows = [("AR-001", "pending_approval", "alice@example.com", "Alice")]
        cols = ["request_id", "status", "requester_email", "requester_name"]
        cur = _make_cursor(rows, cols)
        conn = _make_conn(cur)
        mock_managed_conn.return_value.__enter__ = lambda s: conn
        mock_managed_conn.return_value.__exit__ = MagicMock(return_value=False)

        from db.hr import list_access_requests
        result = list_access_requests(status="pending_approval")
        assert result[0]["status"] == "pending_approval"
        # Verify the WHERE clause was applied
        execute_call = cur.execute.call_args
        assert "pending_approval" in str(execute_call)

    @patch("db.hr.ManagedConn")
    def test_no_status_returns_all(self, mock_managed_conn):
        rows = [("AR-001", "fulfilled"), ("AR-002", "pending_approval")]
        cols = ["request_id", "status"]
        cur = _make_cursor(rows, cols)
        conn = _make_conn(cur)
        mock_managed_conn.return_value.__enter__ = lambda s: conn
        mock_managed_conn.return_value.__exit__ = MagicMock(return_value=False)

        from db.hr import list_access_requests
        result = list_access_requests()
        assert len(result) == 2


# ---------------------------------------------------------------------------
# update_request_fulfillment
# ---------------------------------------------------------------------------

class TestUpdateRequestFulfillment:
    @patch("db.hr.ManagedConn")
    def test_updates_to_fulfilled(self, mock_managed_conn):
        row = ("AR-001", "fulfilled", '{"system":"gitea"}')
        cols = ["request_id", "status", "fulfillment_result"]
        cur = _make_cursor([row], cols)
        conn = _make_conn(cur)
        mock_managed_conn.return_value.__enter__ = lambda s: conn
        mock_managed_conn.return_value.__exit__ = MagicMock(return_value=False)

        from db.hr import update_request_fulfillment
        result = update_request_fulfillment("AR-001", {"system": "gitea"})
        assert result["status"] == "fulfilled"
        conn.commit.assert_called_once()

    @patch("db.hr.ManagedConn")
    def test_raises_if_not_found(self, mock_managed_conn):
        cur = _make_cursor([], ["request_id", "status"])
        cur.fetchone.return_value = None
        conn = _make_conn(cur)
        mock_managed_conn.return_value.__enter__ = lambda s: conn
        mock_managed_conn.return_value.__exit__ = MagicMock(return_value=False)

        from db.hr import update_request_fulfillment
        with pytest.raises(ValueError, match="not found"):
            update_request_fulfillment("AR-MISSING", {"system": "gitea"})
