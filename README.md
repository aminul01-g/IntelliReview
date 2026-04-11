---
title: IntelliReview
emoji: 🛡️
colorFrom: blue
colorTo: indigo
sdk: docker
pinned: false
app_port: 7860
---

<!-- markdownlint-disable MD033 -->

<div align="center">
  <img src="https://raw.githubusercontent.com/lucide-icons/lucide/main/icons/shield-check.svg" width="80" height="80" alt="IntelliReview Shield"/>
  <h1>🛡️ IntelliReview</h1>
  <p><strong>The Enterprise AI-Powered Code Review Ecosystem & Architectural Engine</strong></p>
  
  [![License](https://img.shields.io/badge/License-MIT-blue.svg?style=for-the-badge)](LICENSE)
  [![Python](https://img.shields.io/badge/Python-3.11+-ffd43b.svg?style=for-the-badge&logo=python&logoColor=blue)](https://python.org)
  [![FastAPI](https://img.shields.io/badge/FastAPI-0.104.0-009688.svg?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com)
  [![React](https://img.shields.io/badge/React-18.2.0-61dafb.svg?style=for-the-badge&logo=react&logoColor=black)](https://react.dev)
  [![Docker](https://img.shields.io/badge/Docker-Ready-2496ed.svg?style=for-the-badge&logo=docker&logoColor=white)](https://docker.com)
</div>

<br/>

> **IntelliReview** fuses strict AST (Abstract Syntax Tree) bounds with ultra-advanced Large Language Models (`DeepSeek-R1` & `Qwen3-32B`). Unlike naive AI wrappers, IntelliReview features **Diff-Scoped Reviews**, **False-Positive Suppression**, **Context Chunking**, and an **Active Feedback Loop** to maintain a high signal-to-noise ratio for professional engineering teams.

---

## ✨ Comprehensive Ecosystem

| 🧩 Component | 📝 Description | 🔌 Integration |
| :--- | :--- | :--- |
| **Deep Code Analyzer** | Multi-language AST bounds (Python, JS/TS, Java, C/C++) paired with zero-shot semantic deep-dives. | Backend Engine |
| **Agentic MCP Server** | Model Context Protocol exposing AI toolchains to Cursor / Claude Desktop. | `api/mcp_server.py` |
| **Diff-Scoped PR Reviewer**| Zero-touch GitHub Webhook CI/CD to natively comment **only on modified lines** with Auto-Fix patches. | `/api/v1/github` Webhook |
| **VS Code Extension** | Native IDE workflow that surfaces real-time diagnostics and squiggly warnings. | Editor Extension |
| **React Dashboard** | Telemetry tracking, False-Positive Feedback loops, and project architectural health maps. | Web Dashboard |
| **Terminal CLI** | Run code audits continuously inside your terminal natively. | CLI `intellireview` |

---

## 🔬 Enterprise-Grade Code Review Dynamics

IntelliReview was built to solve the core flaws of "naive AI reviewers" (hallucinations, context loss, and notification fatigue).

### 1. Context-Aware AI Engine (Chunking & Prompting)
Sending a 3,000-line file to an LLM will break its context window. IntelliReview employs **Adaptive Chunking**:
- **Qwen3-32B (The Mapper)**: Indexes the directory tree and configuration files (`package.json`, `requirements.txt`) to generate a global architectural map via our **Plan-First Protocol**.
- **DeepSeek-R1 (The Logic Engine)**: Receives mathematically bounded code chunks along with the `Qwen` structural map, ensuring logic refactoring respects global imports and state structures without context overflow.

### 2. Diff-Scoped PR Review
Flooding a Pull Request with complaints about pre-existing, untouched legacy code is the fastest way a tool gets uninstalled.
- The GitHub Webhook integration pulls **Unified Diffs**.
- IntelliReview maps AST boundaries to the specific diff ranges, ensuring the AI only flags vulnerabilities and anti-patterns **introduced in the active PR**.

### 3. False Positive Management & Telemetry
A code reviewer lives or dies by its Signal-to-Noise ratio.
- **Rule Whitelisting**: Use `.intellireview.yml` to define threshold overrides and globally silence noisy linters.
- **Suppression Comments**: Developers can use inline comments like `# intellireview: ignore` to suppress specific rules over fragile lines of code.
- **Active Feedback Loop**: The React Dashboard allows engineers to mark AI suggestions as "Accepted" or "Rejected". This telemetry feeds directly into `Pattern Learner`, dynamically tuning systemic thresholds and prompt strictness over time.

### 4. Robust Security Scanning (SAST)
Our security layer maps directly against the **OWASP Top 10**.
- **Secrets Detection**: Catches hardcoded AWS keys, RSA tokens, and hallucinated AI placeholder URLs via high-entropy regex and AST string traversal.
- **Vulnerability Checks**: Flags injection flows (SQLi, XSS vectors), unsafe deserialization, and path traversal mechanisms before the PR merges.

---

## 🚀 Quick Start

Ensure you have [Docker](https://docker.com) installed or Python 3.11+.

### 1. Environment Configuration

Clone the repository and bootstrap your local environment.

```bash
git clone https://github.com/yourusername/intelliReview.git
cd intelliReview
cp .env.example .env
```

Configure the `.env` securely. Minimal requirements:

```ini
HUGGINGFACE_API_KEY=hf_your_key_here
SECRET_KEY=generate_a_secure_random_key_here

# Required ML Engines
HUGGINGFACE_MODEL=deepseek-ai/DeepSeek-R1
HUGGINGFACE_CONTEXT_MODEL=Qwen/Qwen3-32B

# For GitHub PR Auto-Reviewer functionality:
GITHUB_TOKEN=ghp_your_personal_access_token
GITHUB_WEBHOOK_SECRET=your_secure_webhook_secret
```

### 2. Launch with Docker Compose

Spin up the entire microservice ecosystem (Postgres, MongoDB, Redis, API, Dashboard) via Docker:

```bash
docker-compose up -d
```

* **API:** `http://localhost:8000` (Docs: `http://localhost:8000/docs`)
* **Dashboard:** `http://localhost:3000`

---

## 📚 Advanced Integration Guides

<details>
<summary><b>🔌 1. FastMCP Server: Agentic IDE Workflows</b></summary>
<br/>

IntelliReview exposes its code analysis engine as a FastMCP server. This allows AI agents within Claude Desktop or Cursor to autonomously analyze and fix codebase issues using the `analyze_code` and `analyze_project` endpoints.

Add the following to your MCP configuration:
```json
{
  "mcpServers": {
    "intellireview": {
      "command": "python",
      "args": ["<absolute-path-to-repo>/api/mcp_server.py"],
      "env": {
         "HUGGINGFACE_API_KEY": "hf_your_api_key_here"
      }
    }
  }
}
```
</details>

<details>
<summary><b>🤖 2. GitHub PR Auto-Reviewer</b></summary>
<br/>

Our Zero-Touch Webhook integrates directly into your GitHub CI/CD:
1. Listens to `opened` and `synchronize` PR events.
2. Extracts the Unified Diff.
3. Generates Auto-Fix patches (` ```diff `) for lines specifically touched by the author.
4. Posts inline comments directly back via GitHub API.

**Setup**: Point your GitHub Webhook Payload URL to `https://your-domain.com/api/v1/webhooks/github` and set the secret matching your `.env`.
</details>

<details>
<summary><b>🛠️ 3. VS Code Native Extension</b></summary>
<br/>

Highlight security flaws natively in your IDE via squiggly lines.
1. `cd vscode-extension && npm install && npm run compile`
2. Press `F5` in VS Code to open the extension host.
3. In settings, set `intellireview.serverUrl` and your `apiToken`.
4. Run Command Panel: `IntelliReview: Analyze Current File`
</details>

---

## 💻 CLI Usage

The IntelliReview CLI provides a powerful terminal interface for local offline audits.

```bash
# Installation
pip install -e .

# Configure API endpoint mapping
intellireview config-set --key api_url --value http://localhost:8000
intellireview login

# Analyze a targeted file
intellireview analyze src/main.py

# Recursively crawl and audit a directory
intellireview analyze-dir src/ --recursive
```

---

## ⚙️ Custom Settings (`.intellireview.yml`)

Set custom thresholds and override global analyzers natively per project root:

```yaml
version: 1.0
analysis:
  languages:
    - python
    - javascript
  ignore:
    - node_modules/
    - tests/
  rules:
    complexity_threshold: 10
    max_function_length: 50
    # True false positive management
    severity_filter: ["critical", "high"] 
```

---

## 🔐 Auth & Enterprise Security Roadmap

IntelliReview currently utilizes JWT-based authentication combined with secure bcrypt password hashing via PostgreSQL user mapping.

**Coming in v2 (Enterprise):**
- **SSO/OAuth2 Integration**: Natively binding with Okta, Google Workspace, and GitHub Teams.
- **RBAC (Role-Based Access Control)**: Enforcing Org-level and Team-level repository scoping.
- **Comprehensive Audit Logs**: Tracking all telemetry, manual feedback acceptances, and configuration alterations.

---

## 🧪 Testing & Deployment

IntelliReview utilizes an extensive PyTest automation suite simulating true Multi-Language workflows.

```bash
# Run isolated Unit Tests
pytest tests/unit/

# Run End-To-End API simulation 
python test_e2e.py

# Fast-deploy scaling configs to Cloud
kubectl apply -f kubernetes/
```

<br/>

<div align="center">
  <p>🚀 Built with ❤️ using FastAPI, Hugging Face, React, and Python.</p>
  <p><a href="#-intellireview">⬆ Back to Top</a></p>
</div>
