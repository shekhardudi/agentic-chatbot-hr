import os

BACKEND_URL = os.getenv("BACKEND_URL", "http://localhost:8000")

PERSONAS = [
    {"full_name": "Shekhar Dudi", "email": "shekhar.dudi@demo.local", "role": "Lead AI Engineer"},
    {"full_name": "Alexis Johnson", "email": "alexis.johnson@demo.local", "role": "Software Engineer"},
    {"full_name": "Erica White", "email": "erica.white@demo.local", "role": "Senior Financial Analyst"},
    {"full_name": "Diana Lopez", "email": "diana.lopez@demo.local", "role": "AI Engineer"},
    {"full_name": "Alyssa Flores", "email": "alyssa.flores@demo.local", "role": "UI Engineer"},
    {"full_name": "Crystal Campbell", "email": "crystal.campbell@demo.local", "role": "UX Designer"},
]

MANAGERS = [
    {"full_name": "Vanshika Puri", "email": "vanshika.puri@demo.local"},
    {"full_name":"Jermy Carpenter", "email": "jermy.carpenter@demo.local"},
]

PAGE_TITLE = "Agentic HR Assistant"
