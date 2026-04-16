"""
clarify node — asks one targeted clarification question when intent confidence is low.
"""
from logger import get_logger
from models.state import AgentState
from llm.client import fast_chat

log = get_logger(__name__)

_SYSTEM = (
    "You are an HR assistant. The employee's request was unclear. "
    "Ask ONE short, specific clarification question to understand what they need. "
    "Do not explain yourself or ask multiple questions."
)


def clarify(state: AgentState) -> AgentState:
    log.info("Requesting clarification | session=%s", state.get("session_id"))
    prompt = f"Employee message: {state['message']}\n\nAsk one clarification question."
    state["response"] = fast_chat(prompt, system=_SYSTEM)
    state["status"] = "needs_clarification"
    log.debug("Clarification question generated")
    return state
