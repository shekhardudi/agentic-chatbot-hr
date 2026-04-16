"""
provision_request node — creates access request records in NocoDB.
"""
from logger import get_logger
from models.state import AgentState
from mcp.nocodb_client import NocoDBMCPClient
from config import settings

nocodb = NocoDBMCPClient(settings.nocodb_url, settings.nocodb_api_token, settings.nocodb_base_id)
log = get_logger(__name__)


def provision_request_node(state: AgentState) -> AgentState:
    packages = state.get("matched_packages") or []
    employee_id = state.get("employee_id") or ""
    email = state["employee_email"]
    log.info("Creating access request(s) | email=%s | packages=%s", email, packages)

    try:
        profile = nocodb.get_employee_profile(email)
        approver_id = (profile or {}).get("manager_id", "")
    except Exception as e:
        log.error("Could not fetch manager_id for %s: %s", email, e)
        approver_id = ""

    request_ids = []
    for pkg_id in packages:
        try:
            req = nocodb.create_access_request(
                requester_id=employee_id,
                requester_email=email,
                package_id=pkg_id,
                approver_id=approver_id,
            )
            rid = req.get("request_id", "")
            request_ids.append(rid)
            log.info("Access request created | id=%s | package=%s", rid, pkg_id)
        except Exception as e:
            log.error("Failed to create access request | package=%s | error=%s", pkg_id, e)
            request_ids.append(f"ERROR:{e}")

    state["request_id"] = request_ids[0] if request_ids else None
    state["approval_status"] = "pending_approval"
    state["status"] = "pending_approval"
    log.info("Provisioning request submitted | request_id=%s", state["request_id"])
    return state
