# CLAUDE.md – IntelliReview + HAMAD (Production AI Code Review Platform)

## YOUR ROLE
You are an elite senior software engineer. You will build **IntelliReview** – an enterprise‑grade AI code review platform with **HAMAD** (Hardware‑Aware Multi‑Agent DevOps) – from zero to production‑ready, bulletproof system.

**Absolute requirements**:
- All code must be **secure**, **tested**, **observable**, **documented**, **CI/CD ready**, and **deployable**.
- No shortcuts. Every feature described below must be fully implemented.
- You must follow the provided architecture, tech stack, and project structure exactly.
- Generate **all** files, configurations, documentation, and tests.

---

## PROJECT CONTEXT (What we’re building)

### Core goal
AI code review platform that acts as a Quality Gate for AI‑generated code, **plus** hardware‑aware validation for embedded systems (Arduino, ESP32, industrial PLCs).

### Features (must all be present)
1. **Multi‑agent AI reasoning** – Security, Performance, Style, Hardware (HAMAD).
2. **PR webhook integration** – GitHub/GitLab, async Celery tasks, 60‑second SLA.
3. **Tech Debt Ratio (TDR)** tracking over time.
4. **Learning loop** – from developer accept/reject feedback.
5. **Premium React dashboard** – dark/light theme, command palette, analytics, hardware profile editor.
6. **MCP server** – IDE integration (Cursor, VSCode).
7. **HAMAD** – hardware manifest, resource estimation (RAM/Flash), circuit simulation (Wokwi), safety rules, hardware‑aware review comments.

### Tech stack (exact)
- **Backend**: Python 3.12+, FastAPI, Uvicorn, Celery, Redis, SQLAlchemy, PostgreSQL, Alembic.
- **Code analysis**: Bandit, Pylint, Flake8, Radon, Esprima, GitPython.
- **AI/LLM**: LangChain, LangGraph, Google Generative AI, Hugging Face Hub, Llama 3.1 70B, Qwen‑2.5‑Coder 7B.
- **Frontend**: React 18, TypeScript, Vite, Tailwind, Radix UI, Monaco Editor, Recharts, TanStack Query + Table.
- **Infra**: Docker, Docker Compose, GitHub Actions, Prometheus, OpenTelemetry.
- **Hardware simulation**: Wokwi HTTP API (optional), fallback static rules.

---

## PRODUCTION QUALITY GATES (must satisfy)

### Security
- JWT authentication (python‑jose), bcrypt passwords, refresh tokens, OAuth2 GitHub.
- Rate limiting (slowapi/redis).
- Pydantic input validation – no raw SQL.
- Secrets via environment variables only.
- GitHub webhook signature verification.
- Audit log for all state‑changing actions (AuditLog table).

### Testing
- Unit tests: all analyzers, routes, models – **≥85% coverage**.
- Integration tests: API endpoints, Celery tasks, GitHub webhooks.
- e2e tests: React dashboard with Playwright.
- Mutation testing on critical logic (severity_orchestrator, resource_estimator).

### Observability
- Structured JSON logs with request ID.
- Prometheus metrics: request count, latency, error rate, LLM duration, queue size, hardware simulation duration.
- OpenTelemetry traces (FastAPI → Celery → LLM → DB).
- Health endpoints: `/health`, `/ready`.

### CI/CD & Deployment
- GitHub Actions: lint (ruff, mypy), test, build, push to registry, deploy to staging/prod.
- Multi‑stage Dockerfiles (backend, frontend, celery‑worker, redis, postgres).
- Docker Compose for local dev.
- Terraform or plain Docker deployment to a cloud VM.

### Reliability
- Celery retries with exponential backoff.
- Circuit breakers for LLM API calls (tenacity).
- Graceful shutdown.
- Idempotent webhook processing.

### Documentation
- README (setup, env vars, run instructions, webhook config).
- API docs (Swagger/ReDoc auto‑generated).
- Architecture Decision Records (ADRs) in `docs/adr/`.
- Runbook for common failures.
- `docs/hardware.md` – how to write manifests, Wokwi setup.

---

## DIRECTORY STRUCTURE (create exactly this)
intellireview/
├── api/ # FastAPI backend
│ ├── main.py
│ ├── auth.py
│ ├── database.py
│ ├── celery_app.py
│ ├── mcp_server.py
│ ├── models/ # SQLAlchemy models
│ ├── schemas/ # Pydantic
│ ├── routes/ # analysis, auth, webhooks, hardware, feedback, metrics
│ └── middleware/ # auth, rate limit, resilience
├── analyzer/ # Core analysis engine
│ ├── parsers/ # AST parsers (Python, JS, C/C++ for HAMAD)
│ ├── detectors/ # security, quality, ai_patterns, antipatterns
│ ├── metrics/ # complexity, duplication, TDR
│ ├── context/ # AST diff mapper
│ ├── feedback/ # severity orchestrator, learning loop
│ └── rules/ # custom rule engine
├── hardware/ # HAMAD module (new)
│ ├── manifest_schema.json
│ ├── profile_manager.py
│ ├── resource_estimator.py
│ ├── circuit_simulator.py
│ ├── safety_rules.py
│ └── component_library.py
├── ml_models/ # AI/ML components
│ ├── agents/ # LangGraph nodes
│ │ ├── orchestrator.py
│ │ ├── hardware_planner.py
│ │ ├── resource_estimation_agent.py
│ │ ├── simulation_agent.py
│ │ └── hardware_reviewer.py
│ ├── generators/
│ ├── embeddings/
│ └── pattern_learner.py
├── dashboard/ # React frontend
│ ├── src/
│ │ ├── pages/ # Dashboard, ReviewEngine, ScanHistory, HardwareProfiles
│ │ ├── components/
│ │ ├── contexts/ # Auth, Theme
│ │ └── lib/api.ts
│ └── vite.config.ts
├── cli/ # CLI tools
├── config/ # Settings (pydantic-settings)
├── tests/ # unit, integration, e2e, fixtures
├── integrations/ # VSCode extension, MCP
├── scripts/ # seed data, benchmark
├── docs/ # adr, hardware.md, runbook.md
├── .github/workflows/ # CI/CD
├── docker-compose.yml
├── Dockerfile.backend
├── Dockerfile.frontend
└── Dockerfile.worker


---

## EXECUTION TASKS (do in order, verify each phase)

### Phase 0: Scaffolding & configuration
- Create directory structure as above.
- Create `pyproject.toml` (backend) with dependencies: fastapi, uvicorn, sqlalchemy, alembic, celery, redis, langchain, langgraph, google-generativeai, huggingface_hub, bandit, pylint, flake8, radon, esprima, gitpython, python-jose, passlib, pydantic-settings, structlog, prometheus-client, opentelemetry-api, opentelemetry-instrumentation-fastapi, tenacity, pytest, pytest-cov, mutmut, etc.
- Create `dashboard/package.json` with React 18, TypeScript, Vite, Tailwind, Radix UI, lucide-react, recharts, @tanstack/react-query, @tanstack/react-table, axios, react-router-dom, monaco-editor, react-markdown.
- Create `.env.example` with all required keys (DATABASE_URL, REDIS_URL, SECRET_KEY, GITHUB_* keys, GOOGLE_API_KEY, HUGGINGFACE_API_KEY, WOKWI_API_KEY, LLAMA_API_BASE, QWEN_API_BASE).
- Configure ruff, mypy, pre-commit.

### Phase 1: Database & models (SQLAlchemy + Alembic)
- `api/models/`:
  - `User`, `Team`, `Project`, `Analysis`, `AuditLog`, `RuleTelemetry`, `SuggestionFeedback`, `OAuthDeviceCode`, `UserProfile`.
  - **HAMAD**: `HardwareProfile` (id, name, target_board, manifest_json, created_by), `ComponentSpec`, `HardwareAudit`.
- Write Alembic migration (initial).
- `api/database.py` – async engine, session dependency.

### Phase 2: FastAPI backend core
- `api/main.py` – CORS, middleware (logging, auth, rate limit), include routers.
- `api/auth.py` – JWT + GitHub OAuth, refresh tokens.
- `api/routes/`:
  - `auth.py`, `analyses.py`, `webhooks.py`, `feedback.py`, `projects.py`, `metrics.py`, `hardware.py`.
- `api/middleware/` – auth, rate limit, resilience (retry+circuitbreaker).
- Health endpoints (`/health`, `/ready`).

### Phase 3: Analysis engine (deterministic)
- `analyzer/parsers/` – Python (ast), JS (esprima), C/C++ (tree-sitter or pycparser stub).
- `analyzer/detectors/` – implement SecurityDetector (Bandit), QualityDetector (Radon), AIPatternsDetector, AntiPatternsDetector.
- `analyzer/metrics/` – Tech Debt Ratio.
- `analyzer/context/ast_diff_mapper.py` – compare two ASTs.
- `analyzer/feedback/severity_orchestrator.py` – combine config, rejection rates, dataflow.
- `analyzer/feedback/learning_loop.py` – auto‑adjust rules after >70% rejection over ≥10 samples.
- `analyzer/feedback/feedback_generator.py` – produce PR comments.

### Phase 4: AI agents (LangGraph)
- `ml_models/agents/orchestrator.py` – LangGraph workflow: security_audit → performance_profiling → style_check → tech_debt_assessment → (if hardware manifest) hardware_planner.
- `ml_models/agents/hardware_planner.py` – decide which hardware checks to run.
- `ml_models/agents/resource_estimation_agent.py` – calls `hardware/resource_estimator.py` (LLM + heuristics).
- `ml_models/agents/simulation_agent.py` – calls `hardware/circuit_simulator.py` (Wokwi API).
- `ml_models/agents/hardware_reviewer.py` – aggregate findings into Markdown.
- `ml_models/pattern_learner.py` – persist learned patterns from feedback.

### Phase 5: HAMAD hardware validation (full)
- `hardware/manifest_schema.json` – JSON schema for manifest.
- `hardware/profile_manager.py` – CRUD, validation, retrieval.
- `hardware/resource_estimator.py` – estimate RAM/Flash from C/C++ code using Qwen 7B + heuristics.
- `hardware/circuit_simulator.py` – Wokwi client with timeout (30s), fallback to static rule evaluation.
- `hardware/safety_rules.py` – evaluate voltage, current, pin conflicts against manifest and code.
- `hardware/component_library.py` – built‑in specs for common components (servo, LED, etc.).

### Phase 6: Celery tasks
- `api/tasks/analysis_task.py` – orchestrates full analysis (static + AI + hardware) with timeout, retries.
- `api/tasks/hardware_task.py` – separate task for hardware‑only analysis (called by orchestrator).
- `api/celery_app.py` – Celery app with Redis broker, result backend.

### Phase 7: Webhooks & MCP
- `api/routes/webhooks.py` – GitHub endpoint: verify signature, push to Celery, return 202. Support PR events.
- `api/mcp_server.py` – MCP server for IDE integration (project audit).

### Phase 8: React frontend
- Scaffold with Vite + React + TypeScript + Tailwind.
- `src/contexts/AuthContext.tsx`, `ThemeContext.tsx`.
- Pages: Login, Dashboard (metrics TDR chart), ReviewEngine (Monaco editor + submit), ScanHistory, HardwareProfiles (JSON editor with schema validation), Analytics.
- Components: CommandPalette (⌘K), AnalysisResultsTable, HardwareFindingsTab.
- API client (axios) with JWT interceptor.
- React Query for data fetching.
- Dark/light theme (Tailwind `dark:` class).

### Phase 9: CLI tool
- `cli/cli.py` – commands: `audit <path>`, `login`, `hardware profile upload <file>`.

### Phase 10: Testing
- Unit tests for each detector, estimator, rule, agent.
- Integration tests: fake GitHub webhook, Celery task with mocked LLM.
- e2e tests: Playwright for login → submit code → see results → accept/reject.
- Mutation tests on `severity_orchestrator.py` and `resource_estimator.py`.

### Phase 11: Observability & CI/CD
- Add `api/metrics.py` – Prometheus endpoint.
- Configure structlog + OpenTelemetry.
- Create `.github/workflows/ci.yml` – lint, typecheck, test, build images, push to ghcr.
- Dockerfiles (backend, worker, frontend) and `docker-compose.prod.yml`.
- Healthcheck probes.

### Phase 12: Documentation
- `README.md` – exactly how to start (docker-compose up), env vars, webhook setup.
- `docs/hardware.md` – manifest example, Wokwi integration, custom rules.
- `docs/runbook.md` – common failures and fixes.
- `docs/adr/` – decisions (e.g., why LangGraph, why Celery, why Wokwi).

---

## OUTPUT FORMAT FOR THE AGENT

You will generate **all files** listed above, with complete, runnable code. When a file is large, split into logical parts but ensure it is functional. Use comments for TODO stubs only for non‑critical external APIs (e.g., LTspice) – but the core must work with mocks.

After writing all files, produce a final summary that includes:
- Exact commands to start the entire stack (docker-compose up).
- How to run tests.
- Example `curl` to trigger a hardware‑aware review.
- Example hardware manifest JSON.
- How to configure a GitHub App for webhooks.

**Do not skip any requirement. Do not leave security holes. All environment‑specific values must be read from environment variables, never hardcoded.**

Now begin building IntelliReview with HAMAD.