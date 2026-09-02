# Dependencies Documentation

This document provides detailed information about all project dependencies and their purposes.

---

## Core Dependencies

### LangGraph & LangChain

**langgraph** (^0.1.0)
- **Purpose**: State machine orchestration framework for multi-agent workflows
- **Key Features**:
  - Graph-based workflow definition
  - State persistence and recovery
  - Conditional routing and cycles
  - Human-in-the-loop support via `interrupt_before`
- **Usage**: Core engine for orchestrating PM, Dev, Tester, and Human agents
- **Docs**: https://langchain-ai.github.io/langgraph/

**langchain** (^0.2.0)
- **Purpose**: LLM framework core utilities and abstractions
- **Key Features**:
  - Message and chat history management
  - Prompt templates and chaining
  - Tool/function calling abstractions
  - Output parsing
- **Usage**: Foundation for agent implementations and LLM interactions
- **Docs**: https://python.langchain.com/

**google-genai** (^1.75.0)
- **Purpose**: Direct Google Gemini API client
- **Key Features**:
  - Gemini interactions API
  - Synchronous and asynchronous clients
  - Text and multimodal generation
- **Usage**: Direct LLM backbone for PM, Dev agents, and design questions
- **Docs**: https://googleapis.github.io/python-genai/

### Observability & Tracing

**langsmith** (^0.1.0)
- **Purpose**: Tracing, debugging, and monitoring for LLM applications
- **Key Features**:
  - End-to-end execution tracing
  - State mutation visibility
  - Performance profiling
  - Error tracking
- **Usage**: Full transparency into agent decision-making
- **Docs**: https://smith.langchain.com/docs

### Code Execution & Sandboxing

**e2b** (^1.0.0)
- **Purpose**: Secure, isolated code execution environment
- **Key Features**:
  - Sandbox VMs (Linux-based)
  - Dependency installation (pip, npm, etc.)
  - Stdout/stderr capture
  - Timeout and resource limits
  - Multi-language support
- **Usage**: Tester Agent runs generated code safely
- **Docs**: https://e2b.dev/docs

### Frontend & UI

**streamlit** (^1.28.0)
- **Purpose**: Web UI framework for data applications
- **Key Features**:
  - Rapid development (no HTML/CSS required)
  - Real-time updates
  - Widget library (buttons, forms, charts, etc.)
  - Session state management
- **Usage**: User-facing dashboard for the boardroom
- **Docs**: https://docs.streamlit.io

### Data & Configuration

**pydantic** (^2.0.0)
- **Purpose**: Data validation and settings management
- **Key Features**:
  - Runtime type validation
  - Serialization/deserialization
  - Config management
  - Error messages
- **Usage**: State TypedDict validation, agent configuration
- **Docs**: https://docs.pydantic.dev/

**python-dotenv** (^1.0.0)
- **Purpose**: Load environment variables from .env files
- **Key Features**:
  - .env file parsing
  - Variable interpolation
- **Usage**: Loading API keys and configuration
- **Docs**: https://python-dotenv.readthedocs.io/

### Networking & HTTP

**aiohttp** (^3.9.0)
- **Purpose**: Async HTTP client and server
- **Key Features**:
  - Async/await support
  - Connection pooling
  - Request/response handling
  - SSL/TLS support
- **Usage**: Async API calls to Gemini and E2B
- **Alternative**: httpx (see below)

**httpx** (^0.25.0)
- **Purpose**: Modern HTTP client with async support
- **Key Features**:
  - Sync and async APIs
  - HTTP/1.1 and HTTP/2
  - Request/response streaming
  - Authentication handling
- **Usage**: HTTP client for external APIs

### Resilience & Reliability

**tenacity** (^8.2.0)
- **Purpose**: Retry logic and resilience patterns
- **Key Features**:
  - Exponential backoff
  - Jitter support
  - Conditional retries
  - Timeout handling
- **Usage**: Retry API calls to Gemini/E2B on failures
- **Docs**: https://tenacity.readthedocs.io/

### Type Hints

**typing-extensions** (^4.8.0)
- **Purpose**: Backported type hints for older Python versions
- **Key Features**:
  - `TypedDict` (Python 3.10+)
  - `Literal`, `Union`, `Optional` enhancements
  - Protocol support
- **Usage**: Advanced type annotations for agent states
- **Docs**: https://docs.python.org/3/library/typing_extensions.html

---

## Development Dependencies

Install with: `uv sync --all-extras` or `uv add --dev <package>`

### Testing

**pytest** (^7.4.0)
- **Purpose**: Testing framework
- **Usage**: Run test suite: `uv run pytest`

**pytest-asyncio** (^0.21.0)
- **Purpose**: Async test support for pytest
- **Usage**: Test async agent functions

**pytest-cov** (^4.1.0)
- **Purpose**: Coverage reporting
- **Usage**: `uv run pytest --cov=agency`

### Code Quality

**ruff** (^0.1.0)
- **Purpose**: Fast Python linter (written in Rust)
- **Key Features**:
  - 10-100x faster than flake8
  - Wide rule set
  - Auto-fix capabilities
- **Usage**: `uv run ruff check .`

**black** (^23.11.0)
- **Purpose**: Code formatter
- **Usage**: `uv run black .`

**isort** (^5.12.0)
- **Purpose**: Import sorter
- **Usage**: `uv run isort .`

**mypy** (^1.7.0)
- **Purpose**: Static type checker
- **Usage**: `uv run mypy agency/`

### Development Tools

**ipython** (^8.16.0)
- **Purpose**: Enhanced Python REPL
- **Usage**: `uv run ipython`

**ipdb** (^0.13.0)
- **Purpose**: IPython debugger
- **Usage**: `import ipdb; ipdb.set_trace()` in code

---

## Dependency Graph

```
Orchestration Layer
├── langgraph (state machine)
├── langchain (abstractions)
└── google-genai (Gemini API)

Execution Layer
├── e2b (sandboxing)
└── streamlit (UI)

Observability Layer
└── langsmith (tracing)

Infrastructure Layer
├── pydantic (data validation)
├── python-dotenv (config)
├── aiohttp/httpx (HTTP)
├── tenacity (resilience)
└── typing-extensions (types)

Development Layer
├── pytest (testing)
├── ruff (linting)
├── black (formatting)
└── mypy (type checking)
```

---

## Adding New Dependencies

### With uv

```bash
# Add to runtime dependencies
uv add package-name

# Add to dev dependencies
uv add --dev package-name

# Update pyproject.toml
# and automatically sync uv.lock
uv sync
```

### Manual (pyproject.toml)

Add to the appropriate section in `pyproject.toml`:

```toml
[project]
dependencies = [
    # ... existing ...
    "new-package>=1.0.0",
]

[project.optional-dependencies]
dev = [
    # ... existing ...
    "new-dev-package>=1.0.0",
]
```

Then run: `uv sync`

---

## Troubleshooting Dependencies

### Issue: Module not found

```bash
# Ensure venv is activated and synced
uv sync

# Or run directly with uv
uv run python script.py
```

### Issue: Version conflict

```bash
# Clear and resync
uv sync --fresh

# Or check what's installed
uv pip list
```

### Issue: Slow package resolution

```bash
# Use uv's speed advantages
uv sync --all-extras  # Faster than pip install -e ".[dev]"
```

---

## API Keys Required

These packages interact with external services that require free API keys:

| Package | Service | Free Tier |
|---------|---------|-----------|
| google-genai | Google Gemini | Google AI plan |
| e2b | E2B Sandbox | 100 hrs/month |
| langsmith | LangSmith | 5,000 traces/month |

See [README.md](README.md#2️⃣-get-free-api-keys-2-minutes) for setup instructions.

---

## Version Updates

To update all dependencies to latest versions:

```bash
uv sync --upgrade
```

To update specific package:

```bash
uv add package-name@latest
```

Check what's outdated:

```bash
uv pip index --all-extras
```
