import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

PERSONAS = [
    {"full_name": "Shekhar Dudi", "email": "shekhar.dudi@demo.local", "role": "Lead AI Engineer"},
    {"full_name": "Daniel Potts", "email": "daniel.potts@demo.local", "role": "Operations Manager"},
    {"full_name": "Erica White", "email": "erica.white@demo.local", "role": "Senior Financial Analyst"},
    {"full_name": "Hannah Lopez", "email": "hannah.lopez@demo.local", "role": "HR Manager"},
]

MANAGERS = [
    {"full_name": "Vanshika Puri", "email": "vanshika.puri@demo.local"},
]

PAGE_TITLE = "Agentic HR Assistant"
