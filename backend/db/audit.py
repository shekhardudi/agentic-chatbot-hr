"""
Audit event writer — inserts into audit_events table in PostgreSQL.
"""
import json
from datetime import datetime, timezone

from logger import get_logger
from db.connection import ManagedConn

log = get_logger(__name__)


def write_audit_event(
    session_id: str | None,
    employee_id: str | None,
    employee_email: str | None,
    intent: str | None,
    worker: str | None,
    tools_called: list | None = None,
    evidence_used: list | None = None,
    outcome: str | None = None,
    response_text: str | None = None,
    llm_trace: dict | None = None,
) -> None:
    log.debug(
        "Writing audit event | session=%s | employee=%s | intent=%s | worker=%s | outcome=%s",
        session_id, employee_email, intent, worker, outcome,
    )
    sql = """
        INSERT INTO audit_events (
            event_ts, session_id, employee_id, employee_email,
            intent, worker, tools_called, evidence_used,
            outcome, response_text, llm_trace
        ) VALUES (
            %s, %s, %s, %s,
            %s, %s, %s, %s,
            %s, %s, %s
        )
    """
    now = datetime.now(timezone.utc)
    with ManagedConn() as conn:
        with conn.cursor() as cur:
            cur.execute(
                sql,
                (
                    now,
                    session_id,
                    employee_id,
                    employee_email,
                    intent,
                    worker,
                    json.dumps(tools_called or []),
                    json.dumps(evidence_used or []),
                    outcome,
                    response_text,
                    json.dumps(llm_trace or {}),
                ),
            )
        conn.commit()
    log.debug("Audit event written | session=%s", session_id)
