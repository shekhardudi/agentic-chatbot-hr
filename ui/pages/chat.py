import uuid
import warnings
import streamlit as st

# Suppress the deprecation warning — components.v1.html is needed for JS execution
with warnings.catch_warnings():
    warnings.filterwarnings("ignore", message=".*st\.components\.v1\.html.*")
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
        "Can I get Mattermost access?",
        "I want access to Gitea and Mattermost",
    ],
    "📦 Access Request Status": [
        "What's the status of my access requests?",
        "Did my Gitea request get approved?",
        "Did my Mattermost request get approved?",
    ],
}

# ---------------------------------------------------------------------------
# Guide content
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
"""

TIPS = """
**Switching Personas**
Use the sidebar dropdown to test as different employees. \
Each persona has its own leave balances, manager, and \
access packages.

**Apply for Leave**
Say *"I want to take 3 days annual leave"*. If you omit \
the type or duration the assistant will ask one follow-up \
question before submitting.

**Check Access Requests**
Ask *"What's the status of my Gitea request?"* for a \
specific system, or *"Show all my requests"* for everything.

**Manager Approvals**
Open the **Manager Approvals** page to approve or deny \
pending software-access requests. Provisioning in Gitea \
and Mattermost runs automatically once approved.

**Policy Citations**
Policy answers include the source document and section. \
Ask follow-up questions — the assistant rewrites and \
re-searches on each turn.

**Integrated Systems**
The sidebar links take you directly to the live NocoDB, \
Gitea, and Mattermost instances that back every response.
Check Agentic_hr in Nocodb
Check usersin Gitea
Check Team Members in Mattermost
"""

# --- Title row with guide-panel toggle ---
_title_left, _title_right = st.columns([6, 1])
with _title_left:
    st.title("HR/IT Provisioning Assistant")
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
            "url": "/nocodb/",
        },
        {
            "name": "Gitea",
            "icon": "🔀",
            "category": "Version Control",
            "desc": "Git service hosting policy docs & HR workflow configs",
            "url": "/gitea/",
        },
        {
            "name": "Mattermost",
            "icon": "💬",
            "category": "Team Collaboration",
            "desc": "Messaging hub for approvals, notifications & team comms",
            "url": "/mattermost/",
        },
    ]

    cards_html = '<div style="margin-top:8px;"><strong style="font-size:1.05rem;">Integrated Systems</strong><br><span style="font-size:0.9rem; color:#d4d4d4;">(Click and checkout)</span></div>'
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
    cards_html += '<div style="font-size:0.75rem; color:#fff; margin-top:8px; padding-top:5px; border-top:1px solid #d4d4d4;">🔒 Self-signed authentication—pages may take a few seconds to load.</div>'
    st.markdown(cards_html, unsafe_allow_html=True)

# --- Session state init ---
if "chat_history" not in st.session_state:
    st.session_state["chat_history"] = []
if "session_id" not in st.session_state:
    st.session_state["session_id"] = str(uuid.uuid4())
if "employee_email" not in st.session_state:
    st.session_state["employee_email"] = PERSONAS[0]["email"]

# ---------------------------------------------------------------------------
# Message processing
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
    # Signal that the page should scroll to bottom on next render
    st.session_state["_scroll_to_bottom"] = True

# Capture chat_input — always at page level so Streamlit pins it to bottom
user_input = st.chat_input("Ask an HR/IT Provisioning question…")

# ---------------------------------------------------------------------------
# Layout: chat column + optional fixed guide panel
# ---------------------------------------------------------------------------
_guide_open = st.session_state.get("show_guide", True)

if _guide_open:
    st.markdown(
        """<style>
        /* Right panel: fixed to viewport — does not scroll with the page */
        section[data-testid="stMain"] [data-testid="stColumn"]:nth-child(2) {
            position: fixed !important;
            right: 0;
            top: 3.5rem;
            width: 24% !important;
            max-width: 24% !important;
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
        /* Keep chat input within the chat column (left 3/4) */
        .stChatInput { max-width: 75%; }
        /* Ensure left chat column scrolls independently */
        section[data-testid="stMain"] [data-testid="stColumn"]:nth-child(1) {
            max-width: 75% !important;
        }
        </style>""",
        unsafe_allow_html=True,
    )
    chat_col, info_col = st.columns([3, 1], gap="medium")
else:
    chat_col = st.container()
    info_col = None

# --- Chat history ---
with chat_col:
    for msg in st.session_state["chat_history"]:
        message_bubble(msg["role"], msg["content"], msg.get("citations"))
        if msg.get("status") and msg.get("request_id"):
            status_badge(msg["status"], msg.get("request_id"))

    # Invisible anchor at the bottom of chat — always scroll into view
    if st.session_state.get("chat_history"):
        st.markdown(
            '<div id="chat-anchor" style="height:1px;"></div>',
            unsafe_allow_html=True,
        )
        components.html("""<script>
            const anchor = parent.document.getElementById('chat-anchor');
            if (anchor) {
                anchor.scrollIntoView({ block: 'start' });
            }
        </script>""", height=0)

    if user_input:
        # Show the user's message immediately
        message_bubble("user", user_input)
        # Place anchor after user message, scroll to it to show spinner
        st.markdown(
            '<div id="input-anchor" style="height:1px;"></div>',
            unsafe_allow_html=True,
        )
        components.html("""<script>
            var a = parent.document.getElementById('input-anchor');
            if (a) a.scrollIntoView({ block: 'start' });
        </script>""", height=0)
        with st.spinner("Thinking…"):
            _process_message(user_input)
        st.rerun()

# --- Guide panel (fixed right sidebar) ---
if info_col is not None:
    with info_col:
        tab_examples, tab_howto, tab_tips = st.tabs(["🧪 Try It Out", "📖 How It Works", "💡 Tips"])

        with tab_examples:
            for category, queries in EXAMPLE_QUERIES.items():
                with st.expander(category):
                    for q in queries:
                        if st.button(q, key=f"ex_{q}", use_container_width=True):
                            st.session_state["_prefill_query"] = q
                            st.rerun()

        with tab_howto:
            st.markdown(HOW_IT_WORKS)

        with tab_tips:
            st.markdown(TIPS)

# ---------------------------------------------------------------------------
# JS: populate chat input when a "Try It Out" example is clicked
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

# ---------------------------------------------------------------------------
# Clear scroll flag if set (scrolling now handled inline after chat render)
# ---------------------------------------------------------------------------
st.session_state.pop("_scroll_to_bottom", None)
