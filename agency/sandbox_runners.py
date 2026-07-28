"""E2B sandbox orchestration: install dependencies, start servers/builds, and
capture logs for each supported project stack (plain Python, FastAPI, Django,
React/Vite, and full-stack FastAPI + React).

Every function here receives an already-created E2B `sandbox` handle (see
`agency.nodes.tester_node`) plus the normalized `{filepath: content}` map of
generated source files, and returns a single string of captured logs.
"""
import json
import re
import time

from e2b.sandbox.commands.command_handle import CommandExitException


def _install_python_deps(sandbox, source_files: dict) -> str:
    """Install Python deps from requirements.txt or pyproject.toml. Return log."""
    if "requirements.txt" in source_files:
        r = sandbox.commands.run("pip install -r requirements.txt 2>&1", timeout=120)
        return (r.stdout or r.stderr or "")[-3000:]
    if "pyproject.toml" in source_files:
        r = sandbox.commands.run("pip install -e . 2>&1", timeout=120)
        return (r.stdout or r.stderr or "")[-3000:]
    return ""


def _wait_for_port(sandbox, port: int, retries: int = 15, delay: float = 1.5) -> bool:
    """Poll until HTTP server responds on given port inside sandbox."""
    for attempt in range(retries):
        try:
            check = sandbox.commands.run(
                f"curl -s http://127.0.0.1:{port}/ -o /dev/null -w '%{{http_code}}'",
                timeout=5,
            )
            if check.stdout.strip() in ("200", "301", "302", "404", "405", "422"):
                return True
        except Exception as e:
            print(f"[_wait_for_port] attempt {attempt + 1}/{retries} on port {port} failed: {e}")
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
        f"--host 0.0.0.0 --port 8000 > /tmp/server.log 2>&1 &"
    )
    sandbox.commands.run(start_cmd, timeout=10)

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

    sandbox.commands.run("pkill -f 'uvicorn' 2>/dev/null || true", timeout=5)
    return "\n".join(logs)


def _run_django(sandbox, source_files: dict) -> str:
    logs = []
    install_log = _install_python_deps(sandbox, source_files)
    if install_log:
        logs.append(f"[install]\n{install_log}")

    migrate = sandbox.commands.run(
        "python manage.py migrate --no-input 2>&1", timeout=60
    )
    logs.append(f"[migrate]\n{(migrate.stdout or migrate.stderr or '')[-2000:]}")

    start_cmd = (
        "nohup python manage.py runserver 0.0.0.0:8000 "
        "> /tmp/server.log 2>&1 &"
    )
    sandbox.commands.run(start_cmd, timeout=10)

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

    sandbox.commands.run("pkill -f 'manage.py runserver' 2>/dev/null || true", timeout=5)
    return "\n".join(logs)


def _run_react(sandbox, source_files: dict) -> str:
    logs = []

    # Prefer clean install when a lockfile is provided. If no lockfile,
    # limit Node's heap for npm to avoid OOM in constrained sandboxes and
    # use conservative flags to speed up install.
    if "package-lock.json" in source_files or "npm-shrinkwrap.json" in source_files:
        install_cmd = "NODE_ENV=development npm ci --include=dev --silent 2>&1"
    else:
        install_cmd = (
            "NODE_ENV=development NODE_OPTIONS=--max-old-space-size=1536 npm install "
            "--no-audit --no-fund --legacy-peer-deps --include=dev --silent 2>&1"
        )

    install = sandbox.commands.run(install_cmd, timeout=300)
    logs.append(f"[npm install]\n{(install.stdout or install.stderr or '')[-1200:]}")

    # Catch build errors gracefully so they appear in logs rather than raising
    try:
        build = sandbox.commands.run("npm run build 2>&1", timeout=600)
        build_out = (build.stdout or build.stderr or "")[-3000:]
        build_failed = build.exit_code != 0
    except CommandExitException as e:
        stderr = getattr(e, "stderr", "") or ""
        stdout = getattr(e, "stdout", "") or ""
        build_out = (stderr + stdout or str(e))[-3000:]
        build_failed = True
    logs.append(f"[build]\n{build_out}")

    if build_failed:
        logs.append("[test result] failed")
        return "\n".join(logs)

    # Detect output dir: Vite → dist, CRA/Next → build
    pkg_json = source_files.get("package.json", "")
    # Check for vite.config file OR "vite" in the devDependencies/dependencies section only,
    # not in the package name or description (which would be a false positive).
    _pkg_deps: str = ""
    if pkg_json:
        try:
            _pkg_obj = json.loads(pkg_json)
            _pkg_deps = json.dumps({
                **_pkg_obj.get("dependencies", {}),
                **_pkg_obj.get("devDependencies", {}),
            })
        except (json.JSONDecodeError, AttributeError):
            pass
    is_vite = "vite.config" in " ".join(source_files.keys()) or '"vite"' in _pkg_deps
    serve_dir = "dist" if is_vite else "build"
    start_cmd = (
        f"nohup npx serve -s {serve_dir} -l 3000 "
        f"> /tmp/serve.log 2>&1 &"
    )
    sandbox.commands.run(start_cmd, timeout=10)

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

    try:
        sandbox.commands.run("pkill -f 'npx serve'", timeout=5)
    except Exception:
        pass  # process may have already exited; ignore
    return "\n".join(logs)


def _run_fullstack(sandbox, source_files: dict) -> str:
    """Run a full-stack project: FastAPI backend (port 8000) + React/Vite frontend (port 3000)."""
    logs = []

    # --- Backend ---
    backend_files = {k: v for k, v in source_files.items() if k.startswith("backend/")}

    if "backend/requirements.txt" in source_files:
        r = sandbox.commands.run("cd backend && pip install -r requirements.txt 2>&1", timeout=120)
        logs.append(f"[backend install]\n{(r.stdout or r.stderr or '')[-2000:]}")

    entry_module, app_var = "main", "app"
    for fname, content in backend_files.items():
        if fname.endswith(".py") and "FastAPI(" in content:
            rel = fname[len("backend/"):].replace(".py", "").replace("/", ".")
            entry_module = rel
            m = re.search(r'(\w+)\s*=\s*FastAPI\(', content)
            if m:
                app_var = m.group(1)
            break

    sandbox.commands.run(
        f"cd backend && nohup uvicorn {entry_module}:{app_var} "
        f"--host 0.0.0.0 --port 8000 > /tmp/backend.log 2>&1 &",
        timeout=10,
    )
    backend_ready = _wait_for_port(sandbox, 8000)
    logs.append(f"[backend ready: {backend_ready}]")

    if backend_ready:
        for endpoint in ["/", "/docs", "/openapi.json"]:
            r = sandbox.commands.run(
                f"curl -s -o /dev/null -w '%{{http_code}}' http://127.0.0.1:8000{endpoint}",
                timeout=10,
            )
            logs.append(f"GET backend{endpoint} -> {r.stdout.strip()}")

    backend_log = sandbox.commands.run("cat /tmp/backend.log 2>&1", timeout=5)
    logs.append(f"[backend log]\n{(backend_log.stdout or '')[-2000:]}")

    # --- Frontend ---
    install_cmd = (
        "cd frontend && NODE_ENV=development NODE_OPTIONS=--max-old-space-size=1536 npm install "
        "--no-audit --no-fund --legacy-peer-deps --include=dev --silent 2>&1"
    )
    install = sandbox.commands.run(install_cmd, timeout=300)
    logs.append(f"[frontend npm install]\n{(install.stdout or install.stderr or '')[-1200:]}")

    try:
        build = sandbox.commands.run("cd frontend && npm run build 2>&1", timeout=600)
        build_out = (build.stdout or build.stderr or "")[-3000:]
        build_failed = build.exit_code != 0
    except CommandExitException as e:
        stderr = getattr(e, "stderr", "") or ""
        stdout = getattr(e, "stdout", "") or ""
        build_out = (stderr + stdout or str(e))[-3000:]
        build_failed = True
    logs.append(f"[frontend build]\n{build_out}")

    if build_failed:
        logs.append("[test result] frontend build failed")
        return "\n".join(logs)

    sandbox.commands.run(
        "nohup npx serve -s frontend/dist -l 3000 > /tmp/serve.log 2>&1 &",
        timeout=10,
    )
    frontend_ready = _wait_for_port(sandbox, 3000)
    logs.append(f"[frontend serve ready: {frontend_ready}]")

    if frontend_ready:
        r = sandbox.commands.run(
            "curl -s -o /dev/null -w '%{http_code}' http://127.0.0.1:3000/",
            timeout=10,
        )
        logs.append(f"GET frontend / -> {r.stdout.strip()}")

    serve_log = sandbox.commands.run("cat /tmp/serve.log 2>&1", timeout=5)
    logs.append(f"[serve log]\n{(serve_log.stdout or '')[-1000:]}")

    try:
        sandbox.commands.run("pkill -f 'uvicorn' 2>/dev/null || true", timeout=5)
        sandbox.commands.run("pkill -f 'npx serve' 2>/dev/null || true", timeout=5)
    except Exception:
        pass
    return "\n".join(logs)
