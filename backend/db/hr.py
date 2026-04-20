"""
Direct PostgreSQL data access for HR tables: employees, access_packages,
access_requests.  Replaces NocoDB REST calls in the provision / approval path.
"""
import json
from datetime import datetime, timezone

from logger import get_logger
from db.connection import ManagedConn

log = get_logger(__name__)


def _rows_to_dicts(cur) -> list[dict]:
    cols = [d[0] for d in cur.description]
    return [dict(zip(cols, row)) for row in cur.fetchall()]


def _row_to_dict(cur) -> dict | None:
    row = cur.fetchone()
    if row is None:
        return None
    cols = [d[0] for d in cur.description]
    return dict(zip(cols, row))


# ------------------------------------------------------------------
# Employee queries (READ-only)
# ------------------------------------------------------------------

def get_employee_profile(email: str) -> dict | None:
    log.info("Fetching employee profile | email=%s", email)
    with ManagedConn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM employees WHERE email = %s", (email,))
            result = _row_to_dict(cur)
    if result:
        log.info("Employee found | email=%s | id=%s", email, result.get("employee_id"))
    else:
        log.warning("Employee not found | email=%s", email)
    return result


def get_employee_by_id(employee_id: str) -> dict | None:
    log.info("Fetching employee profile | employee_id=%s", employee_id)
    with ManagedConn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM employees WHERE employee_id = %s", (employee_id,))
            result = _row_to_dict(cur)
    if result:
        log.info("Employee found | employee_id=%s | email=%s", employee_id, result.get("email"))
    else:
        log.warning("Employee not found | employee_id=%s", employee_id)
    return result


# ------------------------------------------------------------------
# Access package queries (READ-only)
# ------------------------------------------------------------------

def list_access_packages() -> list[dict]:
    log.debug("Listing all access packages")
    with ManagedConn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM access_packages")
            results = _rows_to_dicts(cur)
    log.debug("Access packages returned %d rows", len(results))
    return results


def get_access_package(package_id: str) -> dict | None:
    log.debug("Fetching access package | package_id=%s", package_id)
    with ManagedConn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM access_packages WHERE package_id = %s", (package_id,))
            return _row_to_dict(cur)


# ------------------------------------------------------------------
# Access request queries (READ + WRITE)
# ------------------------------------------------------------------

def create_access_request(
    requester_id: str,
    requester_email: str,
    package_id: str,
    approver_id: str,
) -> dict:
    request_id = f"AR-{datetime.now(timezone.utc).strftime('%Y%m%d%H%M%S')}"
    now = datetime.now(timezone.utc)
    log.info("Creating access request | requester=%s | package=%s | id=%s", requester_email, package_id, request_id)
    sql = """
        INSERT INTO access_requests (request_id, requester_id, package_id, approver_id, status, created_ts)
        VALUES (%s, %s, %s, %s, %s, %s)
        RETURNING *
    """
    with ManagedConn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (request_id, requester_id, package_id, approver_id, "pending_approval", now))
            result = _row_to_dict(cur)
        conn.commit()
    log.info("Access request created | id=%s", request_id)
    return result


def list_access_requests(status: str | None = None) -> list[dict]:
    log.debug("Listing access requests | status=%s", status)
    sql = """
        SELECT r.*, e.email AS requester_email, e.full_name AS requester_name
        FROM access_requests r
        LEFT JOIN employees e ON e.employee_id = r.requester_id
    """
    with ManagedConn() as conn:
        with conn.cursor() as cur:
            if status:
                cur.execute(sql + " WHERE r.status = %s ORDER BY r.created_ts DESC", (status,))
            else:
                cur.execute(sql + " ORDER BY r.created_ts DESC")
            return _rows_to_dicts(cur)


def get_access_request(request_id: str) -> dict | None:
    log.debug("Fetching access request | id=%s", request_id)
    with ManagedConn() as conn:
        with conn.cursor() as cur:
            cur.execute("SELECT * FROM access_requests WHERE request_id = %s", (request_id,))
            return _row_to_dict(cur)


def approve_or_deny_request(request_id: str, decision: str, approver_email: str) -> dict:
    log.info("Decision on request %s: %s by %s", request_id, decision, approver_email)
    now = datetime.now(timezone.utc)
    sql = """
        UPDATE access_requests
        SET status = %s, decided_ts = %s
        WHERE request_id = %s
        RETURNING *
    """
    with ManagedConn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, (decision, now, request_id))
            result = _row_to_dict(cur)
        conn.commit()
    if result is None:
        raise ValueError(f"Access request '{request_id}' not found.")
    return result


def get_access_requests_by_employee(
    employee_id: str,
    request_id: str | None = None,
    target_systems: list[str] | None = None,
) -> list[dict]:
    """Get access requests for an employee, joined with access_packages for names."""
    sql = """
        SELECT
            ar.request_id,
            ar.package_id,
            ap.package_name,
            ap.target_system,
            ar.status,
            ar.created_ts,
            ar.decided_ts,
            ar.fulfillment_result
        FROM access_requests ar
        LEFT JOIN access_packages ap ON ar.package_id = ap.package_id
        WHERE ar.requester_id = %s
    """
    params: list = [employee_id]

    if request_id:
        sql += " AND ar.request_id = %s"
        params.append(request_id)

    if target_systems:
        placeholders = ", ".join(["%s"] * len(target_systems))
        sql += f" AND LOWER(ap.target_system) IN ({placeholders})"
        params.extend([s.lower() for s in target_systems])

    sql += " ORDER BY ar.created_ts DESC"

    log.info("Fetching access requests | employee_id=%s | request_id=%s | systems=%s", employee_id, request_id, target_systems)
    with ManagedConn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, params)
            results = _rows_to_dicts(cur)
    log.info("Access requests returned %d rows | employee_id=%s", len(results), employee_id)
    return results


def update_request_fulfillment(request_id: str, result: dict) -> dict:
    log.info("Updating fulfillment | request_id=%s", request_id)
    sql = """
        UPDATE access_requests
        SET status = %s, fulfillment_result = %s
        WHERE request_id = %s
        RETURNING *
    """
    with ManagedConn() as conn:
        with conn.cursor() as cur:
            cur.execute(sql, ("fulfilled", json.dumps(result), request_id))
            row = _row_to_dict(cur)
        conn.commit()
    if row is None:
        raise ValueError(f"Access request '{request_id}' not found.")
    return row
