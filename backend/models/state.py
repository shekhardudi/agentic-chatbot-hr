from typing import TypedDict, Optional


class AgentState(TypedDict):
    # Identity
    employee_email: str
    employee_id: Optional[str]
    employee_profile: Optional[dict]
    session_id: Optional[str]
    message: str

    # Triage
    intent: Optional[str]           # leave_balance | policy_query | software_provision | unsupported
    entities: Optional[dict]
    confidence: Optional[float]
    needs_clarification: bool

    # HR worker
    leave_data: Optional[dict]

    # Policy RAG worker
    rewritten_queries: Optional[list]
    retrieved_chunks: Optional[list]
    parent_sections: Optional[list]
    evidence_sufficient: Optional[bool]
    topic_verdicts: Optional[list]

    # Provisioning worker
    matched_packages: Optional[list]
    eligible: Optional[bool]
    eligibility_reason: Optional[str]
    request_id: Optional[str]
    approval_status: Optional[str]
    fulfillment_result: Optional[dict]

    # Leave application
    leave_apply_type: Optional[str]
    leave_apply_hours: Optional[float]
    leave_apply_duration: Optional[float]
    leave_apply_unit: Optional[str]
    leave_apply_sufficient: Optional[bool]
    leave_apply_current_balance: Optional[float]
    leave_apply_new_balance: Optional[float]
    leave_apply_status: Optional[str]

    # Access request status
    access_requests_data: Optional[list]

    # Output
    response: Optional[str]
    citations: Optional[list]
    status: Optional[str]
