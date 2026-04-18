"""provision_request node — creates access request records."""
from logger import get_logger
from models.state import AgentState
from db.hr import get_employee_profile, create_access_request

log = get_logger(__name__)


def provision_request_node(state: AgentState) -> AgentState:
    packages = state.get("matched_packages") or []
    employee_id = state.get("employee_id") or ""
    email = state["employee_email"]
    log.info("Creating access request(s) | email=%s | packages=%s", email, packages)

    profile = state.get("employee_profile")
    if not profile:
        log.debug("Profile not in state — fetching from DB | email=%s", email)
        try:
            profile = get_employee_profile(email)
        except Exception as e:
            log.error("Could not fetch profile for %s: %s", email, e)
            profile = {}
    approver_id = profile.get("manager_id", "")

    request_ids = []
    for pkg_id in packages:
        try:
            req = create_access_request(
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
