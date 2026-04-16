"""
Loads all prompt templates from llm/prompt_files/ at import time.
Each prompt uses Python str.format() placeholders, e.g. {message}, {question}.
"""
from pathlib import Path

_PROMPT_DIR = Path(__file__).parent / "prompt_files"


def _load(filename: str) -> str:
    return (_PROMPT_DIR / filename).read_text(encoding="utf-8")


TRIAGE_PROMPT = _load("triage.txt")
QUERY_REWRITE_PROMPT = _load("query_rewrite.txt")
EVIDENCE_GRADE_PROMPT = _load("evidence_grade.txt")
POLICY_ANSWER_PROMPT = _load("policy_answer.txt")
COMPOSE_PROMPT = _load("compose.txt")
