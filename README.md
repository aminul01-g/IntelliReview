---
title: IntelliReview
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
app_port: 7860
---

<!-- [Image 1: IntelliReview Branding] -->
![IntelliReview Branding](docs/assets/branding.png)

## 🛡️ IntelliReview
**The Quality Gate for AI-Generated Code**

[![Build Status](https://img.shields.io/badge/build-passing-brightgreen.svg?style=for-the-badge)](https://github.com/aminul01-g/IntelliReview/actions)
[![Code Coverage](https://img.shields.io/badge/coverage-94%25-success.svg?style=for-the-badge)](https://github.com/aminul01-g/IntelliReview)
[![Health Score](https://img.shields.io/badge/Health_Score-A-brightgreen.svg?style=for-the-badge)](https://github.com/aminul01-g/IntelliReview)
[![SonarQube](https://img.shields.io/badge/integration-SonarQube-4E9BCD.svg?style=for-the-badge)](https://github.com/aminul01-g/IntelliReview)

---

## 📖 Executive Summary

In the era of AI-native software engineering, large language models (LLMs) are generating complex codebases in minutes. However, this velocity introduces severe risks: hallucinated APIs, subtle state management flaws, $O(n^2)$ regressions, and insecure cryptographic implementations.

**IntelliReview** is an enterprise-grade, hybrid-reasoning static analysis platform. It acts as the definitive quality gate between AI-generated code and your production environment. By utilizing both deterministic AST parsing and specialized LLM agents, IntelliReview automatically reviews pull requests, exposes architectural drift, and tracks the longitudinal health of your codebase.

---

## 🧠 The Hybrid Reasoning Paradigm

IntelliReview transcends traditional regex-based linters by uniting rigid structural analysis with cognitive contextual understanding:

1. **Deterministic Processing (AST Engine)**
   The pipeline parses incoming code into Abstract Syntax Trees (ASTs). This phase ensures zero hallucinations when enforcing strict style guides, detecting known CWE vulnerabilities (e.g., SQL injections), and executing custom `yaml` programmatic rules.
   
2. **Generative Processing (Agentic Orchestration)**
   Through a LangChain-based worker swarm, mathematically bounded code chunks are routed to hyper-specialized AI agents:
   - **Architecture Agent**: Evaluates SOLID principle compliance and tight-coupling degradation.
   - **Performance Agent**: Identifies algorithmic inefficiencies and memory leak risks.
   - **Security Agent**: Infers logical bypass vulnerabilities undetected by standard static tools.

---

## ⚡ Core Modules

### 🖥️ 1. Command Center & Metrics Dashboard
The unified React-based frontend (`AppShell` architecture) provides actionable telemetry. Powered by `Recharts`, the dashboard highlights:
- **Longitudinal Tracking**: Visualize AI suggestion acceptance rates and false-positive filtering over time.
- **Language Distributions**: Aggregated statistics of stack utilization.

### 🔍 2. AI Review Engine & Diff Analysis
A specialized interactive engine capable of ingesting raw code blobs, bulk repository directories, or standard unified git `diffs`. This restricts the AI's compute scope strictly to modified lines, slashing context window constraints and rapidly proposing direct branch remediations.

### 📜 3. Custom Rules Studio
Engineering leaders can deploy `.intellireview.yml` configurations to enforce local architectural philosophies. Instead of fighting generic AI assumptions, teams bind specific regex paradigms or nested AST node requirements directly into the review pipeline. 

**Example `.intellireview.yml` Configuration:**
```yaml
version: "1.0"
rules:
  - id: "RESTRICT_EVAL"
    severity: "critical"
    pattern: "eval\\(.*\\)"
    message: "Use of eval() is strictly prohibited."
  - id: "ENFORCE_LOGGER"
    severity: "high"
    ast_node: "CallExpression"
    pattern: "console.log"
    message: "Use the internal `logger` module instead of console.log."
```

### 🧮 4. Technical Debt Aggregator
Backed by **TimescaleDB** time-series data, IntelliReview calculates real-time **Technical Debt Ratios (TDR)** for every class and function:

$$ TDR = \frac{\text{Remediation Hours}}{\text{Original Development Hours}} $$

This empirical measurement allows product managers to mathematically trigger maintenance cycles when $TDR > 0.15$.

---

## 🔌 Integration Ecosystem

### 🌐 GitHub App Identity & Lifecycle
Rather than precarious PAT handling, IntelliReview establishes secure GitHub App communication channels. Relying on mathematically validated **JWTs** and short-lived, repository-scoped installation tokens, the system autonomously listens to PR Webhooks, reviews diffs, and injects actionable inline comments exactly where the code degraded.

### 🤖 Model Context Protocol (MCP) Server
IntelliReview operates an integrated **MCP Server**, exposing its core engine capabilities outward. Consequently, downstream AI agents (like Claude Code, Cursor, or Windsurf) can invoke `intellireview.analyze()` as a tool mid-generation, establishing an unprecedented auto-corrective loop.

---

## 🚀 Quickstart & Installation

IntelliReview orchestrates its microservices through Docker, leveraging **FastAPI (Python)** for the backend APIs, **React + Vite** for the frontend interfaces, and **Redis/Celery** for asynchronous task queuing.

### Prerequisites
- Node.js (v18+)
- Python (v3.11+)
- PostgreSQL (with `timescaledb` extension)
- Redis Server

### 1. Backend API via FastAPI
```bash
# Clone the repository
git clone https://github.com/aminul01-g/IntelliReview.git
cd IntelliReview/backend

# Initialize virtual environment and install dependencies
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# Migrate schema and boot the server
cp .env.example .env # Configure Postgres, Redis, and OpenAI endpoints
alembic upgrade head
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### 2. Frontend Dashboard via Vite
```bash
# Navigate to the frontend workspace (recently overhauled with Vite/Tailwind)
cd ../dashboard

# Install React dependencies and start the development server
npm install
npm run dev
```
> The premium web interface will be reliably served at `http://localhost:5173`.

---

## 🛠️ Usage & Operations

IntelliReview can be invoked in several ways depending on your CI/CD and developer workflows:

### 1. Direct Analysis via CLI
You can utilize the platform directly from any terminal to vet code instantly before pushing to version control.
```bash
# Analyze a specific project directory
intellireview analyze ./src --strict

# Generate a JSON output for CI pipelines
intellireview analyze ./backend --format=json > report.json
```

### 2. GitHub Pull Request Bot
Once installed via the GitHub App integration, IntelliReview will automatically subscribe to tracking events.
- Simply open a Pull Request.
- IntelliReview will post a top-level **Executive Summary** detailing the Technical Debt trajectory.
- The Engine will inject **Inline Diff Comments** explicitly alongside lines that trigger security or structural alarms.

### 3. MCP Agent Invocation
For users of tools like **Cursor** or **Claude Code**, configure your agent's MCP settings to point to the IntelliReview internal socket:
```json
{
  "mcpServers": {
    "intellireview": {
      "command": "python",
      "args": ["-m", "intellireview.mcp"]
    }
  }
}
```
*Your agent will now self-correct using IntelliReview's rule subsets.*

---

## 🗺️ Strategic Roadmap

- **Phase 1: Agentic Remediation** — Transitioning from posting passive inline GitHub PR comments to automatically opening secondary "fix" branches with applied diff patches.
- **Phase 2: IDE Gutter Integration** — Direct VS Code / JetBrains daemon integration, analyzing context buffers synchronously to prevent flawed code from ever reaching remote Git origins.
- **Phase 3: Multi-LLM Consensus Verification** — Injecting Mistral & Llama auxiliary verification nodes to vote on issues detected by the primary model, driving false-positive rates effectively to zero.

---

## 🤝 Contributing

We believe that code quality is a community-driven initiative. Whether you want to add a new AST language parser, tune the LangChain orchestrator, or improve the React dashboard:
1. **Fork** the repository and create your feature branch: `git checkout -b feature/amazing-feature`
2. **Commit** your changes adhering to conventional commits: `git commit -m 'feat: added amazing feature'`
3. **Push** to the branch and open a Pull Request.

Please review our `CONTRIBUTING.md` for our full development lifecycle and testing requirements.

---

## 📄 License

Distributed under the **Apache 2.0 License**. See `LICENSE` for more information.

---

*IntelliReview: Because even AI needs a senior engineer in its corner.*
