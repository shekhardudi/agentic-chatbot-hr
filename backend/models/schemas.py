from typing import Optional
from pydantic import BaseModel


class ChatRequest(BaseModel):
    employee_email: str
    message: str
    session_id: Optional[str] = None


class Citation(BaseModel):
    document: str
    section: str
    chunk_id: Optional[str] = None


class ChatResponse(BaseModel):
    response: str
    intent: Optional[str] = None
    citations: list[Citation] = []
    request_id: Optional[str] = None
    status: str = "complete"


class ApprovalRequest(BaseModel):
    decision: str  # "approved" | "denied"
    approver_email: str


class PendingApproval(BaseModel):
    request_id: str
    requester_email: str
    requester_name: str = ""
    packages: list[str]
    status: str
    created_ts: str
