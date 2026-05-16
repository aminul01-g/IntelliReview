## Phase 0: Project scaffolding
- Create the exact directory structure shown in the user message.
- Initialize `pyproject.toml` (backend) and `package.json` (frontend).
- Add `.env.example` with all required variables:
DATABASE_URL=postgresql://user:pass@localhost/intellireview
REDIS_URL=redis://localhost:6379/0
SECRET_KEY=<generate>
GITHUB_CLIENT_ID=xxx
GITHUB_CLIENT_SECRET=xxx
GITHUB_WEBHOOK_SECRET=xxx
GOOGLE_API_KEY=xxx
HUGGINGFACE_API_KEY=xxx
MONGODB_URL=mongodb://localhost:27017 (optional)

text
- Configure `ruff`, `mypy`, `pytest`, `pre-commit`.

## Phase 1: Backend core (FastAPI)
- `api/main.py`: FastAPI app with CORS, middleware (auth, logging, rate limit), router includes `/auth`, `/webhooks`, `/analyses`, `/feedback`, `/projects`, `/admin`.
- `api/auth.py`: JWT creation/verification, OAuth with GitHub (device flow optional).
- `api/database.py`: SQLAlchemy async engine, session dependency, Alembic migrations.
- `api/models/`: all tables: User, Team, Project, Analysis, AuditLog, RuleTelemetry, SuggestionFeedback, OAuthDeviceCode, UserProfile.
- `api/schemas/`: Pydantic models for requests/responses.
- `api/routes/`: endpoints for submitting code for review, listing analyses, feedback (accept/reject), dashboard stats (Tech Debt Ratio over time).
- `api/middleware/`: AuthMiddleware, GitHubPermissionsMiddleware, ResilienceMiddleware (retry+circuitbreaker).
- `celery_app.py` – Celery instance with Redis broker.

## Phase 2: Core analysis engine (`analyzer/`)
- `parsers/`: AST parsers using `ast` (Python), `esprima` (JS), plus stubs for Java/C++ (can raise NotImplemented for now but structure ready).
- `detectors/`:
- SecurityDetector (wraps Bandit, plus custom rules for SQL injection, hardcoded secrets).
- AIPatternsDetector (detects overly‑confident comments, hallucinated APIs).
- AntiPatternsDetector (god functions, duplicate code via Radon).
- QualityDetector (complexity, maintainability index).
- `metrics/`: Tech Debt Ratio = (effort to fix issues) / total lines, aggregated per commit.
- `context/`: Diff mapper that compares current PR diff with previous analysis.
- `feedback/`:
- `severity_orchestrator.py`: combines config overrides (.intellireview.yml), rejection rate demotion, dataflow tracing, DESIGN.md constraints, semantic reachability.
- `learning_loop.py`: auto‑generates config suggestions when rule rejection >70% over ≥10 samples.
- `feedback_generator.py`: produces Markdown comments for PRs with “IntelliReview AI Audit” header.
- `rules/`: custom rule engine that loads YAML rules from a `rules/` folder.
- `utils/`: redaction of secrets before logging.

## Phase 3: AI/ML agents (`ml_models/`)
- `agents/orchestrator.py`: LangGraph workflow with nodes: `security_audit` → `performance_profiling` → `style_check` → `tech_debt_assessment`. Each node calls a specialized LLM (via LangChain chat models). Uses Google Generative AI (Gemini) or Hugging Face.
- `agents/tech_debt_agent.py`: estimates effort to fix debt.
- `generators/suggestion_generator.py`: produces actionable code snippets.
- `embeddings/code_embeddings.py`: stores vector embeddings of code chunks in PostgreSQL (pgvector) for semantic search.
- `pattern_learner.py`: reads `learned_patterns.json` from user feedback, updates rule weights.
- `context_analyzer.py`: uses embedding similarity to find similar past reviews.
- `code_smell_detector.py`: LLM‑based smell detection.

## Phase 4: Celery tasks (`api/tasks/`)
- `analysis_task.py`: receives a repo URL, commit SHA, or direct code snippet, triggers the full pipeline (parse → detect → AI agents → severity orchestration → store results → post PR comment).
- `rollup_task.py`: weekly aggregation of Tech Debt Ratio per project/team.

## Phase 5: Webhooks and MCP
- `api/routes/webhooks.py`: GitHub webhook endpoint – verifies signature, pushes to Celery, responds immediately.
- `api/mcp_server.py`: implements Model Context Protocol to allow IDEs (Cursor, VSCode) to request an audit of an entire project. Returns a Markdown report with per‑file metrics and AI review.

## Phase 6: CLI tool (`cli/cli.py`)
- Command `intellireview audit <path>` – runs same analysis locally, prints styled table with severity colors.
- Command `intellireview login` – device OAuth flow.
- Command `intellireview feedback submit` – for offline feedback.

## Phase 7: React frontend (`dashboard/`)
- Scaffold with Vite + React 18 + TypeScript + Tailwind.
- Implement `src/contexts/AuthContext.tsx` (JWT storage, login via GitHub).
- Routes: `/login`, `/dashboard`, `/review`, `/scan-history`, `/analytics`, `/settings`.
- Components:
- `MonacoEditor` for code input.
- `AnalysisResultsTable` (TanStack Table) with sort/filter, showing findings, severity, rule name, and accept/reject buttons.
- `TechDebtChart` (Recharts) showing TDR trend.
- `CommandPalette` (Radix UI) to quickly navigate/search analyses.
- Dark/light theme toggle using Tailwind dark mode class.
- API client (`src/lib/api.ts`) using Axios with request/response interceptors to add JWT and handle 401.
- React Query for data fetching (list analyses, submit analysis, submit feedback).
- Real‑time updates via WebSocket (FastAPI `WebSocketEndpoint`) for long‑running analyses.

## Phase 8: VSCode extension (`vscode-extension/`)
- Extension that calls the MCP server or REST API to audit currently opened file/project, displays results in a sidebar.

## Phase 9: testing
- Write unit tests for all `analyzer/` functions (pytest with fixtures).
- Mock external APIs (GitHub, LLM) in tests.
- Integration tests: spin up test database (SQLite in memory), test Celery task flow.
- e2e tests: Playwright for dashboard (login, submit code, see result, click accept/reject).
- Mutation testing on critical files (e.g., severity_orchestrator.py).

## Phase 10: Observability & operations
- Add Prometheus metrics endpoint (`/metrics`).
- Configure structlog for JSON logging with request ID.
- Add OpenTelemetry instrumentation for FastAPI, Celery, Redis, HTTP calls.
- Write a Grafana dashboard JSON (to be imported) for monitoring.
- Add liveness and readiness probes in Docker Compose.

## Phase 11: CI/CD & deployment
- Create `.github/workflows/ci.yml` – runs lint, typecheck, test, build images, push to Docker Hub (or ghcr).
- Create `Dockerfile.backend`, `Dockerfile.frontend`, `Dockerfile.worker`, `docker-compose.prod.yml` with nginx serving frontend and reverse‑proxying API.
- Write `deploy.sh` script that uses docker compose on a production VM (or provide Ansible playbook).
- Set up automatic database migrations (Alembic run as init container).

## Phase 12: Documentation
- `README.md`: features, quick start (docker compose up), environment variables, how to configure webhooks, how to add custom rules.
- `docs/architecture.md`: C4 diagrams (text descriptions acceptable), data flow, decision records.
- `docs/runbook.md`: troubleshooting steps for common issues.
- `docs/security.md`: threat model, secret rotation, data retention.
