import uuid
import streamlit as st
import streamlit.components.v1 as components

from config import PERSONAS, PAGE_TITLE, SERVICE_HOST
from api_client import send_message
from components.persona_selector import persona_selector
from components.message_bubble import message_bubble, status_badge

# ---------------------------------------------------------------------------
# Example queries grouped by use-case
# ---------------------------------------------------------------------------
EXAMPLE_QUERIES = {
    "📋 Leave Balance": [
        "How many annual leave days do I have?",
        "Show me all my leave balances",
        "What is my sick leave balance?",
    ],
    "✈️ Apply for Leave": [
        "I want to apply for 3 days of annual leave",
        "I need to take 2 days of sick leave",
        "Can I take 8 hours of personal leave?",
    ],
    "📖 Policy Questions": [
        "What is the travel expense reimbursement limit?",
        "How does the notice period work?",
        "What are the office timings?",
    ],
    "🔧 Software Access": [
        "I need access to Gitea",
        "Can I get Mattermost access for my team?",
        "I want access to Gitea and Mattermost",
    ],
    "📦 Access Request Status": [
        "What's the status of my access requests?",
        "Did my Gitea request get approved?",
        "Check status of request AR-0001",
    ],
}

# ---------------------------------------------------------------------------
# How-it-works content
# ---------------------------------------------------------------------------
HOW_IT_WORKS = """
This is an **agentic HR assistant** powered by a \
LangGraph state-machine. Each query flows through \
a multi-step pipeline:

**1 — Intent Detection**
Your message is classified into one of the supported \
intents by an LLM triage agent.

**2 — Employee Resolution**
Your persona is looked up in NocoDB to fetch your \
employee profile and team info.

**3 — Specialised Processing**
Based on intent, the request is routed to a dedicated \
pipeline:

- **Leave Balance** — Fetches leave data from NocoDB \
and formats balances by type.
- **Apply for Leave** — Collects leave type & duration, \
calculates hours (1 day = 8 hrs), validates against \
your balance, and updates NocoDB.
- **Policy Query** — Rewrites your query, retrieves \
matching chunks from pgvector, grades evidence, and \
synthesises an answer with citations.
- **Software Access** — Maps to access packages, checks \
eligibility, creates a Postgres request, provisions \
accounts via Gitea / Mattermost APIs.
- **Access Status** — Queries Postgres for your requests \
joined with package details.

**4 — Response Composition**
Output is formatted into a Markdown-rich response \
with citations where applicable.

**5 — Audit Trail**
Every interaction is logged with intent, status, \
and timing metadata.

---

**Tips**
- Switch personas in the sidebar to test as \
different employees.
- Use **Manager Approvals** to approve / deny \
pending software-access requests.
- Integrated systems (NocoDB, Gitea, Mattermost) \
are linked in the sidebar.
"""

# --- Title row with guide-panel toggle ---
_title_left, _title_right = st.columns([6, 1])
with _title_left:
    st.title("HR Assistant")
with _title_right:
    st.markdown("<div style='height:0.6rem'></div>", unsafe_allow_html=True)
    st.toggle("📖 Guide", value=True, key="show_guide")

# --- Sidebar: persona selector ---
with st.sidebar:
    st.header("Employee Persona")
    persona = persona_selector(PERSONAS)
    st.divider()
    st.caption(f"Email: `{persona['email']}`")
    if st.button("New conversation"):
        st.session_state.pop("chat_history", None)
        st.session_state.pop("session_id", None)
        st.rerun()

    TOOLS = [
        {
            "name": "NocoDB",
            "icon": "🗄️",
            "category": "HR Data Platform",
            "desc": "No-code database powering employee records & leave tracking",
            "url": f"http://{SERVICE_HOST}:8080",
        },
        {
            "name": "Gitea",
            "icon": "🔀",
            "category": "Version Control",
            "desc": "Git service hosting policy docs & HR workflow configs",
            "url": f"http://{SERVICE_HOST}:3000",
        },
        {
            "name": "Mattermost",
            "icon": "💬",
            "category": "Team Collaboration",
            "desc": "Messaging hub for approvals, notifications & team comms",
            "url": f"http://{SERVICE_HOST}:8065",
        },
    ]

    cards_html = '<div style="margin-top:8px;"><strong style="font-size:0.95rem;">Integrated Systems (Click and checkout):</strong></div>'
    for tool in TOOLS:
        cards_html += f"""<a href="{tool['url']}" target="_blank" style="
            text-decoration:none; color:inherit; display:block;
            border:1px solid #444; border-radius:6px;
            padding:6px 8px; margin-top:5px;">
            <div style="display:flex; align-items:center; gap:6px;">
                <span style="font-size:1.05rem;">{tool['icon']}</span>
                <div style="line-height:1.3;">
                    <strong style="font-size:0.82rem;">{tool['name']}</strong>
                    <span style="background:#555; color:#eee; font-size:0.58rem;
                        padding:1px 5px; border-radius:3px; margin-left:4px;
                        vertical-align:middle;">{tool['category']}</span>
                    <div style="font-size:0.7rem; color:#999; margin-top:1px;">
                        {tool['desc']}
                    </div>
                </div>
            </div>
        </a>"""
    st.markdown(cards_html, unsafe_allow_html=True)

# --- Session state init ---
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())
if "employee_email" not in st.session_state:
    st.session_state["employee_email"] = PERSONAS[0]["email"]

# ---------------------------------------------------------------------------
# Process input BEFORE rendering columns so messages appear inside chat_col
# ---------------------------------------------------------------------------
def _process_message(text: str) -> None:
    """Send a message to the backend and append both user + assistant msgs."""
    st.session_state["chat_history"].append({"role": "user", "content": text})
    try:
        response = send_message(
            employee_email=st.session_state["employee_email"],
            message=text,
            session_id=st.session_state["session_id"],
        )
        st.session_state["chat_history"].append({
            "role": "assistant",
            "content": response.get("response", ""),
            "citations": response.get("citations", []),
            "status": response.get("status"),
            "request_id": response.get("request_id"),
        })
    except Exception as e:
        st.session_state["chat_history"].append({
            "role": "assistant",
            "content": f"⚠️ Backend error: {e}",
        })

# Capture chat_input (always at page level so Streamlit pins it to bottom)
user_input = st.chat_input("Ask an HR question…")

# ---------------------------------------------------------------------------
# Layout: chat + optional guide panel (collapsible right sidebar)
# ---------------------------------------------------------------------------
_guide_open = st.session_state.get("show_guide", True)

if _guide_open:
    st.markdown(
        """<style>
        /* right-panel: fixed sidebar pinned to viewport */
        section[data-testid="stMain"] [data-testid="stColumn"]:nth-child(2) {
            position: fixed !important;
            right: 0;
            top: 3.5rem;
            width: 24% !important;
            height: calc(100vh - 3.5rem);
            overflow-y: auto;
            border-left: 1px solid rgba(250,250,250,0.08);
            padding: 0 1rem 1rem 1.2rem;
            background: var(--background-color);
            z-index: 50;
        }
        section[data-testid="stMain"] [data-testid="stColumn"]:nth-child(2)::-webkit-scrollbar {
            width: 4px;
        }
        section[data-testid="stMain"] [data-testid="stColumn"]:nth-child(2)::-webkit-scrollbar-thumb {
            background: #555; border-radius: 2px;
        }
        /* constrain chat input to the chat column width (3/4 of main) */
        .stChatInput {
            max-width: 75%;
        }
        </style>""",
        unsafe_allow_html=True,
    )
    chat_col, info_col = st.columns([3, 1], gap="medium")
else:
    chat_col = st.container()
    info_col = None

# --- Chat history + inline spinner ---
with chat_col:
    for msg in st.session_state["chat_history"]:
        message_bubble(msg["role"], msg["content"], msg.get("citations"))
        if msg.get("status") and msg.get("request_id"):
            status_badge(msg["status"], msg.get("request_id"))

    # Process new input inside chat_col so spinner appears below the last message
    if user_input:
        with st.spinner("Thinking…"):
            _process_message(user_input)
        st.rerun()

# --- Guide panel (right sidebar) ---
if info_col is not None:
    with info_col:
        tab_examples, tab_howto = st.tabs(["🧪 Try It Out", "📖 How It Works"])

        with tab_examples:
            for category, queries in EXAMPLE_QUERIES.items():
                with st.expander(category):
                    for q in queries:
                        if st.button(q, key=f"ex_{q}", use_container_width=True):
                            st.session_state["_prefill_query"] = q
                            st.rerun()

        with tab_howto:
            st.markdown(HOW_IT_WORKS)

# ---------------------------------------------------------------------------
# JS injection: populate chat input when an example query was clicked
# ---------------------------------------------------------------------------
if st.session_state.get("_prefill_query"):
    _prefill = st.session_state.pop("_prefill_query")
    _safe = _prefill.replace("\\", "\\\\").replace("'", "\\'")
    components.html(f"""<script>
        const el = parent.document.querySelector(
            'textarea[data-testid="stChatInputTextArea"]');
        if (el) {{
            const setter = Object.getOwnPropertyDescriptor(
                window.HTMLTextAreaElement.prototype, 'value').set;
            setter.call(el, '{_safe}');
            el.dispatchEvent(new Event('input', {{ bubbles: true }}));
            el.focus();
        }}
    </script>""", height=0)
