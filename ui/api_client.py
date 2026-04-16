import requests
from config import BACKEND_URL


def send_message(employee_email: str, message: str, session_id: str | None = None) -> dict:
    """POST /chat"""
    response = requests.post(
        f"{BACKEND_URL}/chat",
        json={"employee_email": employee_email, "message": message, "session_id": session_id},
        timeout=60,
    )
    response.raise_for_status()
    return response.json()


def get_pending_approvals() -> list[dict]:
    """GET /approvals"""
    response = requests.get(f"{BACKEND_URL}/approvals", timeout=15)
    response.raise_for_status()
    return response.json()


def submit_decision(request_id: str, decision: str, approver_email: str) -> dict:
    """POST /approvals/{request_id}"""
    response = requests.post(
        f"{BACKEND_URL}/approvals/{request_id}",
        json={"decision": decision, "approver_email": approver_email},
        timeout=30,
    )
    response.raise_for_status()
    return response.json()
