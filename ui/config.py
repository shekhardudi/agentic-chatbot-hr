import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

PERSONAS = [
    {"full_name": "Shekhar Dudi", "email": "shekhar.dudi@demo.local", "role": "Lead AI Engineer"},
    {"full_name": "New Starter", "email": "new.starter@demo.local", "role": "Recently hired employee"},
    {"full_name": "Contractor", "email": "contractor@demo.local", "role": "Contract worker"},
    {"full_name": "Long-Tenure Employee", "email": "longtenure@demo.local", "role": "8+ year employee"},
]

MANAGERS = [
    {"full_name": "Priya Shah", "email": "priya.shah@demo.local"},
    {"full_name": "Manager Two", "email": "manager2@demo.local"},
]

PAGE_TITLE = "Agentic HR Assistant"
