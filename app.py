from dotenv import load_dotenv
load_dotenv()

import streamlit as st
import uuid
import zipfile
import io
import time
from concurrent.futures import ThreadPoolExecutor

from langgraph.types import Command
from agency.graph import app as workflow

# ─── Page Config ──────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="The Automaton Boardroom",
    page_icon="🤖",
    layout="wide",
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


# ─── Sidebar ──────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("## 🤖 Automaton Boardroom")
    st.caption("Autonomous Multi-Agent Software Factory")
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
    st.markdown("**Pipeline**")
    for i, (label, _) in enumerate(stages):
        if i < current:
            st.markdown(f"✅ {label}")
        elif i == current:
            st.markdown(f"⏳ **{label}**")
        else:
            st.markdown(f"⬜ {label}")

    st.divider()

    if st.session_state.activity_log:
        st.markdown("**Activity Log**")
        with st.container(border=True):
            log_container = st.container(height=180)
            with log_container:
                for i, msg in enumerate(st.session_state.activity_log, 1):
                    st.caption(f"{i}. {msg}")

    if st.session_state.phase not in ("idle",):
        st.divider()
        if st.button("🔄 Start Over", use_container_width=True):
            _reset()
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE: IDLE
# ═══════════════════════════════════════════════════════════════════════════════
if st.session_state.phase == "idle":
    st.title("🚀 The Automaton Boardroom")
    st.markdown(
        "*An autonomous multi-agent software factory — powered by **LangGraph**, "
        "**Gemini / Groq**, and **E2B** secure sandboxes.*"
    )
    st.divider()

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Agents", "5", help="PM · Design Questions · Developer · Tester · Human Review")
    c2.metric("LLM", "Groq + Gemini", help="Groq primary, Gemini fallback")
    c3.metric("Execution", "E2B Sandbox", help="Isolated, secure code execution")
    c4.metric("Cost", "$0", help="Free developer tiers only")

    st.divider()
    st.subheader("What app do you want to build?")

    examples = [
        "A Python script that fetches weather data from Open-Meteo API and prints a 7-day forecast for London",
        "A FastAPI REST API with CRUD endpoints for a todo list backed by an in-memory dict",
        "A React (Vite) counter app with increment, decrement, and reset buttons",
        "A Python script that sorts a list of numbers using bubble sort and prints each step",
    ]

    with st.expander("💡 Example Ideas — click to use"):
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

    if st.button(
        "🚀 Build It",
        type="primary",
        use_container_width=True,
        disabled=not (idea or "").strip(),
    ):
        thread_id = str(uuid.uuid4())
        st.session_state.thread_id = thread_id

        initial_state = {
            "app_idea": idea.strip(),
            "specification": "",
            "source_code": {},
            "test_logs": "",
            "iterations": 0,
            "approved_by_human": False,
            "human_feedback": "",
            "design_questions": [],
            "design_answers": {},
        }

        _log(f"Workflow started: {idea.strip()[:80]}")
        _submit_bg(_run_initial, initial_state, _cfg())
        st.session_state.phase = "running"
        st.rerun()

    st.divider()
    st.markdown(
        "**How it works:** "
        "1) PM writes a technical spec → "
        "2) Design Questions MCQ narrows scope/features → "
        "3) Developer writes code honoring those choices → "
        "4) Tester runs it in E2B sandbox → "
        "5) Errors auto-loop back to Developer (up to 5 times) → "
        "6) You review and approve the final output."
    )


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE: RUNNING
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.phase == "running":
    st.title("⚙️ Agents at Work…")
    st.markdown("The pipeline is running. This may take a few minutes while the E2B sandbox executes your code.")

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
            st.info(
                "⏳ Working… Typical completion time: 1–4 minutes. "
                "LangSmith tracing is active if configured.",
                icon="🔬",
            )
            if st.session_state.activity_log:
                st.caption(f"Last: {st.session_state.activity_log[-1]}")

        time.sleep(0.5)
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE: DESIGN QUESTIONS
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.phase == "design_questions":
    st.title("🧭 Design Decisions")
    st.markdown(
        "Choose options for key build decisions. Your choices will guide the Developer agent.  "
        "*(All choices are single-select; no free-text input.)*"
    )
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
            st.markdown(f"**Question {idx} of {len(design_questions)}**")
            answers[qid] = st.radio(question, options, key=f"dq_{qid}", label_visibility="collapsed")
            st.divider()

        col1, col2 = st.columns([3, 1])
        with col1:
            st.empty()
        with col2:
            submitted = st.form_submit_button("✅ Submit", type="primary", use_container_width=True)

    if submitted:
        _log(f"Design decisions collected: {list(answers.keys())}")
        _submit_bg(_run_resume, Command(resume=answers), _cfg())
        st.session_state.phase = "running"
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE: HUMAN REVIEW
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.phase == "human_review":
    st.title("👤 Human Review")
    payload = st.session_state.interrupt_payload or {}

    snap = workflow.get_state(_cfg())
    final = snap.values

    iterations = final.get("iterations", 0)
    st.markdown(
        f"The agents have finished after **{iterations} iteration(s)**. "
        "Review the generated code and test results below."
    )

    # ── Code viewer ────────────────────────────────────────────────────────────
    source_files = final.get("source_code", {})
    if source_files:
        st.subheader(f"📁 Generated Files ({len(source_files)})")
        tabs = st.tabs(list(source_files.keys()))
        for tab, (fname, content) in zip(tabs, source_files.items()):
            with tab:
                ext = fname.rsplit(".", 1)[-1] if "." in fname else "text"
                lang_map = {
                    "py": "python", "js": "javascript", "jsx": "javascript",
                    "ts": "typescript", "tsx": "typescript", "json": "json",
                    "md": "markdown", "html": "html", "css": "css",
                    "toml": "toml", "txt": "text", "yml": "yaml", "yaml": "yaml",
                }
                # Show file info
                file_size = len(content.encode())
                st.caption(f"📄 {fname} · {file_size:,} bytes")
                st.code(content, language=lang_map.get(ext, "text"), line_numbers=True)

    # ── Test logs ──────────────────────────────────────────────────────────────
    test_logs = final.get("test_logs", "")
    if test_logs:
        st.subheader("🧪 Test Logs")
        has_error = any(
            kw in test_logs
            for kw in ("Error", "error", "FAILED", "failed", "exception", "Exception",
                       "SyntaxError", "ModuleNotFoundError", "ImportError")
        )
        if has_error:
            st.warning("⚠️ Errors were detected — the Developer will auto-correct on revision.", icon="⚠️")
        else:
            st.success("✅ All tests passed!", icon="✅")
        with st.expander(f"📋 Full Logs ({len(test_logs):,} chars)", expanded=False):
            st.code(test_logs, language="text")

    st.divider()

    # ── Approval controls ──────────────────────────────────────────────────────
    st.subheader("Decision")
    col_approve, col_reject = st.columns(2)

    with col_approve:
        if st.button("✅ Approve & Deliver", type="primary", use_container_width=True):
            _log("Human approved the output.")
            _submit_bg(_run_resume, Command(resume="yes"), _cfg())
            st.session_state.phase = "running"
            st.rerun()

    with col_reject:
        reject_reason = st.text_input(
            "What needs to be fixed? (optional feedback to Developer)",
            placeholder="e.g. The API is missing authentication",
            label_visibility="collapsed",
            max_chars=500,
        )
        if st.button(
            "🔁 Reject & Revise",
            use_container_width=True,
            disabled=not reject_reason.strip(),
        ):
            _log(f"Human rejected: {reject_reason.strip()[:80]}")
            _submit_bg(_run_resume, Command(resume=reject_reason.strip()), _cfg())
            st.session_state.phase = "running"
            st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE: DONE
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.phase == "done":
    st.title("📦 Delivery Complete")
    st.balloons()

    snap = workflow.get_state(_cfg())
    final = snap.values

    approved = final.get("approved_by_human", False)
    iterations = final.get("iterations", 0)
    source_files = final.get("source_code", {})
    test_logs = final.get("test_logs", "")

    col1, col2, col3 = st.columns(3)
    col1.metric("Status", "✅ Approved" if approved else "⚠️ Completed", help="Human approval status")
    col2.metric("Iterations", iterations, help="Dev → Test cycles used")
    col3.metric("Files Generated", len(source_files))

    st.divider()

    # ── Download zip ───────────────────────────────────────────────────────────
    if source_files:
        zip_bytes = _make_zip(source_files)
        st.download_button(
            label="⬇️ Download Project ZIP",
            data=zip_bytes,
            file_name="automaton_output.zip",
            mime="application/zip",
            type="primary",
            use_container_width=True,
        )

    st.divider()

    # ── Code viewer ────────────────────────────────────────────────────────────
    if source_files:
        st.subheader(f"📁 Generated Files ({len(source_files)})")
        tabs = st.tabs(list(source_files.keys()))
        for tab, (fname, content) in zip(tabs, source_files.items()):
            with tab:
                ext = fname.rsplit(".", 1)[-1] if "." in fname else "text"
                lang_map = {
                    "py": "python", "js": "javascript", "jsx": "javascript",
                    "ts": "typescript", "tsx": "typescript", "json": "json",
                    "md": "markdown", "html": "html", "css": "css",
                    "toml": "toml", "txt": "text", "yml": "yaml", "yaml": "yaml",
                }
                # Show file info
                file_size = len(content.encode())
                st.caption(f"📄 {fname} · {file_size:,} bytes")
                st.code(content, language=lang_map.get(ext, "text"), line_numbers=True)

    # ── Test logs ──────────────────────────────────────────────────────────────
    if test_logs:
        with st.expander(f"🧪 Test Logs ({len(test_logs):,} chars)", expanded=False):
            st.code(test_logs, language="text")

    st.divider()
    if st.button("🔄 Build Another App", use_container_width=True):
        _reset()
        st.rerun()


# ═══════════════════════════════════════════════════════════════════════════════
# PHASE: ERROR
# ═══════════════════════════════════════════════════════════════════════════════
elif st.session_state.phase == "error":
    st.title("❌ Something Went Wrong")
    err = st.session_state.interrupt_payload or "An unknown error occurred."
    st.error(err)

    st.markdown("**Possible causes:**")
    st.markdown(
        "- Invalid or missing API key (check your `.env` file)\n"
        "- E2B sandbox quota exhausted (100 hrs/month free tier)\n"
        "- Groq / Gemini rate limit hit\n"
        "- Network timeout during sandbox execution"
    )

    if st.button("🔄 Try Again", type="primary", use_container_width=True):
        _reset()
        st.rerun()
