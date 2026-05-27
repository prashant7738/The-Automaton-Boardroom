# 🚀 The Automaton Boardroom: Autonomous Multi-Agent Software Micro-Agency

An advanced, production-grade software engineering multi-agent system built entirely with **LangGraph**, **LangSmith**, and **E2B**. 

Instead of generating static, unverified code chunks, **The Automaton Boardroom** simulates a real software development company. It translates a user's high-level application idea into a rigorous technical spec, writes code files, provisions an isolated Linux cloud sandbox, installs required dependencies, runs verification tests, detects compiler/runtime errors, loops back to self-correct its own codebase, and asks for human feedback before compiling a polished, zipped output.

> **Zero-Cost Solution**: Built entirely on free developer tiers. No credit card required. No hidden fees. $0 to build production-grade AI-assisted software.

---

## ✨ Key Features

- ✅ **Full Development Lifecycle**: Spec → Code → Test → Self-Correct → Human Review → Delivery
- ✅ **Self-Healing AI**: Automatically detects and fixes bugs through iterative testing
- ✅ **Isolated Execution**: Secure E2B sandbox prevents malicious code execution
- ✅ **Human-in-the-Loop**: Pause and approve before final deployment
- ✅ **Zero Dependencies Cost**: Uses only free-tier APIs (Google Gemini, E2B, LangSmith)
- ✅ **Full Observability**: LangSmith tracing for debugging and performance monitoring
- ✅ **Streamlit UI**: Beautiful, interactive web interface for non-technical users

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
boardroom-agency/
│
├── README.MD                   # This file
├── .env                        # API keys (Gemini, E2B, LangSmith) — NOT committed
├── requirements.txt            # Python dependencies
├── app.py                      # Streamlit UI entry point
│
└── agency/                     # Core LangGraph package
    ├── __init__.py
    ├── state.py               # TypedDict state machine definition
    ├── nodes.py               # Agent implementations & E2B tools
    └── graph.py               # Node routing & conditional loops
```

---

## ⚙️ Quick Start

### Prerequisites
- Python 3.10+
- Free API keys (created in next step)

### 1️⃣ Clone & Set Up Environment

```bash
git clone https://github.com/yourusername/automaton-boardroom.git
cd boardroom-agency

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2️⃣ Get Free API Keys (2 minutes)

**Google Gemini:**
1. Go to [Google AI Studio](https://aistudio.google.com/apikey)
2. Click "Get API Key" → "Create API Key in new project"
3. Copy your API key

**E2B:**
1. Go to [E2B Dashboard](https://e2b.dev)
2. Sign up (free) → API Keys
3. Copy your API key

**LangSmith (Optional):**
1. Go to [LangSmith](https://smith.langchain.com)
2. Sign up → Organization → Create API Key

### 3️⃣ Configure Environment Variables

Create a `.env` file in the root directory:

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

### 4️⃣ Run the Application

```bash
streamlit run app.py
```

Open your browser to `http://localhost:8501`

---

## 💡 Usage Examples

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

| Issue | Solution |
|-------|----------|
| `GOOGLE_API_KEY not found` | Verify `.env` file exists in root directory with correct key format |
| `E2B_API_KEY invalid` | Check key hasn't expired; regenerate at [e2b.dev](https://e2b.dev) |
| `Streamlit port 8501 already in use` | `streamlit run app.py --server.port 8502` |
| `Tests keep failing after 5 retries` | Check agent loop max retries; may need human intervention |
| `LangSmith not connecting` | Set `LANGCHAIN_TRACING_V2=false` to proceed without tracing |
| `E2B sandbox quota exceeded` | Check usage at E2B dashboard; free tier = 100 hrs/month |

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
