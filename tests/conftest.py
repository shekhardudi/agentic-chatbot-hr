"""
Shared pytest fixtures for the agentic_hr backend test suite.
"""
import sys
import os
import pytest

# Ensure the backend package is importable without installing
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))


# ---------------------------------------------------------------------------
# Employee fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def active_employee():
    """Active Engineering employee with a manager — eligible for all packages."""
    return {
        "employee_id": "EMP-001",
        "email": "alice@example.com",
        "full_name": "Alice Smith",
        "department": "Engineering",
        "employment_type": "full_time",
        "manager_id": "EMP-100",
        "status": "active",
        "github_username": "alice_smith",
    }


@pytest.fixture
def inactive_employee():
    """Inactive employee — ineligible for all access packages."""
    return {
        "employee_id": "EMP-002",
        "email": "bob@example.com",
        "full_name": "Bob Jones",
        "department": "Engineering",
        "employment_type": "full_time",
        "manager_id": "EMP-100",
        "status": "inactive",
        "github_username": "bob_jones",
    }


@pytest.fixture
def contractor_employee():
    """Active contractor — ineligible for Gitea packages."""
    return {
        "employee_id": "EMP-003",
        "email": "carol@example.com",
        "full_name": "Carol White",
        "department": "Engineering",
        "employment_type": "contractor",
        "manager_id": "EMP-100",
        "status": "active",
        "github_username": "carol_white",
    }


@pytest.fixture
def finance_employee():
    """Active Finance employee — ineligible for Gitea (non-Engineering dept)."""
    return {
        "employee_id": "EMP-004",
        "email": "dave@example.com",
        "full_name": "Dave Brown",
        "department": "Finance",
        "employment_type": "full_time",
        "manager_id": "EMP-100",
        "status": "active",
        "github_username": "dave_brown",
    }


@pytest.fixture
def employee_no_manager():
    """Active employee with no manager_id — ineligible for any package."""
    return {
        "employee_id": "EMP-005",
        "email": "eve@example.com",
        "full_name": "Eve Green",
        "department": "Engineering",
        "employment_type": "full_time",
        "manager_id": "",
        "status": "active",
        "github_username": "eve_green",
    }


# ---------------------------------------------------------------------------
# AgentState fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def base_state():
    """Minimal valid AgentState for test initialisation."""
    return {
        "employee_email": "alice@example.com",
        "employee_id": None,
        "employee_profile": None,
        "session_id": "test-session-001",
        "message": "test message",
        "intent": None,
        "entities": {},
        "confidence": None,
        "needs_clarification": False,
        "leave_data": None,
        "leave_apply_type": None,
        "leave_apply_hours": None,
        "leave_apply_duration": None,
        "leave_apply_unit": None,
        "leave_apply_sufficient": None,
        "leave_apply_current_balance": None,
        "leave_apply_new_balance": None,
        "leave_apply_status": None,
        "access_requests_data": None,
        "rewritten_queries": None,
        "retrieved_chunks": None,
        "parent_sections": None,
        "evidence_sufficient": None,
        "topic_verdicts": None,
        "matched_packages": None,
        "eligible": None,
        "eligibility_reason": None,
        "request_id": None,
        "approval_status": None,
        "fulfillment_result": None,
        "response": None,
        "citations": [],
        "status": "complete",
    }


@pytest.fixture
def leave_balance_state(base_state, active_employee):
    """AgentState ready for a leave_balance lookup."""
    state = dict(base_state)
    state.update({
        "message": "How many annual leave days do I have?",
        "intent": "leave_balance",
        "entities": {"leave_type": "annual"},
        "confidence": 0.95,
        "employee_id": active_employee["employee_id"],
        "employee_profile": active_employee,
    })
    return state


@pytest.fixture
def leave_apply_ready_state(base_state, active_employee):
    """AgentState with all leave application details gathered — ready to calculate."""
    state = dict(base_state)
    state.update({
        "message": "I want to take 3 days of annual leave",
        "intent": "leave_apply",
        "entities": {"leave_type": "annual", "leave_duration": 3, "leave_unit": "days"},
        "confidence": 0.92,
        "employee_id": active_employee["employee_id"],
        "employee_profile": active_employee,
        "leave_apply_type": "annual",
        "leave_apply_duration": 3.0,
        "leave_apply_unit": "days",
        "leave_apply_status": "ready",
    })
    return state


@pytest.fixture
def policy_query_state(base_state):
    """AgentState for a policy query."""
    state = dict(base_state)
    state.update({
        "message": "What is the travel reimbursement limit?",
        "intent": "policy_query",
        "entities": {},
        "confidence": 0.9,
    })
    return state


@pytest.fixture
def provision_state(base_state, active_employee):
    """AgentState for a software provisioning request."""
    state = dict(base_state)
    state.update({
        "message": "I need Gitea access",
        "intent": "software_provision",
        "entities": {"systems": ["gitea"]},
        "confidence": 0.95,
        "employee_id": active_employee["employee_id"],
        "employee_profile": active_employee,
    })
    return state


# ---------------------------------------------------------------------------
# RAG chunk fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_chunks():
    """A list of mock child_chunk dicts for RAG tests."""
    return [
        {
            "child_id": "child-001",
            "parent_id": "parent-001",
            "content": "Employees are entitled to 20 days of annual leave per year.",
            "window_index": 0,
            "score": 0.92,
        },
        {
            "child_id": "child-002",
            "parent_id": "parent-001",
            "content": "Sick leave is capped at 10 days per calendar year.",
            "window_index": 1,
            "score": 0.85,
        },
        {
            "child_id": "child-003",
            "parent_id": "parent-002",
            "content": "Travel reimbursement requires manager approval above $500.",
            "window_index": 0,
            "score": 0.78,
        },
    ]


@pytest.fixture
def sample_parent_sections():
    """Mock parent section dicts matching the sample_chunks parent_ids."""
    return [
        {
            "parent_id": "parent-001",
            "document_id": "doc-001",
            "heading": "Leave Entitlements",
            "content": "Full section content about leave...",
            "summary": "Leave entitlement rules",
            "chunk_index": 0,
            "filename": "leave_policy.pdf",
        },
        {
            "parent_id": "parent-002",
            "document_id": "doc-002",
            "heading": "Travel & Expenses",
            "content": "Full section content about travel...",
            "summary": "Travel and expense reimbursement rules",
            "chunk_index": 1,
            "filename": "expenses_policy.pdf",
        },
    ]


# ---------------------------------------------------------------------------
# Access request fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def pending_access_request():
    """A mock access request in pending_approval status."""
    return {
        "request_id": "AR-20240101120000",
        "requester_id": "EMP-001",
        "requester_email": "alice@example.com",
        "requester_name": "Alice Smith",
        "package_id": "PKG-GH-ENG-STD",
        "package_name": "Gitea Engineering Standard",
        "target_system": "gitea",
        "approver_id": "EMP-100",
        "status": "pending_approval",
        "created_ts": "2024-01-01T12:00:00+00:00",
        "decided_ts": None,
        "fulfillment_result": None,
    }


@pytest.fixture
def fulfilled_access_request():
    """A mock access request in fulfilled status."""
    return {
        "request_id": "AR-20240101130000",
        "requester_id": "EMP-001",
        "requester_email": "alice@example.com",
        "requester_name": "Alice Smith",
        "package_id": "PKG-SL-ENG-STD",
        "package_name": "Mattermost Engineering Standard",
        "target_system": "mattermost",
        "approver_id": "EMP-100",
        "status": "fulfilled",
        "created_ts": "2024-01-01T12:00:00+00:00",
        "decided_ts": "2024-01-01T13:00:00+00:00",
        "fulfillment_result": '{"system": "mattermost", "team": "engineering"}',
    }
