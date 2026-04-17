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
  <!-- [Image 1: IntelliReview Branding] -->
  <img src="docs/assets/branding.png" alt="IntelliReview Branding" width="600"/>

  <h1>🛡️ IntelliReview</h1>
  <p><em>AI-Powered Code Review Assistant</em></p>

  <!-- Badges integrated with SonarQube / DeepSource APIs (Placeholders) -->
  <p>
    <a href="#"><img src="https://img.shields.io/badge/build-passing-brightgreen.svg?style=for-the-badge" alt="Build Status"></a>
    <a href="#"><img src="https://img.shields.io/badge/coverage-94%25-success.svg?style=for-the-badge" alt="Code Coverage"></a>
    <a href="#"><img src="https://img.shields.io/badge/Health_Score-A-brightgreen.svg?style=for-the-badge" alt="Health Score"></a>
    <a href="#"><img src="https://img.shields.io/badge/integration-SonarQube-4E9BCD.svg?style=for-the-badge" alt="SonarQube"></a>
  </p>
</div>

## Table of Contents
1. [Executive Overview](#executive-overview)
2. [Core Module Deep-Dive](#core-module-deep-dive)
   - [Dashboard](#dashboard)
   - [Analysis Engine](#analysis-engine)
   - [Custom Rules Engine](#custom-rules-engine)
   - [Analysis History & Metrics](#analysis-history--metrics)
3. [Architectural Specifications](#architectural-specifications)
   - [Multi-Agent Orchestration](#multi-agent-orchestration)
   - [MCP Intelligence](#mcp-intelligence)
   - [GitHub App Lifecycle](#github-app-lifecycle)
   - [Technical Debt Management](#technical-debt-management)
4. [Installation & Setup](#installation--setup)
5. [Roadmap: Evolutionary Outlook](#roadmap-evolutionary-outlook)

---

## Executive Overview

IntelliReview is a context-aware ecosystem designed to transcend traditional linting mechanisms. By employing a **hybrid reasoning paradigm**, the platform fundamentally bridges the gap between structured rule-checking and artificial intelligence. 

The system utilizes a **Deterministic + Generative** approach:
- **Deterministic**: Extensively utilizes precise Abstract Syntax Tree (AST) parsing and predefined patterns to catch fundamental structural, style, and security flaws without hallucination.
- **Generative**: Deploys localized Large Language Models over mathematically bounded scopes to supply context-aware reviews, actionable diff patches, and security rationale for complex software architectures.

---

## Core Module Deep-Dive

### Dashboard
<!-- [Image 2: Dashboard] -->
![Dashboard Interface](docs/assets/dashboard.png)

The IntelliReview Dashboard provides immediate insights into repository velocity and structural integrity. Central to the dashboard are the **Health Score** and **Technical Debt** metrics, which accurately track the evolution of code quality over time. These continuously updated indicators highlight deteriorating modules, allowing engineering teams to make data-driven decisions on when to pivot from feature building to refactoring.

### Analysis Engine
<!-- [Images 3, 4, 5: Analysis Engine] -->
![Analysis Engine - Raw Code](docs/assets/analysis-raw.png)
<br/>
![Analysis Engine - Architecture](docs/assets/analysis-architecture.png)
<br/>
![Analysis Engine - Diff Review](docs/assets/analysis-diff.png)

The Analysis Engine supports diverse workflows designed to accommodate specific developer needs through three distinct input modes:
1. **Raw Code Pasting**: For immediate validation of snippets and functions during active development.
2. **Project-Wide Uploads**: For comprehensive local evaluation (spanning both structural file hierarchy and isolated logic).
3. **Diff Review**: Specialized mode mapped directly to standard `git diff` outputs, automatically scoping the analysis constraints precisely to the modified lines.

### Custom Rules Engine
<!-- [Image 6: Custom Rules Engine] -->
![Custom Rules Engine](docs/assets/custom-rules.png)

Project-specific standardization securely functions through the `.intellireview.yml` configuration system. This Custom Rules Engine enables technical leads and DevOps engineers to enforce strictly defined style guides and specialized security patterns dynamically. Instead of relying purely on generalized AI assertions, teams define precise regex or structural paradigms which the underlying engine applies natively during AST traversal.

### Analysis History & Metrics
<!-- [Images 7, 8: Analysis History & Metrics] -->
![Analysis History](docs/assets/analysis-history.png)
<br/>
![Longitudinal Metrics](docs/assets/analysis-metrics.png)

Focusing on measurable developer productivity, the History & Metrics modules offer longitudinal tracking mechanisms. Specifically, the system continually evaluates **Team Velocity** alongside **AI Suggestion Acceptance Rates**. Over cycles, this reveals the true utility and structural alignment of the AI propositions, continuously optimizing review parameters while providing high-level operational metrics to engineering stakeholders.

---

## Architectural Specifications

### Multi-Agent Orchestration
IntelliReview adopts an asynchronous orchestrator architecture using specialized LangChain-based worker agents. To conquer vast context windows while preventing hallucination, the orchestrator delegates complex evaluation loops to narrowly-scoped agents:
- **Security Agent**: Identifies vulnerabilities, tracking CWE compliance, and validates data sanitization.
- **Performance Agent**: Detects $O(n^2)$ degradations, memory leak potential, and optimal API payloads.
- **Architecture Agent**: Evaluates SOLID principle adherence, module coupling, and scalable abstractions.

### MCP Intelligence
By integrating a robust **Model Context Protocol (MCP)** server, IntelliReview gains direct, real-time programmatic access to fundamental codebase semantics. Crucial capabilities include:
- **AST-Based Indexing**: Structural comprehension of classes, interfaces, and function signatures.
- **Symbol Searching**: Pinpointing exact structural usages rather than probabilistic text generation.
- **Cross-File Dataflow Tracking**: Understanding state propagation, enabling the AI to flag systemic architectural flaws instead of single-file limitations.

### GitHub App Lifecycle
Security routing operates via a comprehensive GitHub App framework, enforcing stringent operational permissions:
- **JWT Identity Management**: Backend communication relies exclusively on mathematically validated JSON Web Tokens, decoupling identity state from susceptible cookie storage.
- **Installation-Level Access Tokens**: The App mints repository-scoped, short-lived tokens ensuring fine-grained, minimally invasive permissions strictly configured for `Pull Request` comment capabilities and codebase read access.

### Technical Debt Management
The platform utilizes quantitative formulas heavily integrated into TimescaleDB's tracking suite to deduce the **Health Score**. The core determination calculates the **Technical Debt Ratio (TDR)**:

$$ TDR = \frac{\text{RemediationCost}}{\text{DevelopmentCost}} $$

Whenever structural anomalies or code smells appear, the engine computes exact remediation hours against the aggregate development time required for that modular component, yielding an objective metric for evaluating maintenance requirements.

---

## Installation & Setup

### Prerequisites
- Node.js `18+`
- Python `3.11+`
- PostgreSQL (with TimescaleDB extension for longitudinal tracking)
- Redis (for Celery and Agent queuing)

### Backend Setup (FastAPI & Agents)
```bash
# 1. Clone & Enter backend directory
git clone https://github.com/aminul01-g/IntelliReview.git
cd IntelliReview

# 2. Virtual Environment Setup
python3.11 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt

# 3. Environment Variables
cp .env.example .env
# Edit .env to supply POSTGRES_URL, REDIS_URL, and LLM API Keys

# 4. Initialize Database and run the API
alembic upgrade head
uvicorn api.main:app --host 0.0.0.0 --port 8000 --reload
```

### Frontend Setup (React Dashboard)
```bash
# 1. Navigate to frontend module
cd frontend

# 2. Install dependencies
npm install

# 3. Start development server
npm run dev
```
> The React interface will natively bind to `http://localhost:3000` assuming standard port mapping.

---

## Roadmap: Evolutionary Outlook

To further reinforce continuous integration pipelines, upcoming major features focus on deployment rigidity and systemic autofixes:
- **IDE Extensions**: Direct gutter diagnostics and code lenses integrated into VS Code / JetBrains environments avoiding context-switching.
- **Hard-Blocking PR Gates**: CI actions enabling configurable thresholds (e.g., automatically blocking Pull Requests that exceed a `0.15` TDR rating).
- **Agentic Remediation (Autofix)**: Transitioning from purely diagnostic alerts to direct branch creations with auto-applicable deterministic patches via `diff` blocks.
