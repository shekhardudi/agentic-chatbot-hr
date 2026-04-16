from fastapi import APIRouter, HTTPException

from logger import get_logger
from models.schemas import ApprovalRequest, PendingApproval
from mcp.nocodb_client import NocoDBMCPClient
from config import settings
from graph.nodes.provision_fulfill import run_fulfillment

router = APIRouter()
log = get_logger(__name__)
nocodb = NocoDBMCPClient(settings.nocodb_url, settings.nocodb_api_token, settings.nocodb_base_id)


@router.get("/approvals", response_model=list[PendingApproval])
def list_approvals():
    log.info("GET /approvals — fetching pending requests")
    try:
        requests = nocodb.list_access_requests(status="pending_approval")
    except Exception as e:
        log.error("Failed to fetch approvals from NocoDB: %s", e)
        raise HTTPException(status_code=502, detail=f"NocoDB error: {e}")

    log.info("GET /approvals — found %d pending request(s)", len(requests))
    result = []
    for r in requests:
        pkg = r.get("package_id", "")
        result.append(
            PendingApproval(
                request_id=r["request_id"],
                requester_email=r.get("requester_email", ""),
                packages=[pkg] if pkg else [],
                status=r.get("status", "pending_approval"),
                created_ts=str(r.get("created_ts", "")),
            )
        )
    return result


@router.post("/approvals/{request_id}", response_model=dict)
async def decide_approval(request_id: str, body: ApprovalRequest):
    log.info(
        "POST /approvals/%s — decision=%s by %s",
        request_id,
        body.decision,
        body.approver_email,
    )

    if body.decision not in ("approved", "denied"):
        raise HTTPException(status_code=400, detail="decision must be 'approved' or 'denied'")

    try:
        nocodb.approve_or_deny_request(request_id, body.decision, body.approver_email)
    except Exception as e:
        log.error("Failed to update request %s in NocoDB: %s", request_id, e)
        raise HTTPException(status_code=502, detail=f"NocoDB error: {e}")

    if body.decision == "approved":
        log.info("Request %s approved — triggering fulfillment", request_id)
        try:
            await run_fulfillment(request_id)
            log.info("Fulfillment complete for request %s", request_id)
        except Exception as e:
            log.error("Fulfillment failed for request %s: %s", request_id, e)
            return {"request_id": request_id, "status": "approved", "fulfillment_error": str(e)}
    else:
        log.info("Request %s denied by %s", request_id, body.approver_email)

    return {"request_id": request_id, "status": body.decision}
