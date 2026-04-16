"""
classify_intent node — triage agent that extracts intent, entities, and confidence.
Uses the fast LLM model.
"""
import json

from logger import get_logger
from models.state import AgentState
from llm.client import fast_chat
from llm.prompts import TRIAGE_PROMPT

log = get_logger(__name__)


def classify_intent(state: AgentState) -> AgentState:
    log.info("Classifying intent | message=%r", state["message"][:80])
    prompt = TRIAGE_PROMPT.format(message=state["message"])
    raw = fast_chat(prompt)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        import re
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(match.group()) if match else {}

    state["intent"] = result.get("intent", "unsupported")
    state["entities"] = result.get("entities", {})
    state["confidence"] = float(result.get("confidence", 0.0))

    log.info(
        "Intent classified | intent=%s | confidence=%.2f | entities=%s",
        state["intent"], state["confidence"], state["entities"],
    )

    state["needs_clarification"] = (
        state["confidence"] < 0.6 and state["intent"] == "unsupported"
    )
    if state["needs_clarification"]:
        log.warning(
            "Low confidence (%.2f) — requesting clarification | message=%r",
            state["confidence"], state["message"][:60],
        )
    return state
