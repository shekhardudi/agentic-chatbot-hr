-- Synthetic HR seed data

-- -----------------------------------------------------------------------
-- Tables
-- -----------------------------------------------------------------------

CREATE TABLE IF NOT EXISTS employees (
    employee_id    TEXT PRIMARY KEY,
    email          TEXT NOT NULL UNIQUE,
    full_name      TEXT NOT NULL,
    preferred_name TEXT,
    title          TEXT,
    department     TEXT NOT NULL,
    business_unit  TEXT,
    office_location TEXT,
    employment_type TEXT NOT NULL DEFAULT 'full_time',
    manager_id     TEXT,
    hire_date      DATE NOT NULL,
    status         TEXT NOT NULL DEFAULT 'active',
    github_username TEXT,
    slack_user_id  TEXT,
    is_manager     BOOLEAN NOT NULL DEFAULT FALSE
);

CREATE TABLE IF NOT EXISTS leave_balances (
    id              SERIAL PRIMARY KEY,
    employee_id     TEXT NOT NULL REFERENCES employees(employee_id),
    leave_type      TEXT NOT NULL,
    balance_hours   NUMERIC(10,1) NOT NULL DEFAULT 0,
    accrued_ytd_hours NUMERIC(10,1) NOT NULL DEFAULT 0,
    used_ytd_hours  NUMERIC(10,1) NOT NULL DEFAULT 0,
    as_of_ts        TIMESTAMPTZ NOT NULL DEFAULT now(),
    UNIQUE (employee_id, leave_type)
);

CREATE TABLE IF NOT EXISTS access_packages (
    package_id     TEXT PRIMARY KEY,
    package_name   TEXT NOT NULL UNIQUE,
    target_system  TEXT NOT NULL,
    risk_level     TEXT NOT NULL DEFAULT 'low',
    approval_rule  TEXT NOT NULL,
    payload        JSONB NOT NULL DEFAULT '{}'
);

CREATE TABLE IF NOT EXISTS access_requests (
    request_id     TEXT PRIMARY KEY,
    requester_id   TEXT NOT NULL REFERENCES employees(employee_id),
    package_id     TEXT NOT NULL REFERENCES access_packages(package_id),
    approver_id    TEXT REFERENCES employees(employee_id),
    status         TEXT NOT NULL DEFAULT 'pending',
    created_ts     TIMESTAMPTZ NOT NULL DEFAULT now(),
    decided_ts     TIMESTAMPTZ,
    fulfillment_result JSONB
);

-- -----------------------------------------------------------------------
-- Seed data
-- -----------------------------------------------------------------------

INSERT INTO employees (employee_id, email, full_name, preferred_name, title, department, business_unit, office_location, employment_type, manager_id, hire_date, status, github_username, slack_user_id, is_manager) VALUES
  ('EMP-100', 'priya.shah@demo.local', 'Priya Shah', 'Priya', 'Engineering Manager', 'Engineering', 'Infrastructure', 'San Francisco', 'full_time', '', '2015-03-12', 'active', 'priyashah', 'U_PRIYASHAH', TRUE),
  ('EMP-101', 'hannah.lopez@demo.local', 'Hannah Lopez', 'Hannah', 'HR Manager', 'HR', 'Product', 'London', 'full_time', '', '2017-04-08', 'active', 'hannahlopez', 'U_HANNAHLOPEZ', TRUE),
  ('EMP-102', 'brent.mendoza@demo.local', 'Brent Mendoza', 'Brent', 'Finance Manager', 'Finance', 'Product', 'New York', 'full_time', '', '2014-12-04', 'active', 'brentmendoza', 'U_BRENTMENDOZA', TRUE),
  ('EMP-103', 'frank.fox@demo.local', 'Frank Fox', 'Frank', 'Legal Manager', 'Legal', 'Product', 'San Francisco', 'full_time', '', '2015-02-08', 'active', 'frankfox', 'U_FRANKFOX', TRUE),
  ('EMP-104', 'daniel.potts@demo.local', 'Daniel Potts', 'Daniel', 'Operations Manager', 'Operations', 'Infrastructure', 'San Francisco', 'full_time', '', '2015-10-19', 'active', 'danielpotts', 'U_DANIELPOTTS', TRUE),
  ('EMP-001', 'shekhar.dudi@demo.local', 'Shekhar Dudi', 'Shekhar', 'Lead AI Engineer', 'Engineering', 'Product', 'San Francisco', 'full_time', 'EMP-100', '2023-06-15', 'active', 'shekhardudi', 'U_SHEKHARDUDI', FALSE),
  ('EMP-002', 'anna.massey@demo.local', 'Anna Massey', 'Anna', 'Research scientist (medical)', 'Engineering', 'Product', 'Remote', 'full_time', 'EMP-100', '2026-04-01', 'active', 'annamassey', 'U_ANNAMASSEY', FALSE),
  ('EMP-003', 'diana.lopez@demo.local', 'Diana Lopez', 'Diana', 'Principal Engineer', 'Engineering', 'Infrastructure', 'San Francisco', 'full_time', 'EMP-100', '2018-01-04', 'active', 'dianalopez', 'U_DIANALOPEZ', FALSE),
  ('EMP-004', 'stephen.neal@demo.local', 'Stephen Neal', 'Stephen', 'Naval architect', 'HR', 'Corporate', 'New York', 'full_time', 'EMP-101', '2022-07-05', 'inactive', 'stephenneal', 'U_STEPHENNEAL', FALSE),
  ('EMP-005', 'contractor@demo.local', 'Ricky Dougherty', 'Ricky', 'Contract Developer', 'Engineering', 'Product', 'Remote', 'contractor', 'EMP-100', '2025-06-25', 'active', 'rickydougherty', 'U_RICKYDOUGHERTY', FALSE),
  ('EMP-006', 'erica.white@demo.local', 'Erica White', 'Erica', 'Senior Financial Analyst', 'Finance', 'Corporate', 'New York', 'full_time', 'EMP-102', '2022-06-23', 'active', 'ericawhite', 'U_ERICAWHITE', FALSE),
  ('EMP-007', 'sarah.smith@demo.local', 'Sarah Smith', 'Sarah', 'Armed forces training and education officer', 'Operations', 'Product', 'New York', 'full_time', 'EMP-104', '2018-09-23', 'active', 'sarahsmith', 'U_SARAHSMITH', FALSE),
  ('EMP-008', 'brittany.foley@demo.local', 'Brittany Foley', 'Brittany', 'Clinical embryologist', 'Operations', 'Infrastructure', 'Remote', 'full_time', 'EMP-104', '2022-09-16', 'active', 'brittanyfoley', 'U_BRITTANYFOLEY', FALSE),
  ('EMP-009', 'alexis.johnson@demo.local', 'Alexis Johnson', 'Alexis', 'Metallurgist', 'HR', 'Product', 'New York', 'full_time', 'EMP-101', '2023-02-06', 'active', 'alexisjohnson', 'U_ALEXISJOHNSON', FALSE),
  ('EMP-010', 'maurice.ferguson@demo.local', 'Maurice Ferguson', 'Maurice', 'Electronics engineer', 'Legal', 'Corporate', 'San Francisco', 'full_time', 'EMP-103', '2024-09-28', 'active', 'mauriceferguson', 'U_MAURICEFERGUSON', FALSE),
  ('EMP-011', 'crystal.campbell@demo.local', 'Crystal Campbell', 'Crystal', 'Dancer', 'Engineering', 'Corporate', 'London', 'full_time', 'EMP-100', '2025-04-14', 'active', 'crystalcampbell', 'U_CRYSTALCAMPBELL', FALSE),
  ('EMP-012', 'sandra.mendoza@demo.local', 'Sandra Mendoza', 'Sandra', 'Health promotion specialist', 'Engineering', 'Corporate', 'San Francisco', 'part_time', 'EMP-100', '2020-12-29', 'active', 'sandramendoza', 'U_SANDRAMENDOZA', FALSE),
  ('EMP-013', 'jodi.flowers@demo.local', 'Jodi Flowers', 'Jodi', 'Ergonomist', 'Operations', 'Corporate', 'New York', 'full_time', 'EMP-104', '2025-02-22', 'active', 'jodiflowers', 'U_JODIFLOWERS', FALSE),
  ('EMP-014', 'jeremy.carpenter@demo.local', 'Jeremy Carpenter', 'Jeremy', 'Production manager', 'Engineering', 'Corporate', 'San Francisco', 'full_time', 'EMP-100', '2024-01-02', 'active', 'jeremycarpenter', 'U_JEREMYCARPENTER', FALSE),
  ('EMP-015', 'garrett.weeks@demo.local', 'Garrett Weeks', 'Garrett', 'Biochemist, clinical', 'HR', 'Corporate', 'London', 'contractor', 'EMP-101', '2025-02-04', 'active', 'garrettweeks', 'U_GARRETTWEEKS', FALSE),
  ('EMP-016', 'kelsey.lopez@demo.local', 'Kelsey Lopez', 'Kelsey', 'Chartered loss adjuster', 'HR', 'Corporate', 'San Francisco', 'full_time', 'EMP-101', '2021-08-25', 'active', 'kelseylopez', 'U_KELSEYLOPEZ', FALSE),
  ('EMP-017', 'alyssa.flores@demo.local', 'Alyssa Flores', 'Alyssa', 'Designer, fashion/clothing', 'Operations', 'Product', 'New York', 'full_time', 'EMP-104', '2025-05-09', 'active', 'alyssaflores', 'U_ALYSSAFLORES', FALSE),
  ('EMP-018', 'craig.colon@demo.local', 'Craig Colon', 'Craig', 'Scientist, forensic', 'Legal', 'Infrastructure', 'New York', 'full_time', 'EMP-103', '2021-10-10', 'on_leave', 'craigcolon', 'U_CRAIGCOLON', FALSE),
  ('EMP-019', 'wanda.garrett@demo.local', 'Wanda Garrett', 'Wanda', 'Designer, ceramics/pottery', 'Finance', 'Product', 'San Francisco', 'part_time', 'EMP-102', '2024-08-20', 'active', 'wandagarrett', 'U_WANDAGARRETT', FALSE),
  ('EMP-020', 'angelica.silva@demo.local', 'Angelica Silva', 'Angelica', 'Oncologist', 'Finance', 'Infrastructure', 'London', 'full_time', 'EMP-102', '2020-10-03', 'active', 'angelicasilva', 'U_ANGELICASILVA', FALSE);

INSERT INTO leave_balances (employee_id, leave_type, balance_hours, accrued_ytd_hours, used_ytd_hours, as_of_ts) VALUES
  ('EMP-100', 'annual', 151.5, 160, 8.5, '2026-04-15T15:12:04.392609+00:00'),
  ('EMP-100', 'sick', 1313.2, 1333.2, 20.0, '2026-04-15T15:12:04.392647+00:00'),
  ('EMP-100', 'personal', 13.4, 24.0, 10.6, '2026-04-15T15:12:04.392655+00:00'),
  ('EMP-100', 'long_service', 480.0, 480.0, 0.0, '2026-04-15T15:12:04.392662+00:00'),
  ('EMP-101', 'annual', 134.3, 160, 25.7, '2026-04-15T15:12:04.392685+00:00'),
  ('EMP-101', 'sick', 1078.2, 1083.9, 5.7, '2026-04-15T15:12:04.392697+00:00'),
  ('EMP-101', 'personal', 22.3, 24.0, 1.7, '2026-04-15T15:12:04.392704+00:00'),
  ('EMP-101', 'long_service', 480.0, 480.0, 0.0, '2026-04-15T15:12:04.392711+00:00'),
  ('EMP-102', 'annual', 130.2, 160, 29.8, '2026-04-15T15:12:04.392724+00:00'),
  ('EMP-102', 'sick', 1343.9, 1365.5, 21.6, '2026-04-15T15:12:04.392734+00:00'),
  ('EMP-102', 'personal', 15.0, 24.0, 9.0, '2026-04-15T15:12:04.392741+00:00'),
  ('EMP-102', 'long_service', 480.0, 480.0, 0.0, '2026-04-15T15:12:04.392746+00:00'),
  ('EMP-103', 'annual', 142.9, 160, 17.1, '2026-04-15T15:12:04.392757+00:00'),
  ('EMP-103', 'sick', 1320.5, 1343.8, 23.3, '2026-04-15T15:12:04.393305+00:00'),
  ('EMP-103', 'personal', 19.7, 24.0, 4.3, '2026-04-15T15:12:04.393331+00:00'),
  ('EMP-103', 'long_service', 480.0, 480.0, 0.0, '2026-04-15T15:12:04.393337+00:00'),
  ('EMP-104', 'annual', 120.1, 160, 39.9, '2026-04-15T15:12:04.393357+00:00'),
  ('EMP-104', 'sick', 1255.0, 1260.5, 5.5, '2026-04-15T15:12:04.393366+00:00'),
  ('EMP-104', 'personal', 18.1, 24.0, 5.9, '2026-04-15T15:12:04.393379+00:00'),
  ('EMP-104', 'long_service', 480.0, 480.0, 0.0, '2026-04-15T15:12:04.393383+00:00'),
  ('EMP-001', 'annual', 26.5, 56.7, 30.2, '2026-04-15T15:12:04.393390+00:00'),
  ('EMP-001', 'sick', 306.4, 340.8, 34.4, '2026-04-15T15:12:04.393395+00:00'),
  ('EMP-001', 'personal', 22.2, 24.0, 1.8, '2026-04-15T15:12:04.393400+00:00'),
  ('EMP-002', 'annual', 4.0, 4.0, 0.0, '2026-04-15T15:12:04.393408+00:00'),
  ('EMP-002', 'sick', 0.0, 0.0, 0.0, '2026-04-15T15:12:04.393413+00:00'),
  ('EMP-002', 'personal', 16.8, 24.0, 7.2, '2026-04-15T15:12:04.393417+00:00'),
  ('EMP-003', 'annual', 144.6, 160, 15.4, '2026-04-15T15:12:04.393424+00:00'),
  ('EMP-003', 'sick', 970.9, 994.7, 23.8, '2026-04-15T15:12:04.393429+00:00'),
  ('EMP-003', 'personal', 18.4, 24.0, 5.6, '2026-04-15T15:12:04.393432+00:00'),
  ('EMP-003', 'long_service', 480.0, 480.0, 0.0, '2026-04-15T15:12:04.393436+00:00'),
  ('EMP-004', 'annual', 65.5, 75.6, 10.1, '2026-04-15T15:12:04.393442+00:00'),
  ('EMP-004', 'sick', 432.2, 454.3, 22.1, '2026-04-15T15:12:04.393446+00:00'),
  ('EMP-004', 'personal', 12.7, 24.0, 11.3, '2026-04-15T15:12:04.393460+00:00'),
  ('EMP-006', 'annual', 49.1, 76.3, 27.2, '2026-04-15T15:12:04.393467+00:00'),
  ('EMP-006', 'sick', 453.6, 458.2, 4.6, '2026-04-15T15:12:04.393472+00:00'),
  ('EMP-006', 'personal', 13.4, 24.0, 10.6, '2026-04-15T15:12:04.393476+00:00'),
  ('EMP-007', 'annual', 121.2, 151.2, 30.0, '2026-04-15T15:12:04.393483+00:00'),
  ('EMP-007', 'sick', 877.9, 908.6, 30.7, '2026-04-15T15:12:04.393495+00:00'),
  ('EMP-007', 'personal', 19.9, 24.0, 4.1, '2026-04-15T15:12:04.393499+00:00'),
  ('EMP-007', 'long_service', 480.0, 480.0, 0.0, '2026-04-15T15:12:04.393503+00:00'),
  ('EMP-008', 'annual', 59.9, 71.6, 11.7, '2026-04-15T15:12:04.393510+00:00'),
  ('EMP-008', 'sick', 424.0, 430.3, 6.3, '2026-04-15T15:12:04.393516+00:00'),
  ('EMP-008', 'personal', 24.0, 24.0, 0.0, '2026-04-15T15:12:04.393520+00:00'),
  ('EMP-009', 'annual', 34.9, 63.8, 28.9, '2026-04-15T15:12:04.393527+00:00'),
  ('EMP-009', 'sick', 354.4, 383.2, 28.8, '2026-04-15T15:12:04.393533+00:00'),
  ('EMP-009', 'personal', 12.3, 24.0, 11.7, '2026-04-15T15:12:04.393537+00:00'),
  ('EMP-010', 'annual', 7.3, 30.9, 23.6, '2026-04-15T15:12:04.393545+00:00'),
  ('EMP-010', 'sick', 165.6, 185.9, 20.3, '2026-04-15T15:12:04.393550+00:00'),
  ('EMP-010', 'personal', 22.7, 24.0, 1.3, '2026-04-15T15:12:04.393555+00:00'),
  ('EMP-011', 'annual', 7.5, 20.1, 12.6, '2026-04-15T15:12:04.393561+00:00'),
  ('EMP-011', 'sick', 87.0, 120.7, 33.7, '2026-04-15T15:12:04.393566+00:00'),
  ('EMP-011', 'personal', 17.9, 24.0, 6.1, '2026-04-15T15:12:04.393571+00:00'),
  ('EMP-012', 'annual', 97.9, 105.9, 8.0, '2026-04-15T15:12:04.393579+00:00'),
  ('EMP-012', 'sick', 303.1, 318.1, 15.0, '2026-04-15T15:12:04.393584+00:00'),
  ('EMP-012', 'personal', 10.1, 12.0, 1.9, '2026-04-15T15:12:04.393588+00:00'),
  ('EMP-013', 'annual', 1.1, 22.9, 21.8, '2026-04-15T15:12:04.393598+00:00'),
  ('EMP-013', 'sick', 100.6, 137.5, 36.9, '2026-04-15T15:12:04.393603+00:00'),
  ('EMP-013', 'personal', 13.0, 24.0, 11.0, '2026-04-15T15:12:04.393607+00:00'),
  ('EMP-014', 'annual', 21.7, 45.7, 24.0, '2026-04-15T15:12:04.393614+00:00'),
  ('EMP-014', 'sick', 255.2, 274.7, 19.5, '2026-04-15T15:12:04.393619+00:00'),
  ('EMP-014', 'personal', 22.7, 24.0, 1.3, '2026-04-15T15:12:04.393624+00:00'),
  ('EMP-016', 'annual', 78.3, 92.8, 14.5, '2026-04-15T15:12:04.393636+00:00'),
  ('EMP-016', 'sick', 518.2, 557.6, 39.4, '2026-04-15T15:12:04.393644+00:00'),
  ('EMP-016', 'personal', 14.3, 24.0, 9.7, '2026-04-15T15:12:04.393648+00:00'),
  ('EMP-017', 'annual', 14.2, 18.7, 4.5, '2026-04-15T15:12:04.393656+00:00'),
  ('EMP-017', 'sick', 102.9, 112.5, 9.6, '2026-04-15T15:12:04.393661+00:00'),
  ('EMP-017', 'personal', 17.2, 24.0, 6.8, '2026-04-15T15:12:04.393665+00:00'),
  ('EMP-018', 'annual', 87.1, 90.3, 3.2, '2026-04-15T15:12:04.393688+00:00'),
  ('EMP-018', 'sick', 513.1, 542.4, 29.3, '2026-04-15T15:12:04.393696+00:00'),
  ('EMP-018', 'personal', 14.2, 24.0, 9.8, '2026-04-15T15:12:04.393700+00:00'),
  ('EMP-019', 'annual', 0.8, 33.1, 32.3, '2026-04-15T15:12:04.393708+00:00'),
  ('EMP-019', 'sick', 78.0, 99.3, 21.3, '2026-04-15T15:12:04.393715+00:00'),
  ('EMP-019', 'personal', 10.5, 12.0, 1.5, '2026-04-15T15:12:04.393720+00:00'),
  ('EMP-020', 'annual', 84.3, 110.7, 26.4, '2026-04-15T15:12:04.393728+00:00'),
  ('EMP-020', 'sick', 626.9, 664.8, 37.9, '2026-04-15T15:12:04.393929+00:00'),
  ('EMP-020', 'personal', 22.0, 24.0, 2.0, '2026-04-15T15:12:04.393948+00:00');

INSERT INTO access_packages (package_id, package_name, target_system, risk_level, approval_rule, payload) VALUES
  ('PKG-GH-ENG-STD', 'github_engineering_standard', 'gitea', 'low', 'manager_auto_approve', '{"org": "agentic-hr", "team": "engineering", "role": "member", "permission": "write"}'),
  ('PKG-SL-ENG-STD', 'slack_engineering_standard', 'mattermost', 'low', 'manager_auto_approve', '{"team": "engineering", "channels": ["general", "engineering", "standups"], "role": "member"}');
