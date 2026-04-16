"""
policy_answer node — generates a cited answer using the strong LLM.
If evidence is insufficient, produces an abstention response.
"""
import json
import re

from logger import get_logger
from models.state import AgentState
from llm.client import strong_chat
from llm.prompts import POLICY_ANSWER_PROMPT

log = get_logger(__name__)


def policy_answer_node(state: AgentState) -> AgentState:
    chunks = state.get("retrieved_chunks") or []
    parent_sections = state.get("parent_sections") or []

    if not state.get("evidence_sufficient") or not chunks:
        closest = parent_sections[0] if parent_sections else None
        if closest:
            log.warning(
                "Abstaining — citing closest section | file=%s | heading=%r",
                closest.get("filename"), closest.get("heading", "")[:60],
            )
            state["response"] = (
                f"I found related sections in '{closest['filename']}' "
                f"(section: {closest['heading']}) but not enough evidence to answer confidently. "
                "Please review that section directly."
            )
            state["citations"] = [{
                "document": closest["filename"],
                "section": closest["heading"],
                "chunk_id": None,
            }]
        else:
            log.warning("Abstaining — no relevant sections found")
            state["response"] = (
                "I couldn't find relevant HR policy information to answer your question. "
                "Please contact the HR team directly."
            )
            state["citations"] = []
        return state

    log.info("Generating cited answer | evidence_chunks=%d | parent_sections=%d", len(chunks), len(parent_sections))

    parent_map = {p["parent_id"]: p for p in parent_sections}
    evidence_parts = []
    for c in chunks[:6]:
        parent = parent_map.get(c["parent_id"], {})
        filename = parent.get("filename", "unknown")
        heading = parent.get("heading", "")
        evidence_parts.append(f"[{c['child_id']}] Source: {filename} — {heading}\n{c['content']}")
    evidence_text = "\n\n---\n\n".join(evidence_parts)

    prompt = POLICY_ANSWER_PROMPT.format(
        question=state["message"],
        evidence=evidence_text,
    )
    raw = strong_chat(prompt)

    try:
        result = json.loads(raw)
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", raw, re.DOTALL)
        result = json.loads(match.group()) if match else {"answer": raw, "citations": []}

    state["response"] = result.get("answer", raw)
    state["citations"] = result.get("citations", [])
    log.info("Policy answer generated | citations=%d", len(state["citations"]))
    return state
