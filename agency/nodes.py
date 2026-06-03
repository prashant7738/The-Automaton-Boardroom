from typing import Annotated , TypedDict, Dict
from typing_extensions import Literal
import os
import json
import re
import time
from dotenv import load_dotenv
import traceback

from .states import AgencyState

# Load environment variables from .env file
load_dotenv()

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq



from e2b import Sandbox
from e2b.sandbox.commands.command_handle import CommandExitException
from langgraph.types import interrupt

from langsmith import traceable



def model(prompt,temperature = 0.3):

    try:
        llm = ChatGroq(
            model="llama-3.3-70b-versatile",
            temperature=temperature,
            api_key=os.getenv('GROQ_API_KEY')
        )

        return llm.invoke(prompt)
    
    except Exception as e:
        print(f"groq doesnt get called due to {e}. Now gemini ....")
        llm = ChatGoogleGenerativeAI(
            model="gemini-2.0-flash",
            temperature = temperature,
            api_key=os.getenv('GOOGLE_API_KEY')
            )
        return llm.invoke(prompt)

       

@traceable
def pm_node(state: AgencyState) -> Dict:
    prompt = f"""You are a Product Manager. Create technical specs for this app idea:
    Idea : {state['app_idea']}
    Provide the required markdown file structures and implementation logic.
    """

    response = model(prompt)

    return{"specification":response.content}


@traceable
def input_collector_node(state: AgencyState) -> Dict:
    prompt = f"""Analyze this app idea and specification. Identify all user inputs needed to run the program.
    App idea: {state['app_idea']}
    Specification: {state['specification']}

    Return ONLY a valid JSON array. Each element must have:
    - "name": Python variable name (snake_case, no spaces)
    - "type": one of int / float / str
    - "description": short human-readable prompt to ask the user

    Example: [{{"name": "num1", "type": "float", "description": "First number"}}, ...]
    If no inputs are needed, return [].
    Return ONLY the JSON array, no markdown, no extra text.
    """

    response = model(prompt, temperature=0.0)
    content = response.content.strip()

    match = re.search(r'\[.*\]', content, re.DOTALL)
    required_inputs = json.loads(match.group()) if match else []

    user_inputs = {}
    if required_inputs:
        user_inputs = interrupt({
            "type": "input_request",
            "inputs": required_inputs,
        })

    return {"required_inputs": required_inputs, "user_inputs": user_inputs}


# ---------------------------------------------------------------------------
# Sandbox helpers
# ---------------------------------------------------------------------------

def _install_python_deps(sandbox, source_files: dict) -> str:
    """Install Python deps from requirements.txt or pyproject.toml. Return log."""
    if "requirements.txt" in source_files:
        r = sandbox.commands.run("pip install -r requirements.txt 2>&1", timeout=120)
        return (r.stdout or r.stderr or "")[:800]
    if "pyproject.toml" in source_files:
        r = sandbox.commands.run("pip install -e . 2>&1", timeout=120)
        return (r.stdout or r.stderr or "")[:800]
    return ""


def _wait_for_port(sandbox, port: int, retries: int = 15, delay: float = 1.5) -> bool:
    """Poll until HTTP server responds on given port inside sandbox."""
    for _ in range(retries):
        try:
            check = sandbox.commands.run(
                f"curl -s http://127.0.0.1:{port}/ -o /dev/null -w '%{{http_code}}'",
                timeout=5,
            )
            if check.stdout.strip() in ("200", "301", "302", "404", "405", "422"):
                return True
        except Exception:
            pass
        time.sleep(delay)
    return False


def _run_python_script(sandbox, source_files: dict) -> str:
    entry = "main.py" if "main.py" in source_files else next(
        (f for f in source_files if f.endswith(".py")), None
    )
    if not entry:
        return "No Python entry point found."
    try:
        result = sandbox.commands.run(f"python {entry} 2>&1", timeout=30)
        out = result.stderr if result.stderr else result.stdout
        return out or f"Exit code: {result.exit_code}. No output."
    except CommandExitException as e:
        return str(e)


def _run_fastapi(sandbox, source_files: dict) -> str:
    logs = []
    install_log = _install_python_deps(sandbox, source_files)
    if install_log:
        logs.append(f"[install]\n{install_log}")

    # Locate the file containing FastAPI() and extract app var name
    entry_module, app_var = "main", "app"
    for fname, content in source_files.items():
        if fname.endswith(".py") and "FastAPI(" in content:
            entry_module = fname.replace(".py", "").replace("/", ".")
            m = re.search(r'(\w+)\s*=\s*FastAPI\(', content)
            if m:
                app_var = m.group(1)
            break

    start_cmd = (
        f"nohup uvicorn {entry_module}:{app_var} "
        f"--host 0.0.0.0 --port 8000 > /tmp/server.log 2>&1 & echo $!"
    )
    proc = sandbox.commands.run(start_cmd, timeout=10)
    pid = proc.stdout.strip()

    ready = _wait_for_port(sandbox, 8000)
    logs.append(f"[server ready: {ready}]")

    if ready:
        for endpoint in ["/", "/docs", "/openapi.json"]:
            r = sandbox.commands.run(
                f"curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:8000{endpoint}",
                timeout=10,
            )
            logs.append(f"GET {endpoint} -> {r.stdout.strip()}")

    server_log = sandbox.commands.run("cat /tmp/server.log 2>&1", timeout=5)
    logs.append(f"[server log]\n{(server_log.stdout or '')[-2000:]}")

    if pid:
        sandbox.commands.run(f"kill {pid} 2>/dev/null || true", timeout=5)
    return "\n".join(logs)


def _run_django(sandbox, source_files: dict) -> str:
    logs = []
    install_log = _install_python_deps(sandbox, source_files)
    if install_log:
        logs.append(f"[install]\n{install_log}")

    migrate = sandbox.commands.run(
        "python manage.py migrate --no-input 2>&1", timeout=60
    )
    logs.append(f"[migrate]\n{(migrate.stdout or migrate.stderr or '')[:500]}")

    start_cmd = (
        "nohup python manage.py runserver 0.0.0.0:8000 "
        "> /tmp/server.log 2>&1 & echo $!"
    )
    proc = sandbox.commands.run(start_cmd, timeout=10)
    pid = proc.stdout.strip()

    ready = _wait_for_port(sandbox, 8000)
    logs.append(f"[server ready: {ready}]")

    if ready:
        r = sandbox.commands.run(
            "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:8000/",
            timeout=10,
        )
        logs.append(f"GET / -> {r.stdout.strip()}")

    server_log = sandbox.commands.run("cat /tmp/server.log 2>&1", timeout=5)
    logs.append(f"[server log]\n{(server_log.stdout or '')[-2000:]}")

    if pid:
        sandbox.commands.run(f"kill {pid} 2>/dev/null || true", timeout=5)
    return "\n".join(logs)


def _run_react(sandbox, source_files: dict) -> str:
    logs = []

    # Prefer clean install when a lockfile is provided. If no lockfile,
    # limit Node's heap for npm to avoid OOM in constrained sandboxes and
    # use conservative flags to speed up install.
    if "package-lock.json" in source_files or "npm-shrinkwrap.json" in source_files:
        install_cmd = "npm ci --silent 2>&1"
    else:
        install_cmd = (
            "NODE_OPTIONS=--max-old-space-size=1536 npm install --no-audit --no-fund "
            "--legacy-peer-deps --silent 2>&1"
        )

    install = sandbox.commands.run(install_cmd, timeout=300)
    logs.append(f"[npm install]\n{(install.stdout or install.stderr or '')[-1200:]}")

    # Catch build errors gracefully so they appear in logs rather than raising
    try:
        build = sandbox.commands.run("npm run build 2>&1", timeout=180)
        build_out = (build.stdout or build.stderr or "")[-800:]
        build_failed = build.exit_code != 0
    except CommandExitException as e:
        stderr = getattr(e, "stderr", "") or ""
        stdout = getattr(e, "stdout", "") or ""
        build_out = (stderr + stdout or str(e))[-800:]
        build_failed = True
    logs.append(f"[build]\n{build_out}")

    if build_failed:
        logs.append("[test result] failed")
        return "\n".join(logs)

    # Detect output dir: Vite → dist, CRA/Next → build
    pkg_json = source_files.get("package.json", "")
    is_vite = "vite.config" in " ".join(source_files.keys()) or '"vite"' in pkg_json
    serve_dir = "dist" if is_vite else "build"
    start_cmd = (
        f"nohup npx serve -s {serve_dir} -l 3000 "
        f"> /tmp/serve.log 2>&1 & echo $!"
    )
    proc = sandbox.commands.run(start_cmd, timeout=10)
    pid = proc.stdout.strip()

    ready = _wait_for_port(sandbox, 3000)
    logs.append(f"[serve ready: {ready}]")

    if ready:
        r = sandbox.commands.run(
            "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/",
            timeout=10,
        )
        logs.append(f"GET / -> {r.stdout.strip()}")

    serve_log = sandbox.commands.run("cat /tmp/serve.log 2>&1", timeout=5)
    logs.append(f"[serve log]\n{(serve_log.stdout or '')[-1000:]}")

    if pid:
        sandbox.commands.run(f"kill {pid} 2>/dev/null || true", timeout=5)
    return "\n".join(logs)


# ---------------------------------------------------------------------------

def _normalize_source_files(source_files: dict) -> dict:
    """Normalize model output to a {filepath: str} map.

    Handles:
    - Values that are dicts instead of strings (model forgot to stringify)
    - Single main.py wrapping an inner JSON file map (as string or dict)
    """
    if not isinstance(source_files, dict):
        return {"main.py": str(source_files)}

    def _coerce_file_value(key: str, value) -> str:
        if isinstance(value, str):
            return value
        if isinstance(value, dict):
            if len(value) == 1:
                sole_key = next(iter(value))
                if isinstance(sole_key, str) and (len(sole_key) > 40 or "\n" in sole_key):
                    return sole_key
            return json.dumps(value, indent=2)
        return str(value)

    coerced = {k: _coerce_file_value(k, v) for k, v in source_files.items()}

    # Multiple files → likely valid
    if len(coerced) > 1:
        return coerced

    # Single-file case: maybe a wrapper with inner JSON map
    if "main.py" in coerced:
        raw = coerced["main.py"].strip()
        if raw.startswith("```"):
            lines = raw.split("\n")[1:]
            if lines and lines[-1].strip() == "```":
                lines = lines[:-1]
            raw = "\n".join(lines)
        match = re.search(r'\{.*\}', raw, re.DOTALL)
        if match:
            try:
                parsed = json.loads(match.group())
                if isinstance(parsed, dict) and parsed:
                    unwrapped = {k: _coerce_file_value(k, v) for k, v in parsed.items()}
                    if all(isinstance(v, str) for v in unwrapped.values()):
                        return unwrapped
            except json.JSONDecodeError:
                pass

    return coerced


# ---------------------------------------------------------------------------

@traceable
def developer_node(state: AgencyState) -> Dict:
    current_iterations = state.get("iterations", 0) + 1

    prompt = f"""You are an Expert Engineer. Generate ALL files needed for this specification:
    {state['specification']}

    Previous test failure logs (if any):
    {state['test_logs']}

    User-provided input values: {state.get('user_inputs', {})}
    Use these exact values as variables at the top of the entry file. Do NOT use input() calls.
    If user_inputs is empty, use reasonable hardcoded defaults.

    STRICT RULES:
    - Return a JSON object where keys are relative file paths and values are file contents.
    - Example for FastAPI: {{"main.py": "...", "requirements.txt": "fastapi\nuvicorn"}}
    - Example for React: {{"package.json": "...", "src/App.jsx": "...", "public/index.html": "..."}}
    - For React apps, prefer Vite. If you use CRA scripts (`react-scripts`), you MUST include `react-scripts` in dependencies.
    - Example for plain Python: {{"main.py": "..."}}
    - Include requirements.txt (Python) or package.json (Node) when third-party packages are needed.
    - Do NOT use local relative imports between generated files unless they are in the same dict.
    - Return ONLY the raw JSON object. No markdown fences, no extra text.
    """

    response = model(prompt)
    raw = response.content.strip()

    # Strip markdown fences if present
    if raw.startswith("```"):
        lines = raw.split("\n")
        lines = lines[1:]
        if lines and lines[-1].strip() == "```":
            lines = lines[:-1]
        raw = "\n".join(lines)

    # Try to parse as JSON dict of files
    source_code = None
    json_match = re.search(r'\{.*\}', raw, re.DOTALL)
    if json_match:
        try:
            parsed = json.loads(json_match.group())
            if isinstance(parsed, dict) and all(isinstance(v, str) for v in parsed.values()):
                source_code = parsed
        except json.JSONDecodeError:
            pass

    # Fallback: treat entire response as main.py
    if source_code is None:
        source_code = {"main.py": raw}

    source_code = _normalize_source_files(source_code)

    return {
        "source_code": source_code,
        "iterations": current_iterations,
    }


@traceable
def tester_node(state: AgencyState) -> Dict:
    source_files = _normalize_source_files(state['source_code'])

    # Detect project type from file tree and source content
    all_source = " ".join(source_files.values()).lower()
    has_package_json  = "package.json" in source_files
    has_manage_py     = "manage.py" in source_files
    is_fastapi = "fastapi" in all_source and not has_manage_py
    is_django  = has_manage_py or ("django" in all_source and not has_package_json)
    is_react   = has_package_json

    with Sandbox.create() as sandbox:
        # Write full project tree into sandbox
        for filepath, content in source_files.items():
            sandbox.files.write(filepath, content)

        try:
            if is_react:
                logs = _run_react(sandbox, source_files)
            elif is_django:
                logs = _run_django(sandbox, source_files)
            elif is_fastapi:
                logs = _run_fastapi(sandbox, source_files)
            else:
                logs = _run_python_script(sandbox, source_files)
        except Exception as e:
            tb = traceback.format_exc()
            # Include any stdout/stderr stored on the exception, if present
            extra = ""
            try:
                extra = getattr(e, 'stderr', '') or getattr(e, 'stdout', '') or ''
            except Exception:
                extra = ''
            logs = f"[tester exception]\n{str(e)}\n\n{extra}\n\n{tb}"

    return {"test_logs": logs}

@traceable
def human_node(state: AgencyState) -> Dict:
    files = state.get('source_code', {})
    if files:
        sections = [f"# {name}\n{content}" for name, content in files.items()]
        code = "\n\n".join(sections)
    else:
        code = ''
    logs = state.get('test_logs', '')

    # Pause execution and surface info to the caller
    feedback = interrupt({
        "message": "Review required. Approve or provide rejection reason.",
        "code": code,
        "test_logs": logs,
    })

    # feedback is whatever the caller passes via Command(resume=...)
    approved = str(feedback).strip().lower() in ("yes", "approve", "approved", "y")
    return {
        "approved_by_human": approved,
        "human_feedback": str(feedback),
    }