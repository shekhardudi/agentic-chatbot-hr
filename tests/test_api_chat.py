"""
Tests for the POST /chat API endpoint.
Uses FastAPI TestClient with mocked LangGraph pipeline.
"""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock

from fastapi.testclient import TestClient


def _make_app():
    """Create a minimal FastAPI app with just the chat router for testing."""
    import sys, os
    sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

    # Patch settings before importing to avoid requiring real env vars
    with patch("config.Settings"):
        pass

    from fastapi import FastAPI
    from api.chat import router
    app = FastAPI()
    app.include_router(router)
    return app


@pytest.fixture
def client():
    with patch("api.chat.get_compiled_graph") as mock_graph_factory:
        mock_graph = MagicMock()
        mock_graph_factory.return_value = mock_graph
        yield mock_graph, mock_graph_factory


def _complete_state(**overrides):
    """Build a minimal final AgentState that the mock graph will return."""
    state = {
        "employee_email": "alice@example.com",
        "employee_id": "EMP-001",
        "employee_profile": None,
        "session_id": "test-session",
        "message": "test",
        "intent": "leave_balance",
        "entities": {},
        "confidence": 0.9,
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
        "response": "You have 80 hours of annual leave.",
        "citations": [],
        "status": "complete",
    }
    state.update(overrides)
    return state


class TestChatEndpoint:
    def setup_method(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))

    @patch("api.chat.get_compiled_graph")
    def test_successful_chat_response(self, mock_graph_factory):
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value=_complete_state())
        mock_graph_factory.return_value = mock_graph

        from fastapi import FastAPI
        from api.chat import router
        app = FastAPI()
        app.include_router(router)

        with TestClient(app) as client:
            resp = client.post("/chat", json={
                "employee_email": "alice@example.com",
                "message": "How many leave days do I have?",
            })

        assert resp.status_code == 200
        body = resp.json()
        assert body["response"] == "You have 80 hours of annual leave."
        assert body["intent"] == "leave_balance"
        assert body["status"] == "complete"

    @patch("api.chat.get_compiled_graph")
    def test_session_id_generated_when_missing(self, mock_graph_factory):
        final_state = _complete_state()
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value=final_state)
        mock_graph_factory.return_value = mock_graph

        from fastapi import FastAPI
        from api.chat import router
        app = FastAPI()
        app.include_router(router)

        with TestClient(app) as client:
            resp = client.post("/chat", json={
                "employee_email": "alice@example.com",
                "message": "Hello",
            })

        assert resp.status_code == 200
        call_args = mock_graph.ainvoke.call_args[0][0]
        assert call_args["session_id"] is not None

    @patch("api.chat.get_compiled_graph")
    def test_session_id_passed_through(self, mock_graph_factory):
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value=_complete_state())
        mock_graph_factory.return_value = mock_graph

        from fastapi import FastAPI
        from api.chat import router
        app = FastAPI()
        app.include_router(router)

        with TestClient(app) as client:
            resp = client.post("/chat", json={
                "employee_email": "alice@example.com",
                "message": "Hello",
                "session_id": "my-custom-session",
            })

        call_args = mock_graph.ainvoke.call_args[0][0]
        assert call_args["session_id"] == "my-custom-session"

    @patch("api.chat.get_compiled_graph")
    def test_returns_citations(self, mock_graph_factory):
        citations = [{"document": "policy.pdf", "section": "Leave", "chunk_id": "c1"}]
        final_state = _complete_state(
            intent="policy_query",
            response="You are entitled to 20 days.",
            citations=citations,
        )
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value=final_state)
        mock_graph_factory.return_value = mock_graph

        from fastapi import FastAPI
        from api.chat import router
        app = FastAPI()
        app.include_router(router)

        with TestClient(app) as client:
            resp = client.post("/chat", json={
                "employee_email": "alice@example.com",
                "message": "What is leave entitlement?",
            })

        body = resp.json()
        assert len(body["citations"]) == 1
        assert body["citations"][0]["document"] == "policy.pdf"

    @patch("api.chat.get_compiled_graph")
    def test_returns_request_id_for_provision(self, mock_graph_factory):
        final_state = _complete_state(
            intent="software_provision",
            request_id="AR-001",
            approval_status="pending_approval",
            status="pending_approval",
            response="Your request AR-001 is pending approval.",
        )
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value=final_state)
        mock_graph_factory.return_value = mock_graph

        from fastapi import FastAPI
        from api.chat import router
        app = FastAPI()
        app.include_router(router)

        with TestClient(app) as client:
            resp = client.post("/chat", json={
                "employee_email": "alice@example.com",
                "message": "I need Gitea access",
            })

        body = resp.json()
        assert body["request_id"] == "AR-001"
        assert body["status"] == "pending_approval"

    @patch("api.chat.get_compiled_graph")
    def test_graph_exception_returns_500(self, mock_graph_factory):
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(side_effect=RuntimeError("Graph failed"))
        mock_graph_factory.return_value = mock_graph

        from fastapi import FastAPI
        from api.chat import router
        app = FastAPI()
        app.include_router(router)

        with TestClient(app, raise_server_exceptions=False) as client:
            resp = client.post("/chat", json={
                "employee_email": "alice@example.com",
                "message": "Hello",
            })

        assert resp.status_code == 500

    @patch("api.chat.get_compiled_graph")
    def test_missing_response_uses_fallback(self, mock_graph_factory):
        final_state = _complete_state(response=None)
        mock_graph = MagicMock()
        mock_graph.ainvoke = AsyncMock(return_value=final_state)
        mock_graph_factory.return_value = mock_graph

        from fastapi import FastAPI
        from api.chat import router
        app = FastAPI()
        app.include_router(router)

        with TestClient(app) as client:
            resp = client.post("/chat", json={
                "employee_email": "alice@example.com",
                "message": "Hello",
            })

        body = resp.json()
        assert "sorry" in body["response"].lower() or body["response"] != ""

    def test_missing_email_returns_422(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from fastapi import FastAPI
        from api.chat import router
        app = FastAPI()
        app.include_router(router)

        with TestClient(app) as client:
            resp = client.post("/chat", json={"message": "Hello"})

        assert resp.status_code == 422

    def test_missing_message_returns_422(self):
        import sys, os
        sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", "backend"))
        from fastapi import FastAPI
        from api.chat import router
        app = FastAPI()
        app.include_router(router)

        with TestClient(app) as client:
            resp = client.post("/chat", json={"employee_email": "alice@example.com"})

        assert resp.status_code == 422
