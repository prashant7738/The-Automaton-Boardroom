import io
import os
import time
import uuid
import zipfile
from concurrent.futures import ThreadPoolExecutor

import streamlit as st
from dotenv import load_dotenv
from langgraph.types import Command

from agency.graph import app as workflow

load_dotenv()

# Streamlit Community Cloud provides hosted values through st.secrets rather than
# a local .env file. Mirror top-level secrets into the environment so the
# workflow and third-party SDKs keep one configuration contract.
try:
    for _name, _value in st.secrets.items():
        os.environ.setdefault(_name, str(_value))
except FileNotFoundError:
    pass

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Automaton Boardroom",
    page_icon="A",
    layout="wide",
)

st.markdown(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Mono:wght@400;500&family=Space+Grotesk:wght@400;500;600;700&display=swap');

:root {
    --ink: #111318;
    --muted: #6f737d;
    --line: #e5e6e8;
    --paper: #f7f7f5;
    --card: #ffffff;
    --coral: #ff6b4a;
    --coral-deep: #d94d31;
    --mint: #c8f2df;
    --blue: #dce8ff;
}

.stApp { background: var(--paper); color: var(--ink); }
[data-testid="stHeader"] { background: rgba(247,247,245,.88); }
[data-testid="stSidebar"] { background: var(--ink); border-right: 0; }
[data-testid="stSidebar"] * { color: #f7f7f5; }
[data-testid="stSidebar"] [data-testid="stCaptionContainer"] p { color: #a7abb4; }
[data-testid="stSidebar"] hr { border-color: #30333a; }
[data-testid="stSidebar"] [data-testid="stVerticalBlockBorderWrapper"] { background: #1b1e24; border-color: #30333a; }
h1, h2, h3, h4, p, label, button, [data-testid="stMetricValue"] { font-family: 'Space Grotesk', sans-serif; }
h1 { letter-spacing: -0.04em; font-weight: 700; font-size: clamp(2.3rem, 5vw, 4.7rem); line-height: .98; }
h2, h3 { letter-spacing: -0.025em; }
[data-testid="stMetric"] { background: var(--card); border: 1px solid var(--line); padding: 1rem 1.1rem; border-radius: 8px; }
[data-testid="stMetricLabel"] { color: var(--muted); font-family: 'DM Mono', monospace; text-transform: uppercase; font-size: .68rem; }
[data-testid="stMetricValue"] { color: var(--ink); }
[data-testid="stTextArea"] textarea, [data-testid="stTextInput"] input { background: var(--card); border: 1px solid #d7d9dd; border-radius: 7px; font-family: 'Space Grotesk', sans-serif; }
[data-testid="stTextArea"] textarea:focus, [data-testid="stTextInput"] input:focus { border-color: var(--coral); box-shadow: 0 0 0 1px var(--coral); }
.stButton > button, .stDownloadButton > button { border-radius: 6px; min-height: 2.7rem; font-weight: 600; border: 1px solid #d7d9dd; }
.stButton > button[kind="primary"], .stDownloadButton > button[kind="primary"] { background: var(--coral); border-color: var(--coral); color: white; }
.stButton > button[kind="primary"]:hover, .stDownloadButton > button[kind="primary"]:hover { background: var(--coral-deep); border-color: var(--coral-deep); }
[data-testid="stExpander"] { background: var(--card); border: 1px solid var(--line); border-radius: 8px; }
[data-testid="stProgressBar"] > div > div { background: var(--coral); }
.eyebrow { color: var(--coral-deep); font: 500 .7rem 'DM Mono', monospace; letter-spacing: .1em; text-transform: uppercase; }
.hero-copy { max-width: 720px; font-size: 1.12rem; color: var(--muted); }
.section-label { color: var(--muted); font: 500 .72rem 'DM Mono', monospace; letter-spacing: .08em; text-transform: uppercase; }
.status-pill { display: inline-block; padding: .35rem .65rem; border-radius: 999px; font: 500 .72rem 'DM Mono', monospace; background: var(--mint); color: #17563e; }
.file-tab { font-family: 'DM Mono', monospace; font-size: .78rem; }
</style>
""",
    unsafe_allow_html=True,
)

# ─── Session State Defaults ────────────────────────────────────────────────────
_DEFAULTS = {
    "phase": "idle",       # idle | running | design_questions | human_review | done | error
    "thread_id": None,
    "future": None,
    "executor": None,
    "interrupt_payload": None,
    "activity_log": [],
    "idea_text": "",
}
for _k, _v in _DEFAULTS.items():
    if _k not in st.session_state:
        st.session_state[_k] = _v


# ─── Helpers ──────────────────────────────────────────────────────────────────
def _cfg() -> dict:
    return {"configurable": {"thread_id": st.session_state.thread_id}}


def _log(msg: str) -> None:
    st.session_state.activity_log.append(msg)


def _get_graph_interrupt():
    """Return (payload, is_finished) from the current LangGraph state."""
    snap = workflow.get_state(_cfg())
    if not snap.next:
        return None, True  # no pending node → workflow finished
    for task in snap.tasks:
        if hasattr(task, "interrupts") and task.interrupts:
            try:
                return task.interrupts[0].value, False
            except IndexError:
                # Background thread may have consumed the interrupt between
                # the truthiness check above and the index access — skip it.
                pass
    return None, False  # running but no interrupt surfaced yet


def _submit_bg(fn, *args) -> None:
    """Submit a blocking LangGraph call to a background thread."""
    if st.session_state.executor is None:
        st.session_state.executor = ThreadPoolExecutor(max_workers=1)
    st.session_state.future = st.session_state.executor.submit(fn, *args)


def _run_initial(initial_state: dict, config: dict) -> None:
    workflow.invoke(initial_state, config)


def _run_resume(command, config: dict) -> None:
    workflow.invoke(command, config)


def _reset() -> None:
    executor = st.session_state.get("executor")
    if executor is not None:
        executor.shutdown(wait=False)
    st.session_state.phase = "idle"
    st.session_state.thread_id = None
    st.session_state.future = None
    st.session_state.executor = None
    st.session_state.interrupt_payload = None
    st.session_state.activity_log = []


def _make_zip(source_files: dict) -> bytes:
    buf = io.BytesIO()
    with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as zf:
        for path, content in source_files.items():
            zf.writestr(path, content)
    return buf.getvalue()


def _language_for_file(filename: str) -> str:
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    return {
        "py": "python", "js": "javascript", "jsx": "javascript", "ts": "typescript",
        "tsx": "typescript", "json": "json", "md": "markdown", "html": "html",
        "css": "css", "toml": "toml", "txt": "text", "yml": "yaml", "yaml": "yaml",
    }.get(extension, "text")


def _has_test_error(test_logs: str) -> bool:
    markers = ("Error", "error", "FAILED", "failed", "exception", "Exception", "SyntaxError", "ModuleNotFoundError", "ImportError")
    return any(marker in test_logs for marker in markers)


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## A / Boardroom")
    st.caption("Autonomous software studio")
    st.divider()

    # Pipeline stage indicator
    stages = [
        ("📋 PM Agent", "Spec"),
        ("🧭 Design Questions", "Design"),
        ("💻 Developer", "Code"),
        ("🧪 Tester", "Test"),
        ("👤 Human Review", "Review"),
        ("📦 Done", "Done"),
    ]
    phase_to_stage = {
        "idle": -1,
        "running": 2,
        "design_questions": 1,
        "human_review": 4,
        "done": 5,
        "error": -1,
    }
    current = phase_to_stage.get(st.session_state.phase, -1)
    st.markdown("<span class='section-label'>Pipeline</span>", unsafe_allow_html=True)
    for i, (label, _) in enumerate(stages):
        if i < current:
            st.markdown(f"<span class='status-pill'>DONE</span> &nbsp; {label}", unsafe_allow_html=True)
        elif i == current:
            st.markdown(f"<span class='status-pill' style='background:#ffd9cf;color:#8d2f1c'>LIVE</span> &nbsp; <b>{label}</b>", unsafe_allow_html=True)
        else:
            st.markdown(f"<span style='color:#666b75'>○ &nbsp; {label}</span>", unsafe_allow_html=True)

    st.divider()

    if st.session_state.activity_log:
        st.markdown("<span class='section-label'>Activity log</span>", unsafe_allow_html=True)
        with st.container(border=True):
            log_container = st.container(height=180)
            with log_container:
                for i, msg in enumerate(st.session_state.activity_log, 1):
                    st.caption(f"{i:02d}  {msg}")

    if st.session_state.phase not in ("idle",):
        st.divider()
        if st.button("Start over", use_container_width=True):
            _reset()
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE: IDLE
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.phase == "idle":
    st.markdown("<div class='eyebrow'>AUTOMATION / 01</div>", unsafe_allow_html=True)
    st.title("Turn an idea into a tested build.")
    st.markdown(
        "<p class='hero-copy'>A coordinated studio of product, design, engineering, and QA agents. "
        "You set the brief. The boardroom handles the build.</p>",
        unsafe_allow_html=True,
    )
    st.divider()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Agents", "5", help="PM · Design Questions · Developer · Tester · Human Review")
    c2.metric("LLM", "Gemini 3.7 Flash", help="Google Gemini API")
    c3.metric("Execution", "E2B Sandbox", help="Isolated, secure code execution")
    c4.metric("Cost", "$0", help="Free developer tiers only")

    st.divider()
    st.markdown("<div class='section-label'>New build brief</div>", unsafe_allow_html=True)
    st.subheader("What should the boardroom make?")

    examples = [
        "A Python script that fetches weather data from Open-Meteo API and prints a 7-day forecast for London",
        "A FastAPI REST API with CRUD endpoints for a todo list backed by an in-memory dict",
        "A React (Vite) counter app with increment, decrement, and reset buttons",
        "A Python script that sorts a list of numbers using bubble sort and prints each step",
    ]

    with st.expander("Browse starting points"):
        for ex in examples:
            if st.button(ex, key=f"ex_{ex[:30]}", use_container_width=True):
                st.session_state.idea_text = ex
                st.rerun()

    idea = st.text_area(
        "Describe your app idea",
        key="idea_text",
        placeholder="e.g. Build a FastAPI REST API with CRUD operations for a todo list",
        height=120,
        max_chars=2000,
        label_visibility="collapsed",
    )

    with st.form("new_build_form", clear_on_submit=False):
        submitted = st.form_submit_button(
            "Start build  →",
            type="primary",
            use_container_width=True,
            disabled=not (idea or "").strip(),
        )

    if submitted:
        thread_id = str(uuid.uuid4())
        st.session_state.thread_id = thread_id
        initial_state = {
            "app_idea": idea.strip(), "specification": "", "source_code": {}, "test_logs": "",
            "iterations": 0, "approved_by_human": False, "human_feedback": "",
            "design_questions": [], "design_answers": {},
        }
        _log(f"Workflow started: {idea.strip()[:80]}")
        _submit_bg(_run_initial, initial_state, _cfg())
        st.session_state.phase = "running"
        st.rerun()

    st.divider()
    st.markdown("<div class='section-label'>The loop</div>", unsafe_allow_html=True)
    st.markdown("**Brief**  →  **Decide**  →  **Build**  →  **Test**  →  **Review**  →  **Ship**")


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE: RUNNING
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.phase == "running":
    st.markdown("<div class='eyebrow'>AUTOMATION / LIVE</div>", unsafe_allow_html=True)
    st.title("The boardroom is working.")
    st.markdown("Agents are turning your brief into a verified project. This can take a few minutes.")

    future = st.session_state.future

    # Check if background thread finished
    if future is not None and future.done():
        exc = future.exception()
        if exc:
            _log(f"Error: {exc}")
            st.session_state.phase = "error"
            st.session_state.interrupt_payload = str(exc)
            st.rerun()

        payload, is_done = _get_graph_interrupt()

        if is_done:
            _log("Workflow completed successfully.")
            st.session_state.phase = "done"
            st.rerun()
        elif payload is not None:
            st.session_state.interrupt_payload = payload
            if payload.get("type") == "design_questions":
                _log("Agents need design decisions.")
                st.session_state.phase = "design_questions"
            else:
                _log("Human review requested.")
                st.session_state.phase = "human_review"
            st.rerun()
        else:
            # Future done but graph still has next nodes and no interrupt — unlikely
            _log("Unexpected state — retrying.")
            st.session_state.phase = "error"
            st.session_state.interrupt_payload = "Unexpected graph state after invocation."
            st.rerun()

    else:
        # Still running — show progress and auto-refresh
        progress_msgs = [
            "📋 PM Agent is analyzing your idea and writing the specification…",
            "🧭 Design reviewer is drafting key build decisions…",
            "💻 Developer Agent is generating code files…",
            "🧪 Tester Agent is spinning up an E2B sandbox…",
            "🔄 Running code and capturing output…",
        ]
        snap_index = int(time.time() / 4) % len(progress_msgs)

        with st.spinner(progress_msgs[snap_index]):
            st.progress(0.66, text="Pipeline active · specification, code, and verification in motion")
            if st.session_state.activity_log:
                st.markdown(f"**Latest signal**  {st.session_state.activity_log[-1]}")

        time.sleep(0.5)
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE: DESIGN QUESTIONS
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.phase == "design_questions":
    st.markdown("<div class='eyebrow'>DECISION GATE / 02</div>", unsafe_allow_html=True)
    st.title("Choose the shape of the build.")
    st.markdown("A few high-impact decisions will steer the developer agent. Pick one answer per question.")
    st.divider()

    payload = st.session_state.interrupt_payload or {}
    design_questions = payload.get("questions", [])

    if not design_questions:
        _log("No design decisions required — resuming.")
        _submit_bg(_run_resume, Command(resume={}), _cfg())
        st.session_state.phase = "running"
        st.rerun()

    with st.form("design_questions_form"):
        answers = {}
        for idx, q in enumerate(design_questions, 1):
            qid = q.get("id", "q")
            question = q.get("question", qid)
            options = q.get("options", [])
            st.markdown(f"<div class='section-label'>Decision {idx:02d} / {len(design_questions):02d}</div>", unsafe_allow_html=True)
            answers[qid] = st.radio(question, options, key=f"dq_{qid}", label_visibility="collapsed")
            st.divider()

        col1, col2 = st.columns([3, 1])
        with col1:
            st.empty()
        with col2:
            submitted = st.form_submit_button("Lock decisions  →", type="primary", use_container_width=True)

    if submitted:
        _log(f"Design decisions collected: {list(answers.keys())}")
        _submit_bg(_run_resume, Command(resume=answers), _cfg())
        st.session_state.phase = "running"
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE: HUMAN REVIEW
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.phase == "human_review":
    st.markdown("<div class='eyebrow'>SIGN-OFF / 05</div>", unsafe_allow_html=True)
    st.title("Your review is the final gate.")
    payload = st.session_state.interrupt_payload or {}

    snap = workflow.get_state(_cfg())
    final = snap.values

    iterations = final.get("iterations", 0)
    st.markdown(
        f"The agents completed **{iterations} iteration(s)**. Review the output, then approve delivery or send one focused revision note."
    )

    # ── Code viewer ────────────────────────────────────────────────────────────
    source_files = final.get("source_code", {})
    if source_files:
        st.markdown(f"<div class='section-label'>Generated files · {len(source_files)}</div>", unsafe_allow_html=True)
        tabs = st.tabs(list(source_files.keys()))
        for tab, (fname, content) in zip(tabs, source_files.items()):
            with tab:
                file_size = len(content.encode())
                st.caption(f"{fname} · {file_size:,} bytes")
                st.code(content, language=_language_for_file(fname), line_numbers=True)

    # ── Test logs ──────────────────────────────────────────────────────────────
    test_logs = final.get("test_logs", "")
    if test_logs:
        st.subheader("Verification")
        has_error = _has_test_error(test_logs)
        if has_error:
            st.warning("Errors were detected. A revision can be sent back to the developer.")
        else:
            st.success("All tests passed.")
        with st.expander(f"📋 Full Logs ({len(test_logs):,} chars)", expanded=False):
            st.code(test_logs, language="text")

    st.divider()

    # ── Approval controls ──────────────────────────────────────────────────────
    st.subheader("Decision")
    with st.form("review_form"):
        reject_reason = st.text_input(
            "Revision note",
            placeholder="Optional for approval. For revision: e.g. Add authentication to the API.",
            max_chars=500,
        )
        col_approve, col_reject = st.columns(2)
        with col_approve:
            approve = st.form_submit_button("Approve & deliver  →", type="primary", use_container_width=True)
        with col_reject:
            reject = st.form_submit_button("Send revision note", use_container_width=True)

    if approve:
            _log("Human approved the output.")
            _submit_bg(_run_resume, Command(resume="yes"), _cfg())
            st.session_state.phase = "running"
            st.rerun()
    elif reject and reject_reason.strip():
        _log(f"Human rejected: {reject_reason.strip()[:80]}")
        _submit_bg(_run_resume, Command(resume=reject_reason.strip()), _cfg())
        st.session_state.phase = "running"
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE: DONE
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.phase == "done":
    st.markdown("<div class='eyebrow'>DELIVERY / COMPLETE</div>", unsafe_allow_html=True)
    st.title("Your build is ready.")
    st.markdown("The reviewed project has been packaged and is ready to leave the boardroom.")
    st.balloons()

    snap = workflow.get_state(_cfg())
    final = snap.values

    approved = final.get("approved_by_human", False)
    iterations = final.get("iterations", 0)
    source_files = final.get("source_code", {})
    test_logs = final.get("test_logs", "")

    col1, col2, col3 = st.columns(3)
    col1.metric("Status", "Approved" if approved else "Completed", help="Human approval status")
    col2.metric("Iterations", iterations, help="Dev → Test cycles used")
    col3.metric("Files Generated", len(source_files))

    st.divider()

    # ── Download zip ───────────────────────────────────────────────────────────
    if source_files:
        zip_bytes = _make_zip(source_files)
        st.download_button(
            label="Download project ZIP  ↓",
            data=zip_bytes,
            file_name="automaton_output.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True,
        )

    st.divider()

    # ── Code viewer ────────────────────────────────────────────────────────────
    if source_files:
        st.markdown(f"<div class='section-label'>Generated files · {len(source_files)}</div>", unsafe_allow_html=True)
        tabs = st.tabs(list(source_files.keys()))
        for tab, (fname, content) in zip(tabs, source_files.items()):
            with tab:
                file_size = len(content.encode())
                st.caption(f"{fname} · {file_size:,} bytes")
                st.code(content, language=_language_for_file(fname), line_numbers=True)

    # ── Test logs ──────────────────────────────────────────────────────────────
    if test_logs:
        with st.expander(f"🧪 Test Logs ({len(test_logs):,} chars)", expanded=False):
            st.code(test_logs, language="text")

    st.divider()
    if st.button("Build another app", use_container_width=True):
        _reset()
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE: ERROR
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.phase == "error":
    st.markdown("<div class='eyebrow'>SYSTEM / RECOVERY</div>", unsafe_allow_html=True)
    st.title("The run needs attention.")
    err = st.session_state.interrupt_payload or "An unknown error occurred."
    st.error(err)

    st.markdown("**Common causes**")
    st.markdown(
        "- Invalid or missing API key (check your `.env` file)\n"
        "- E2B sandbox quota exhausted (100 hrs/month free tier)\n"
        "- Groq / Gemini rate limit hit\n"
        "- Network timeout during sandbox execution"
    )

    if st.button("Reset and try again  →", type="primary", use_container_width=True):
        _reset()
        st.rerun()
