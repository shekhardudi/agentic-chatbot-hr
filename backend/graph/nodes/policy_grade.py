"""
policy_grade node — LLM grades whether retrieved evidence is sufficient
to answer the question. If not, the answer node will abstain.
"""
import json
import re

from logger import get_logger
from models.state import AgentState
from llm.client import fast_chat
from llm.prompts import EVIDENCE_GRADE_PROMPT

log = get_logger(__name__)


def policy_grade_node(state: AgentState) -> AgentState:
    chunks = state.get("retrieved_chunks") or []
    log.info("Evidence grading | chunks available=%d", len(chunks))

    if not chunks:
        log.warning("No chunks available — evidence insufficient")
        state["evidence_sufficient"] = False
        return state

    evidence_text = "\n\n---\n\n".join(
        f"[{c['child_id']}] {c['content']}" for c in chunks[:6]
    )
    prompt = EVIDENCE_GRADE_PROMPT.format(
        question=state["message"],
        evidence=evidence_text,
    )
    raw = fast_chat(prompt)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(match.group()) if match else {"sufficient": False}

    state["evidence_sufficient"] = bool(result.get("sufficient", False))
    reason = result.get("reason", "")
    log.info("Evidence grade | sufficient=%s | reason=%r", state["evidence_sufficient"], reason[:100])

    if not state["evidence_sufficient"]:
        log.warning("Evidence insufficient — policy_answer will abstain")
    return state
