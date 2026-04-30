---
title: IntelliReview
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
app_port: 7860
---

<div align="center">
  <img src="./dashboard/public/vite.svg" alt="IntelliReview Logo" width="100" />
  <h1>IntelliReview</h1>
  <p><strong>The Quality Gate for AI-Generated Code</strong></p>
  <p>An enterprise-grade, agentic code review platform that combines deterministic static analysis with multi-model AI reasoning to detect vulnerabilities, track technical debt, and enforce architectural standards in real-time.</p>
</div>

<hr />

## 🌟 Overview

The software development lifecycle has fundamentally changed. AI coding assistants (like Copilot, Cursor, and ChatGPT) have dramatically accelerated code generation, allowing teams to ship features faster than ever. However, this speed comes at a cost: AI models frequently hallucinate, introduce subtle security vulnerabilities (like SQL injection or insecure API configurations), and accumulate architectural "technical debt" by ignoring enterprise-specific design patterns.

**IntelliReview** is designed to solve this exact problem. It acts as an automated, highly intelligent **Quality Gate** that sits between code generation and deployment. Instead of relying purely on simple linting, IntelliReview uses a **Hybrid Reasoning Engine** that pairs deterministic AST (Abstract Syntax Tree) parsing with context-aware, specialized LLM agents. It automatically reviews Pull Requests, filters false positives, suggests actionable fixes, and learns from your team's feedback to continuously improve its accuracy.

## ✨ Key Features

- **🤖 Hybrid Reasoning Engine:** Fuses the precision of deterministic static analysis (linters/AST parsers) with the semantic understanding of Large Language Models to catch bugs that traditional tools miss.
- **🛡️ Severity Orchestrator:** A multi-agent consensus algorithm that accurately categorizes issues (INFO, LOW, MEDIUM, HIGH, CRITICAL) and aggressively filters out noise and false positives.
- **🔄 Continuous Learning Loop:** The system learns organically. When developers accept or reject AI suggestions, the system updates its `rule_telemetry` to adjust prompt context and rule weights dynamically over time.
- **📊 Technical Debt Tracking:** Quantifies maintenance burden by calculating a longitudinal `Tech Debt Ratio (TDR)` across all projects and teams.
- **🎨 Premium Dashboard:** A sleek, dynamic React dashboard with a dark/light mode Theme Engine, a global command palette (⌘K) for rapid navigation, and exportable data capabilities (Markdown/JSON).
- **🔌 MCP Integration:** Built-in support for the Model Context Protocol (MCP), allowing seamless integration with IDEs and other local agentic workflows.

---

## 📸 Dashboard Gallery

<div align="center">
  <img src="./docs/assets/animated-login.png" alt="Animated Typewriter Login Demo" width="800" />
  <p><em>Real-time typewriter code analysis demo detecting vulnerabilities live.</em></p>

  <img src="./docs/assets/dashboard-dark.png" alt="Dark Mode Dashboard" width="800" />
  <p><em>Premium Command Center tracking longitudinal telemetry and system health.</em></p>

  <img src="./docs/assets/command-palette.png" alt="Command Palette" width="800" />
  <p><em>Global fuzzy-search Command Palette (⌘K) for rapid platform navigation.</em></p>
  
  <img src="./docs/assets/dashboard-light.png" alt="Light Mode Dashboard" width="800" />
  <p><em>Dynamic Theme Engine seamlessly switching the UI to light mode.</em></p>
</div>

---

## 🏗️ Architecture

IntelliReview operates on a highly scalable, event-driven architecture designed to process thousands of lines of code efficiently:

1. **API Gateway & Orchestrator:** Receives code snippets or GitHub/GitLab webhooks. It handles authentication, project mapping, and manages the lifecycle of an `Analysis` job.
2. **Parser Worker (Deterministic Phase):** Extracts raw code, generates AST diffs, and maps exact line numbers. It extracts semantic context (functions, classes, dependencies) to feed to the AI.
3. **Agentic Review Engine (Probabilistic Phase):** Specialized LLM agents (e.g., a "Security Agent", a "Performance Agent", a "Style Agent") evaluate the code context. 
4. **Severity & Consensus Node:** Aggregates findings from all agents, resolves conflicts, and assigns confidence scores before committing the results to the database.
5. **Learning Subsystem:** Processes developer feedback asynchronously to update the global telemetry matrix.

## 🧩 System Components

- **Backend (`api/`):** A high-performance Python FastAPI server acting as the central nervous system.
- **Frontend (`dashboard/`):** A rich React Single Page Application (SPA) providing thesis-grade data visualization.
- **Workers:** Asynchronous background tasks (simulated or Celery-based depending on scale) that handle heavy LLM inference without blocking the API.
- **MCP Server:** An implementation of the Model Context Protocol that allows external IDE tools to query IntelliReview's historical scan data and rulesets.

## 💻 Tech Stack

**Backend & AI Orchestration:**
- Python 3.10+
- FastAPI (High-performance async API)
- SQLAlchemy (ORM)
- SQLite (Local fallback) / PostgreSQL (Production)
- LangChain & Hugging Face Hub (LLM Orchestration / Open-source models)

**Frontend & UX:**
- React 18 & Vite
- TypeScript
- Tailwind CSS (Styling & Theme Engine)
- Recharts (Data Visualizations)
- Lucide React (Icons)
- Radix UI (Accessible primitive components)

---

## 🚀 Getting Started

### Prerequisites
- Python 3.10 or higher
- Node.js 18 or higher
- Hugging Face API Token (for LLM analysis)

### Installation

1. **Clone the repository:**
   ```bash
   git clone https://github.com/your-org/intellireview.git
   cd intellireview
   ```

2. **Backend Setup:**
   ```bash
   # Create and activate virtual environment
   python -m venv .venv
   source .venv/bin/activate  # On Windows use: .venv\Scripts\activate

   # Install dependencies
   pip install -r requirements.txt

   # Set environment variables
   export HUGGINGFACEHUB_API_TOKEN="your_hf_token_here"
   export JWT_SECRET="your_jwt_secret"
   ```

3. **Frontend Setup:**
   ```bash
   cd dashboard
   npm install
   npm run build
   cd ..
   ```

4. **Running the Unified Server:**
   ```bash
   # Start the FastAPI server (which automatically serves the built React frontend)
   python -m uvicorn api.main:app --host 0.0.0.0 --port 7860
   ```

5. **Access the Application:**
   Open your browser and navigate to `http://localhost:7860`.
   - **Default Admin Login:** Username: `admin` / Password: `admin123`

---

## 📖 Usage

### API Endpoints
IntelliReview exposes a comprehensive REST API. Swagger documentation is available at `http://localhost:7860/docs`.
- `POST /api/v1/analysis/analyze`: Submit code snippets, files, or entire project zip files for immediate AI review.
- `GET /api/v1/analysis/history`: Retrieve paginated past scans and reports.
- `POST /api/v1/analysis/{analysis_id}/feedback`: Submit accept/reject feedback on specific findings to train the learning loop.

### Dashboard Operations
The dashboard allows Engineering Managers and Security Researchers to:
- **Analyze Code:** Paste raw code or upload files directly into the Review Engine.
- **Track Metrics:** Monitor Team Velocity and AI Suggestion Acceptance rates over time.
- **Export Reports:** Generate downloadable Markdown and JSON analysis reports directly from the Scan History view.

### Webhook Setup (GitHub/GitLab)
Configure your CI/CD pipeline (e.g., GitHub Actions) to send Pull Request payload events to IntelliReview's `/api/v1/analysis/analyze` endpoint. The platform will automatically extract diffs, run the review agents, and can be configured to post comments directly back to the PR.

### MCP Integration
IntelliReview serves as an MCP resource. You can configure your local Cursor or VSCode agent to connect to the IntelliReview MCP server, allowing your local editor agent to check code against your organization's centrally managed IntelliReview rulesets before you even commit.

---

## 🧠 How It Works

1. **AST Diff Mapping:** When code is submitted, IntelliReview doesn't just pass strings to an LLM. It parses the Abstract Syntax Tree (AST) to understand the structure. If it's a pull request, it maps the exact line changes.
2. **Agentic Orchestration:** The code context is distributed to a swarm of specialized LLM agents. A "Security Expert" agent looks for OWASP Top 10 vulnerabilities, while a "Clean Code Expert" evaluates maintainability.
3. **Severity Orchestrator:** The responses from the agents are aggregated. The orchestrator checks for consensus. If an issue is flagged as `CRITICAL`, the system requires a high confidence score to avoid blocking builds with false positives.
4. **Learning Loop:** As developers review the findings, they can click "Accept" or "Reject". This telemetry is fed back into the system, dynamically adjusting the prompt contexts and rule heuristics for future scans.

## 📈 Evaluation & Metrics

IntelliReview quantifies codebase health using a proprietary **Tech Debt Ratio (TDR)**. 
- **TDR Definition:** A dynamic score based on the severity of unaddressed issues, the cyclomatic complexity of the affected code, and the historical velocity of the team in addressing technical debt.
- **Feedback Loop Effectiveness:** The dashboard tracks the "AI Suggestion Acceptance Rate." A rising acceptance rate indicates the Continuous Learning Loop is successfully tuning the model's output to match the specific architectural preferences of your team.

---

## 🛣️ Roadmap

The strategic vision for IntelliReview is divided into four distinct phases:

- **Phase 1: Foundation (Current)**
  - Core API engine, Hybrid Reasoning, multi-agent orchestrator, premium React dashboard, SQLite persistence, and basic report generation.
- **Phase 2: Scale & Integrate**
  - Advanced CI/CD integration plugins (GitHub Actions, GitLab CI bots).
  - Production PostgreSQL migration and Redis caching layer.
  - Expanded MCP toolset for deep IDE integration.
- **Phase 3: Deep Customization**
  - Custom fine-tuned local models (Llama 3 / Mistral) to completely eliminate data egress.
  - Enterprise SSO/SAML support.
  - Cross-repository dependency and vulnerability tracking.
- **Phase 4: Autonomous Operations**
  - Autonomous remediation agents capable of automatically generating Pull Requests to fix detected issues.
  - Zero-configuration auto-scaling infrastructure.

---

## 🤝 Contributing

We welcome contributions from the community! Please see our `CONTRIBUTING.md` file for guidelines on how to submit pull requests, report bugs, and suggest architectural enhancements.

## 📄 License

This project is licensed under the MIT License - see the `LICENSE` file for details.

## Acknowledgements

- Built with modern tooling including **FastAPI**, **React**, **Vite**, and **Tailwind CSS**.
- Powered by open-weight models via **Hugging Face** and orchestration by **LangChain**.
- UI primitives inspired by **shadcn/ui** and **Lucide Icons**.
