# 🚀 The Automaton Boardroom: Autonomous Multi-Agent Software Micro-Agency

An advanced, production-grade software engineering multi-agent system built entirely with **LangGraph**, **LangSmith**, and **E2B**. 

Instead of generating static, unverified code chunks, **The Automaton Boardroom** simulates a real software development company. It translates a user's high-level application idea into a rigorous technical spec, writes code files, provisions an isolated Linux cloud sandbox, installs required dependencies, runs verification tests, detects compiler/runtime errors, loops back to self-correct its own codebase, and asks for human feedback before compiling a polished, zipped output.

> **Zero-Cost Solution**: Built entirely on free developer tiers. No credit card required. No hidden fees. $0 to build production-grade AI-assisted software.

---

## ✨ Key Features

- ✅ **Full Development Lifecycle**: Spec → Code → Test → Self-Correct → Human Review → Delivery
- ✅ **Self-Healing AI**: Automatically detects and fixes bugs through iterative testing
- ✅ **Isolated Execution**: Secure E2B sandbox prevents malicious code execution
- ✅ **Prompt-Safety Guardrails**: User-provided ideas, logs, and inputs are wrapped and scanned to reduce prompt injection risk
- ✅ **LLM Provider Resilience**: Groq is tried first, then Gemini fallback is used if needed, with clear failure reporting
- ✅ **Human-in-the-Loop**: Pause and approve before final deployment
- ✅ **Zero Dependencies Cost**: Uses only free-tier APIs (Google Gemini, E2B, LangSmith)
- ✅ **Full Observability**: LangSmith tracing for debugging and performance monitoring
- ✅ **Streamlit UI**: Beautiful, interactive web interface for non-technical users

---

## 🆕 Recent Updates

- Added safer LLM prompt handling so user ideas, specifications, logs, and runtime inputs are treated as data instead of instructions.
- Improved model fallback behavior so Groq failures now fall back cleanly to Gemini, and both-provider failures are reported clearly.
- Updated React/Vite generation and sandbox install behavior so generated apps install `vite` and `@vitejs/plugin-react` reliably before build.

---

## 🏗️ Architecture & Workflow

This platform leverages LangGraph's state machine to handle complex cyclic dependencies, error recovery, and execution states.

```
┌──────────────────────────────────────────────────────────────────┐
│                  User Input: App Idea                            │
└────────────────────────┬─────────────────────────────────────────┘
                         │
                         ▼
          ┌──────────────────────────────┐
          │   📋 PM Agent                 │ ◄─── Analyze Requirements
          │    (Specifications)           │      Create Architecture
          └────────────┬──────────────────┘
                       │
                       ▼
          ┌──────────────────────────────┐
    ┌────►│   💻 Dev Agent               │ ◄─── Write Code Files
    │     │    (Implementation)           │      Handle Errors
    │     └────────────┬──────────────────┘
    │                  │
    │                  ▼
    │     ┌──────────────────────────────┐
    │     │   🧪 Tester Agent            │ ◄─── Run Tests
    │     │    (Verification Gate)        │      Sandbox Execution
    │     └────────────┬──────────────────┘
    │                  │
    │           [Tests Pass/Fail?]
    │            /             \
    │  (FAIL)   /               \   (PASS)
    └──────────                  ▼
                    ┌──────────────────────────────┐
                    │   👤 Human Review Node       │ ◄─── Final Approval
                    │    (Sign-off & Edits)        │      User Feedback
                    └────────────┬─────────────────┘
                                 │
                                 ▼
                    ┌──────────────────────────────┐
                    │  📦 Zipped Deliverable       │
                    └──────────────────────────────┘
```

### 🤖 The Four Specialized Agents

| Agent | Role | Responsibilities |
|-------|------|------------------|
| **PM Agent** | Product Manager | • Analyzes vague requirements • Creates detailed `specifications.md` • Plans file structure & architecture |
| **Dev Agent** | Developer | • Writes clean, modular code • Implements fixes from test failures • Self-corrects based on feedback |
| **Tester Agent** | QA/Gatekeeper | • Spins up isolated E2B sandbox • Creates Python virtual environments • Installs dependencies • Captures stdout/stderr • Reports failures |
| **Human Node** | Stakeholder | • Reviews generated code • Approves or requests changes • Uses LangGraph's `interrupt_before` for explicit sign-off |

---

## 🛠️ Tech Stack: Zero-Cost, Production-Grade

Built entirely on free developer tiers—no credit card required.

| Component | Technology | Free Tier | Purpose |
|-----------|-----------|-----------|---------|
| **Orchestration** | LangGraph + LangChain Core | Open-source | State machine workflow, routing, conditional logic |
| **LLM Brain** | Google Gemini 2.5 Flash | 1,500 req/day | Code generation, analysis, and error fixing |
| **Code Execution** | E2B Sandbox | 100 hrs/month | Isolated, secure code execution environment |
| **Observability** | LangSmith | 5,000 traces/month | Debugging, performance monitoring, tracing |
| **Frontend UI** | Streamlit | Free | Interactive web interface, real-time updates |
| **Language** | Python 3.10+ | Open-source | Primary implementation language |

---

## 📂 Project Structure

```
automaton-boardroom/
│
├── README.md                   # This file
├── .env                        # API keys (Gemini, E2B, LangSmith) — NOT committed
├── .env.example                # Example environment variables template
├── pyproject.toml              # Project config & dependencies (uv)
├── uv.lock                     # Locked dependency versions (auto-generated)
├── app.py                      # Streamlit UI entry point
│
└── agency/                     # Core LangGraph package
    ├── __init__.py
    ├── states.py              # TypedDict state machine definition
    ├── nodes.py               # Agent implementations & E2B tools
    └── graph.py               # Node routing & conditional loops
```

---

## 📦 Dependencies

All dependencies are managed with `uv` and specified in `pyproject.toml`:

| Package | Version | Purpose |
|---------|---------|---------|
| `langgraph` | ^0.1.0 | State machine orchestration & workflow |
| `langchain` | ^0.2.0 | LLM framework core utilities |
| `langchain-google-genai` | ^0.1.0 | Google Gemini LLM integration |
| `langsmith` | ^0.1.0 | Tracing, debugging, & monitoring |
| `e2b` | ^1.0.0 | Secure sandbox code execution |
| `streamlit` | ^1.28.0 | Web UI framework |
| `pydantic` | ^2.0.0 | Data validation & settings |
| `python-dotenv` | ^1.0.0 | Environment variable management |
| `tenacity` | ^8.2.0 | Retry logic for API calls |
| `aiohttp` | ^3.9.0 | Async HTTP client |
| `typing-extensions` | ^4.8.0 | Extended type hints |

---

## 🚀 About `uv` Package Manager

This project uses **[uv](https://docs.astral.sh/uv/)** for dependency management. `uv` is a blazingly fast Python package installer & resolver written in Rust.

### Why uv?
- ⚡ **10-100x faster** than pip
- 🔒 **Deterministic builds** with `uv.lock` file
- 📦 **Complete Python environment management** (venv + packages)
- 🎯 **Simpler commands** (one tool, not pip + venv)
- 🔄 **Lock file by default** for reproducible environments

### Installation

```bash
# macOS/Linux using pip
pip install uv

# macOS using Homebrew
brew install uv

# Windows (via pip)
pip install uv

# Or download from: https://docs.astral.sh/uv/
```

---

## ⚙️ Quick Start

### Prerequisites
- **Python 3.10+** (required for TypedDict)
- **uv** package manager ([install here](https://docs.astral.sh/uv/))
- Free API keys (created in Step 2)

### 1️⃣ Clone & Set Up Environment

```bash
# Clone repository
git clone https://github.com/prashant33/automaton-boardroom.git
cd automaton-boardroom

# Create & activate virtual environment with uv
uv venv

# Activate venv
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Install dependencies via uv
uv sync
```

**Or in one command:**
```bash
uv sync --python 3.11
```

---

### 2️⃣ Get Free API Keys (2 minutes)

**Google Gemini API:**
1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Click "Get API Key" → "Create API Key in new project"
3. Copy your API key

**E2B (Sandbox):**
1. Go to [E2B Dashboard](https://e2b.dev)
2. Sign up (free) → Navigate to API Keys
3. Generate and copy your API key

**LangSmith (Optional - for tracing):**
1. Go to [LangSmith](https://smith.langchain.com)
2. Sign up → Organization settings → API Keys
3. Create and copy your API key

### 3️⃣ Configure Environment Variables

Create a `.env` file in the root directory (copy from `.env.example`):

```env
# LLM Provider Configuration
GOOGLE_API_KEY="your_gemini_api_key_here"

# Secure VM Code Interpreter Sandboxing
E2B_API_KEY="your_e2b_api_key_here"

# Visual Production Tracing & Monitoring (Optional)
LANGCHAIN_TRACING_V2="true"
LANGCHAIN_API_KEY="your_langsmith_api_key_here"
LANGCHAIN_PROJECT="automaton-boardroom"
```

⚠️ **Never commit `.env` to version control!** It contains sensitive API keys.

### 4️⃣ Run the Application

```bash
# Make sure venv is activated
source .venv/bin/activate  # On Windows: .venv\Scripts\activate

# Launch Streamlit app
uv run streamlit run app.py
```

Open your browser to `http://localhost:8501`

---

## � Development Setup

### Install Development Dependencies

```bash
# Install all dependencies including dev tools
uv sync --all-extras

# Or add specific dev dependencies
uv add --dev pytest pytest-asyncio pytest-cov ruff black isort mypy
```

### Common Development Tasks

```bash
# Run tests
uv run pytest

# Run tests with coverage
uv run pytest --cov=agency

# Format code with black
uv run black .

# Sort imports with isort
uv run isort .

# Lint with ruff
uv run ruff check .

# Type check with mypy
uv run mypy agency/

# Run all code quality checks
uv run black . && uv run isort . && uv run ruff check . && uv run mypy agency/
```

### Project Structure for Development

```
automaton-boardroom/
├── agency/                     # Main package
│   ├── __init__.py
│   ├── state.py               # State machine definition
│   ├── nodes.py               # Agent implementations
│   └── graph.py               # LangGraph workflow
├── tests/                      # Test suite
│   ├── __init__.py
│   ├── test_state.py
│   ├── test_nodes.py
│   └── test_graph.py
├── app.py                      # Streamlit entry point
├── pyproject.toml              # Project config with uv
├── uv.lock                     # Dependency lock file
└── .env.example                # Environment template
```

---

### Example 1: Build a Todo CLI App
```
User Input: "Create a Python CLI todo app with add, list, and delete commands. Store data in JSON."

System Flow:
1. PM Agent → Creates spec with CLI design, data schema, error handling
2. Dev Agent → Writes main.py, todos.json handler, argument parser
3. Tester Agent → Spins up sandbox, tests add/list/delete functionality
4. Human Node → Reviews code, approves → Deliverable ready
```

### Example 2: API with Self-Correction
```
User Input: "Build a Flask API that fetches weather data from OpenWeatherMap"

System Flow:
1. PM Agent → Defines endpoints, authentication flow, error handling
2. Dev Agent → Writes Flask app with API integration
3. Tester Agent → Tests endpoints, discovers missing env var handling
4. Dev Agent (Loop) → Automatically fixes missing error handling
5. Tester Agent → Re-runs tests, all pass ✅
6. Human Node → Reviews improved code, approves
```

---

## 🔍 How Self-Correction Works

1. **Tester Agent runs code** → Detects error (e.g., `ImportError: No module named 'numpy'`)
2. **Error logged to state** → Includes full traceback and context
3. **Dev Agent receives error** → Analyzes failure, updates code
4. **Loop back to Tester** → Re-runs tests automatically
5. **Success or new error** → Continue loop or escalate to human
6. **Max retries reached** → Human review for complex issues

### Error Recovery Loop Configuration

```python
# In graph.py
MAX_RETRIES = 5  # Max self-correction attempts
TIMEOUT_SECONDS = 300  # Timeout per test run
SANDBOX_RAM_MB = 512  # E2B sandbox memory allocation
```

---

## 🚨 Troubleshooting

### Common Issues

| Issue | Solution |
|-------|----------|
| `uv: command not found` | Install uv: `pip install uv` or follow [uv installation](https://docs.astral.sh/uv/#installation) |
| `GOOGLE_API_KEY not found` | Verify `.env` file exists in root directory with correct key format |
| `E2B_API_KEY invalid` | Check key hasn't expired; regenerate at [e2b.dev](https://e2b.dev) |
| `Streamlit port 8501 already in use` | `uv run streamlit run app.py -- --server.port 8502` |
| `ModuleNotFoundError: No module named 'langgraph'` | Run `uv sync` to install all dependencies |
| `LangSmith not connecting` | Set `LANGCHAIN_TRACING_V2=false` or check API key validity |
| `E2B sandbox quota exceeded` | Check usage at E2B dashboard; free tier = 100 hrs/month |
| `sh: vite: not found` during React build | Re-run generation after the latest fixes; React/Vite installs now force dev dependencies and include `vite` + `@vitejs/plugin-react` |

### Useful uv Commands

```bash
# Sync dependencies (install/update)
uv sync

# Add a new dependency
uv add package-name

# Add dev dependency
uv add --dev pytest

# Update all dependencies
uv sync --upgrade

# Run a script
uv run python script.py

# Run with specific Python version
uv sync --python 3.11

# List installed packages
uv pip list

# Create fresh environment
uv venv --clean
```

---

## 📊 Cost Analysis

| Resource | Tier | Monthly Limit | Typical Usage |
|----------|------|---------------|---------------|
| Google Gemini API | Free | 1,500 requests | 5-10 small projects |
| E2B Compute | Free | 100 hours | ~2-3 projects/month |
| LangSmith Traces | Free | 5,000 traces | Most projects |
| **Total Cost** | **Free** | **Unlimited Projects** | **$0/month** |

---

## 🎯 Use Cases

- **Rapid Prototyping**: Turn ideas into working code in minutes
- **Learning Tool**: Understand LangGraph and multi-agent patterns
- **Code Review**: Let AI agents review before human sign-off
- **Automation Framework**: Build on top for specialized workflows
- **Education**: Teach students about AI-assisted development
- **Proof-of-Concept**: Validate ideas before engineering investment

---

## 📈 Observability & Tracing

This system integrates with **LangSmith** for full transparency. Every run provides:

- **State mutations**: Before/after snapshots at each node
- **Latency profiles**: Sub-millisecond timing for E2B initialization
- **Self-correction loops**: Visual trace of Dev Agent error fixes
- **Token usage**: Cost tracking and optimization insights
- **Error logs**: Complete traceback capture for debugging

View live traces at [LangSmith Dashboard](https://smith.langchain.com)

---

## 🤝 Contributing

Contributions welcome! Areas for improvement:

- [ ] Support for compiled languages (Go, Rust, Java)
- [ ] GPU-accelerated sandboxes via E2B
- [ ] Docker containerization for easy deployment
- [ ] Database migration support
- [ ] Frontend framework scaffolding (React, Vue, Next.js)
- [ ] CI/CD pipeline integration templates
- [ ] Advanced error recovery strategies
- [ ] Cost optimization for E2B usage

---

## 📝 License

Distributed under the MIT License. See LICENSE for more information.

---

## 🙋 Support & Questions

- **Documentation**: Check the `docs/` folder (coming soon)
- **Issues**: GitHub Issues for bug reports
- **Discussions**: GitHub Discussions for feature requests
- **Community**: Join our Discord community (link TBD)

---

## 📚 Additional Resources

- [LangGraph Documentation](https://langchain-ai.github.io/langgraph/)
- [E2B Sandbox Documentation](https://e2b.dev/docs)
- [LangSmith Documentation](https://smith.langchain.com/docs)
- [Google Gemini API Guide](https://ai.google.dev)
- [Streamlit Documentation](https://docs.streamlit.io)

---

**Built with ❤️ using LangGraph, LangSmith & E2B**

*Last Updated: May 2026*


To run graph:
 python -c "from agency.graph import get_mermaid_png_bytes; from io import BytesIO; from PIL import Image; Image.open(BytesIO(get_mermaid_png_bytes())).show()"

*Last Updated: July 2026*