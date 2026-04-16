"""
resolve_user node — looks up the employee profile from NocoDB
and loads their employee_id into state.
"""
from logger import get_logger
from models.state import AgentState
from mcp.nocodb_client import NocoDBMCPClient
from config import settings

nocodb = NocoDBMCPClient(settings.nocodb_url, settings.nocodb_api_token, settings.nocodb_base_id)
log = get_logger(__name__)


def resolve_user(state: AgentState) -> AgentState:
    email = state["employee_email"]
    log.info("Resolving employee | email=%s", email)
    try:
        profile = nocodb.get_employee_profile(email)
        if profile:
            state["employee_id"] = profile.get("employee_id")
            log.info("Employee resolved | email=%s | id=%s", email, state["employee_id"])
        else:
            state["employee_id"] = None
            log.warning("Employee profile not found | email=%s", email)
    except Exception as e:
        log.error("resolve_user failed | email=%s | error=%s", email, e)
        state["employee_id"] = None
    return state
