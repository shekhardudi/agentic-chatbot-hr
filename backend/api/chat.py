import uuid

from fastapi import APIRouter, Depends, HTTPException

from logger import get_logger
from models.schemas import ChatRequest, ChatResponse, Citation
from graph.builder import get_compiled_graph

router = APIRouter()
log = get_logger(__name__)


@router.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    session_id = request.session_id or str(uuid.uuid4())
    log.info(
        "POST /chat | session=%s | employee=%s | message=%r",
        session_id,
        request.employee_email,
        request.message[:80],
    )

    initial_state = {
        "employee_email": request.employee_email,
        "employee_id": None,
        "session_id": session_id,
        "message": request.message,
        "intent": None,
        "entities": None,
        "confidence": None,
        "needs_clarification": False,
        "leave_data": None,
        "rewritten_queries": None,
        "retrieved_chunks": None,
        "parent_sections": None,
        "evidence_sufficient": None,
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

    try:
        graph = get_compiled_graph()
        final_state = await graph.ainvoke(initial_state)
    except Exception as e:
        log.error("Graph execution failed | session=%s | error=%s", session_id, e, exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

    intent = final_state.get("intent")
    status = final_state.get("status") or "complete"
    log.info(
        "POST /chat complete | session=%s | intent=%s | status=%s",
        session_id,
        intent,
        status,
    )

    citations = [Citation(**c) for c in (final_state.get("citations") or [])]
    return ChatResponse(
        response=final_state.get("response") or "I'm sorry, I couldn't process your request.",
        intent=intent,
        citations=citations,
        request_id=final_state.get("request_id"),
        status=status,
    )
