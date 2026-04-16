"""
generate.py — generates synthetic HR data using Faker.

Produces JSON files in synthetic_data/output/ and SQL in synthetic_data/sql/
Run: python synthetic_data/generate.py
"""
import json
import random
from datetime import date, datetime, timezone
from pathlib import Path

from faker import Faker

fake = Faker()
random.seed(42)

OUTPUT_DIR = Path(__file__).parent / "output"
SQL_DIR = Path(__file__).parent / "sql"
OUTPUT_DIR.mkdir(exist_ok=True)
SQL_DIR.mkdir(exist_ok=True)

TODAY = date.today()

DEPARTMENTS = ["Engineering", "HR", "Finance", "Legal", "Operations"]
BUSINESS_UNITS = ["Product", "Corporate", "Infrastructure"]
LOCATIONS = ["San Francisco", "New York", "London", "Remote"]
EMP_TYPES = ["full_time", "part_time", "contractor"]
STATUSES = ["active", "inactive", "on_leave"]
LEAVE_TYPES = ["annual", "sick", "personal", "parental", "long_service"]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def tenure_years(hire_date: date) -> float:
    return (TODAY - hire_date).days / 365.25


def annual_balance(hire: date) -> tuple[float, float, float]:
    years = tenure_years(hire)
    accrued = min(years * 20, 160)
    used = round(random.uniform(0, min(accrued, 40)), 1)
    balance = round(accrued - used, 1)
    return round(accrued, 1), used, balance


def sick_hours(emp_type: str, hire: date) -> tuple[float, float, float]:
    months = (TODAY - hire).days / 30.4
    if emp_type == "contractor":
        return 0.0, 0.0, 0.0
    rate = 10 if emp_type == "full_time" else 5
    accrued = round(months * rate, 1)
    used = round(random.uniform(0, min(accrued, 40)), 1)
    return accrued, used, round(accrued - used, 1)


def make_leave_balances(emp_id: str, emp_type: str, hire_date: date) -> list[dict]:
    if emp_type == "contractor":
        return []
    balances = []
    hire = hire_date if isinstance(hire_date, date) else date.fromisoformat(hire_date)

    # Annual
    accrued, used, balance = annual_balance(hire)
    balances.append({
        "employee_id": emp_id, "leave_type": "annual",
        "balance_hours": balance, "accrued_ytd_hours": accrued,
        "used_ytd_hours": used, "as_of_ts": datetime.now(timezone.utc).isoformat(),
    })

    # Sick
    accrued, used, balance = sick_hours(emp_type, hire)
    balances.append({
        "employee_id": emp_id, "leave_type": "sick",
        "balance_hours": balance, "accrued_ytd_hours": accrued,
        "used_ytd_hours": used, "as_of_ts": datetime.now(timezone.utc).isoformat(),
    })

    # Personal (flat 24 hrs/yr)
    p_accrued = 24.0 if emp_type == "full_time" else 12.0
    p_used = round(random.uniform(0, 12), 1)
    balances.append({
        "employee_id": emp_id, "leave_type": "personal",
        "balance_hours": round(p_accrued - p_used, 1), "accrued_ytd_hours": p_accrued,
        "used_ytd_hours": p_used, "as_of_ts": datetime.now(timezone.utc).isoformat(),
    })

    # Long service (only 7+ years)
    if tenure_years(hire) >= 7:
        balances.append({
            "employee_id": emp_id, "leave_type": "long_service",
            "balance_hours": 480.0, "accrued_ytd_hours": 480.0,
            "used_ytd_hours": 0.0, "as_of_ts": datetime.now(timezone.utc).isoformat(),
        })

    return balances


def make_github_username(name: str) -> str:
    parts = name.lower().split()
    return "".join(parts)


def make_slack_id(name: str) -> str:
    return "U_" + "".join(name.upper().split())


# ---------------------------------------------------------------------------
# Static reference tables
# ---------------------------------------------------------------------------

ACCESS_PACKAGES = [
    {
        "package_id": "PKG-GH-ENG-STD",
        "package_name": "github_engineering_standard",
        "target_system": "gitea",
        "risk_level": "low",
        "approval_rule": "manager_auto_approve",
        "payload": json.dumps({
            "org": "agentic-hr",
            "team": "engineering",
            "role": "member",
            "permission": "write",
        }),
    },
    {
        "package_id": "PKG-SL-ENG-STD",
        "package_name": "slack_engineering_standard",
        "target_system": "mattermost",
        "risk_level": "low",
        "approval_rule": "manager_auto_approve",
        "payload": json.dumps({
            "team": "engineering",
            "channels": ["general", "engineering", "standups"],
            "role": "member",
        }),
    },
]


# ---------------------------------------------------------------------------
# Manager generation (EMP-100 to EMP-104)
# ---------------------------------------------------------------------------

MANAGER_DEPT_MAP = {
    "EMP-100": "Engineering",
    "EMP-101": "HR",
    "EMP-102": "Finance",
    "EMP-103": "Legal",
    "EMP-104": "Operations",
}

managers: list[dict] = []
for mgr_id, dept in MANAGER_DEPT_MAP.items():
    first = fake.first_name()
    last = fake.last_name()
    full = f"{first} {last}"
    hire = fake.date_between(start_date="-12y", end_date="-5y")
    managers.append({
        "employee_id": mgr_id,
        "email": f"{first.lower()}.{last.lower()}@demo.local",
        "full_name": full,
        "preferred_name": first,
        "title": f"{dept} Manager",
        "department": dept,
        "business_unit": random.choice(BUSINESS_UNITS),
        "office_location": random.choice(LOCATIONS),
        "employment_type": "full_time",
        "manager_id": "",
        "hire_date": str(hire),
        "status": "active",
        "github_username": make_github_username(full),
        "slack_user_id": make_slack_id(full),
        "is_manager": True,
    })

# Override EMP-100 as Priya Shah (engineering manager referenced in docs)
managers[0].update({
    "email": "priya.shah@demo.local",
    "full_name": "Priya Shah",
    "preferred_name": "Priya",
    "github_username": "priyashah",
    "slack_user_id": "U_PRIYASHAH",
})


# ---------------------------------------------------------------------------
# Known test employee (EMP-001)
# ---------------------------------------------------------------------------

known_employee = {
    "employee_id": "EMP-001",
    "email": "shekhar.dudi@demo.local",
    "full_name": "Shekhar Dudi",
    "preferred_name": "Shekhar",
    "title": "Lead AI Engineer",
    "department": "Engineering",
    "business_unit": "Product",
    "office_location": "San Francisco",
    "employment_type": "full_time",
    "manager_id": "EMP-100",
    "hire_date": "2023-06-15",
    "status": "active",
    "github_username": "shekhardudi",
    "slack_user_id": "U_SHEKHARDUDI",
    "is_manager": False,
}


# ---------------------------------------------------------------------------
# Edge case employees
# ---------------------------------------------------------------------------

edge_cases: list[dict] = []

# New starter
ns_first, ns_last = fake.first_name(), fake.last_name()
edge_cases.append({
    "employee_id": "EMP-002",
    "email": f"{ns_first.lower()}.{ns_last.lower()}@demo.local",
    "full_name": f"{ns_first} {ns_last}",
    "preferred_name": ns_first,
    "title": fake.job(),
    "department": "Engineering",
    "business_unit": "Product",
    "office_location": "Remote",
    "employment_type": "full_time",
    "manager_id": "EMP-100",
    "hire_date": str(TODAY.replace(day=1)),
    "status": "active",
    "github_username": make_github_username(f"{ns_first} {ns_last}"),
    "slack_user_id": make_slack_id(f"{ns_first} {ns_last}"),
    "is_manager": False,
})

# Long-tenure employee
lt_first, lt_last = fake.first_name(), fake.last_name()
edge_cases.append({
    "employee_id": "EMP-003",
    "email": f"{lt_first.lower()}.{lt_last.lower()}@demo.local",
    "full_name": f"{lt_first} {lt_last}",
    "preferred_name": lt_first,
    "title": "Principal Engineer",
    "department": "Engineering",
    "business_unit": "Infrastructure",
    "office_location": "San Francisco",
    "employment_type": "full_time",
    "manager_id": "EMP-100",
    "hire_date": str(fake.date_between(start_date="-12y", end_date="-8y")),
    "status": "active",
    "github_username": make_github_username(f"{lt_first} {lt_last}"),
    "slack_user_id": make_slack_id(f"{lt_first} {lt_last}"),
    "is_manager": False,
})

# Inactive employee
ia_first, ia_last = fake.first_name(), fake.last_name()
edge_cases.append({
    "employee_id": "EMP-004",
    "email": f"{ia_first.lower()}.{ia_last.lower()}@demo.local",
    "full_name": f"{ia_first} {ia_last}",
    "preferred_name": ia_first,
    "title": fake.job(),
    "department": "HR",
    "business_unit": "Corporate",
    "office_location": "New York",
    "employment_type": "full_time",
    "manager_id": "EMP-101",
    "hire_date": str(fake.date_between(start_date="-5y", end_date="-2y")),
    "status": "inactive",
    "github_username": make_github_username(f"{ia_first} {ia_last}"),
    "slack_user_id": make_slack_id(f"{ia_first} {ia_last}"),
    "is_manager": False,
})

# Contractor
ct_first, ct_last = fake.first_name(), fake.last_name()
edge_cases.append({
    "employee_id": "EMP-005",
    "email": "contractor@demo.local",
    "full_name": f"{ct_first} {ct_last}",
    "preferred_name": ct_first,
    "title": "Contract Developer",
    "department": "Engineering",
    "business_unit": "Product",
    "office_location": "Remote",
    "employment_type": "contractor",
    "manager_id": "EMP-100",
    "hire_date": str(fake.date_between(start_date="-2y", end_date="-6m")),
    "status": "active",
    "github_username": make_github_username(f"{ct_first} {ct_last}"),
    "slack_user_id": make_slack_id(f"{ct_first} {ct_last}"),
    "is_manager": False,
})

# Finance employee (ineligible for GitHub)
fi_first, fi_last = fake.first_name(), fake.last_name()
edge_cases.append({
    "employee_id": "EMP-006",
    "email": f"{fi_first.lower()}.{fi_last.lower()}@demo.local",
    "full_name": f"{fi_first} {fi_last}",
    "preferred_name": fi_first,
    "title": "Senior Financial Analyst",
    "department": "Finance",
    "business_unit": "Corporate",
    "office_location": "New York",
    "employment_type": "full_time",
    "manager_id": "EMP-102",
    "hire_date": str(fake.date_between(start_date="-4y", end_date="-1y")),
    "status": "active",
    "github_username": make_github_username(f"{fi_first} {fi_last}"),
    "slack_user_id": make_slack_id(f"{fi_first} {fi_last}"),
    "is_manager": False,
})


# ---------------------------------------------------------------------------
# Random employees (EMP-007 to EMP-020)
# ---------------------------------------------------------------------------

random_employees: list[dict] = []
for idx in range(7, 21):
    first = fake.first_name()
    last = fake.last_name()
    full = f"{first} {last}"
    dept = random.choice(DEPARTMENTS)
    mgr_dept_id = {v: k for k, v in MANAGER_DEPT_MAP.items()}.get(dept, "EMP-100")
    emp_type = random.choices(EMP_TYPES, weights=[70, 15, 15])[0]
    status = random.choices(STATUSES, weights=[85, 10, 5])[0]
    hire = fake.date_between(start_date="-8y", end_date="-3m")
    random_employees.append({
        "employee_id": f"EMP-{idx:03d}",
        "email": f"{first.lower()}.{last.lower()}@demo.local",
        "full_name": full,
        "preferred_name": first,
        "title": fake.job(),
        "department": dept,
        "business_unit": random.choice(BUSINESS_UNITS),
        "office_location": random.choice(LOCATIONS),
        "employment_type": emp_type,
        "manager_id": mgr_dept_id,
        "hire_date": str(hire),
        "status": status,
        "github_username": make_github_username(full),
        "slack_user_id": make_slack_id(full),
        "is_manager": False,
    })


# ---------------------------------------------------------------------------
# Assemble all employees
# ---------------------------------------------------------------------------

all_employees = managers + [known_employee] + edge_cases + random_employees

# ---------------------------------------------------------------------------
# Leave balances
# ---------------------------------------------------------------------------

all_leave_balances: list[dict] = []
for emp in all_employees:
    hire = date.fromisoformat(emp["hire_date"])
    balances = make_leave_balances(emp["employee_id"], emp["employment_type"], hire)
    all_leave_balances.extend(balances)

# Override EMP-002 (new starter) with tiny balances
for b in all_leave_balances:
    if b["employee_id"] == "EMP-002":
        if b["leave_type"] == "annual":
            b.update({"accrued_ytd_hours": 4.0, "used_ytd_hours": 0.0, "balance_hours": 4.0})
        elif b["leave_type"] == "sick":
            b.update({"accrued_ytd_hours": 0.0, "used_ytd_hours": 0.0, "balance_hours": 0.0})

# ---------------------------------------------------------------------------
# Access requests (a few pre-seeded examples)
# ---------------------------------------------------------------------------

ACCESS_REQUESTS = [
    {
        "request_id": "AR-0001",
        "requester_id": "EMP-001",
        "requester_email": "shekhar.dudi@demo.local",
        "package_id": "PKG-GH-ENG-STD",
        "approver_id": "EMP-100",
        "status": "fulfilled",
        "created_ts": "2026-01-10T09:00:00Z",
        "decided_ts": "2026-01-10T10:00:00Z",
        "fulfillment_result": json.dumps({"gitea": {"team_added": True}}),
    },
    {
        "request_id": "AR-0002",
        "requester_id": "EMP-006",
        "requester_email": edge_cases[4]["email"],
        "package_id": "PKG-GH-ENG-STD",
        "approver_id": "EMP-102",
        "status": "denied",
        "created_ts": "2026-02-01T14:00:00Z",
        "decided_ts": "2026-02-01T15:00:00Z",
        "fulfillment_result": None,
    },
]


# ---------------------------------------------------------------------------
# Write JSON output
# ---------------------------------------------------------------------------

def write_json(filename: str, data) -> None:
    path = OUTPUT_DIR / filename
    path.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    print(f"  Wrote {path} ({len(data)} records)")


print("Generating synthetic data...")
write_json("employees.json", all_employees)
write_json("leave_balances.json", all_leave_balances)
write_json("access_packages.json", ACCESS_PACKAGES)
write_json("access_requests.json", ACCESS_REQUESTS)


# ---------------------------------------------------------------------------
# Write SQL
# ---------------------------------------------------------------------------

def sql_val(v) -> str:
    if v is None:
        return "NULL"
    if isinstance(v, bool):
        return "TRUE" if v else "FALSE"
    return "'" + str(v).replace("'", "''") + "'"


def write_sql() -> None:
    lines = ["-- Synthetic HR seed data\n"]

    # employees
    lines.append("INSERT INTO employees (employee_id, email, full_name, preferred_name, title, department, business_unit, office_location, employment_type, manager_id, hire_date, status, github_username, slack_user_id, is_manager) VALUES")
    rows = []
    for e in all_employees:
        rows.append(
            f"  ({sql_val(e['employee_id'])}, {sql_val(e['email'])}, {sql_val(e['full_name'])}, "
            f"{sql_val(e['preferred_name'])}, {sql_val(e['title'])}, {sql_val(e['department'])}, "
            f"{sql_val(e['business_unit'])}, {sql_val(e['office_location'])}, {sql_val(e['employment_type'])}, "
            f"{sql_val(e['manager_id'])}, {sql_val(e['hire_date'])}, {sql_val(e['status'])}, "
            f"{sql_val(e['github_username'])}, {sql_val(e['slack_user_id'])}, {sql_val(e.get('is_manager', False))})"
        )
    lines.append(",\n".join(rows) + ";\n")

    # leave_balances
    lines.append("INSERT INTO leave_balances (employee_id, leave_type, balance_hours, accrued_ytd_hours, used_ytd_hours, as_of_ts) VALUES")
    rows = []
    for b in all_leave_balances:
        rows.append(
            f"  ({sql_val(b['employee_id'])}, {sql_val(b['leave_type'])}, "
            f"{b['balance_hours']}, {b['accrued_ytd_hours']}, {b['used_ytd_hours']}, "
            f"{sql_val(b['as_of_ts'])})"
        )
    lines.append(",\n".join(rows) + ";\n")

    # access_packages
    lines.append("INSERT INTO access_packages (package_id, package_name, target_system, risk_level, approval_rule, payload) VALUES")
    rows = []
    for p in ACCESS_PACKAGES:
        rows.append(
            f"  ({sql_val(p['package_id'])}, {sql_val(p['package_name'])}, {sql_val(p['target_system'])}, "
            f"{sql_val(p['risk_level'])}, {sql_val(p['approval_rule'])}, {sql_val(p['payload'])})"
        )
    lines.append(",\n".join(rows) + ";\n")

    sql_path = SQL_DIR / "seed.sql"
    sql_path.write_text("\n".join(lines), encoding="utf-8")
    print(f"  Wrote {sql_path}")


write_sql()
print("Done.")
