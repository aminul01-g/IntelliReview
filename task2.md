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
├── hardware/ # NEW MODULE
│ ├── init.py
│ ├── manifest_schema.json # JSON schema for hardware manifest
│ ├── profile_manager.py # CRUD for HardwareProfile, component specs
│ ├── resource_estimator.py # LLM + heuristic RAM/Flash estimation
│ ├── circuit_simulator.py # Wokhi / LTspice client
│ ├── safety_rules.py # rules for voltage, current, pin conflicts
│ └── component_library.py # built‑in specs for common parts
├── ml_models/agents/
│ ├── hardware_planner.py # LangGraph node: decides which checks to run
│ ├── resource_estimation_agent.py # calls resource_estimator
│ ├── simulation_agent.py # calls circuit_simulator
│ └── hardware_reviewer.py # aggregates findings into review comments
├── api/
│ ├── routes/hardware.py # REST endpoints: CRUD for hardware profiles
│ ├── models/hardware.py # SQLAlchemy models (HardwareProfile, ComponentSpec, HardwareAudit)
│ └── schemas/hardware.py # Pydantic schemas for manifest validation
├── dashboard/src/pages/
│ └── HardwareProfiles.tsx # UI to upload/edit hardware manifest (JSON editor)
├── tests/hardware/ # unit + integration tests
└── migrations/ # Alembic revisions for new tables


# TASKS (execute in order)

## 1. Database models & migrations
- Create `HardwareProfile` model:
  - id, name, target_board (Arduino Uno/ESP32/etc.), manifest_json (JSONB), created_by, created_at.
- Create `ComponentSpec` model:
  - id, component_type, pin, voltage_min, voltage_max, current_max, protocol, notes.
- Create `HardwareAudit` model (inherits from AuditLog or standalone):
  - id, hardware_profile_id, analysis_id (FK to existing Analysis), findings (JSON), simulation_status, resource_estimate (JSON).
- Write Alembic migration.

## 2. Hardware manifest schema & validation
- Write `hardware/manifest_schema.json` (draft v1) with properties: board, components (array of {type, pin, voltage, current, protocol, datasheet_url}), power_budget_mA, sram_bytes, flash_bytes.
- Implement `profile_manager.py` – load, validate against schema, store in DB, retrieve by project/repo.

## 3. Resource estimation agent
- In `hardware/resource_estimator.py`:
  - Parse C/C++ code (using tree-sitter or regex + heuristics for embedded).
  - Estimate SRAM: sum of global variables, string literals, stack usage hints.
  - Estimate Flash: approximate compiled size by counting statements, loops, libraries.
  - Use Qwen‑2.5‑Coder 7B for complex patterns (function call chains, templates).
  - Return `{"ram_bytes": int, "flash_bytes": int, "confidence": float}`.

## 4. Circuit simulation integration
- `hardware/circuit_simulator.py`:
  - Build a client for Wokwi HTTP API (https://docs.wokwi.com/api).
  - Create a temporary circuit from manifest + code (extract pin writes, PWM, digital writes).
  - POST to Wokwi, wait for simulation (timeout 30s), parse output.
  - If Wokwi unavailable, fallback to static rule checker (no simulation).
  - Stub for LTspice (return “simulation not implemented”).

## 5. Safety rules engine
- `hardware/safety_rules.py`:
  - Rules defined as JSON: condition (e.g., `pin.voltage > component.max_voltage`), severity (critical/high/medium), message template.
  - Evaluate against manifest and detected code instructions (e.g., `analogWrite(pin, 255)`).

## 6. LangGraph agents integration
- Extend existing orchestrator (`ml_models/agents/orchestrator.py`) to include a new **HAMAD branch** triggered by a `hardware_profile_id` in the analysis request.
- New nodes (in `ml_models/agents/hardware_planner.py` etc.):
  - `hardware_planner`: decides which checks to run based on manifest.
  - `resource_estimation_agent`: calls resource_estimator.
  - `simulation_agent`: calls circuit_simulator.
  - `hardware_reviewer`: aggregates findings, produces structured output.
- Update the LangGraph state to include `hardware_findings`.

## 7. API endpoints
- `POST /api/v1/hardware/profiles` – create new hardware profile.
- `GET /api/v1/hardware/profiles/{id}` – get manifest.
- `PUT /api/v1/hardware/profiles/{id}` – update.
- `POST /api/v1/analyses/with-hardware` – submit code for review with optional hardware_profile_id.
- Extend existing `POST /webhooks/github` to detect hardware-related files (.ino, .pde, platformio.ini) and automatically match a hardware profile (by repo or by manifest in repo root).

## 8. Frontend (React)
- New page `/hardware`:
  - List hardware profiles.
  - Form/JSON editor to create/edit manifest (use Monaco editor with JSON schema validation).
- Extend analysis result view to show hardware findings tab (voltage violations, resource overages, simulation logs).

## 9. Celery task update
- Create new task `analyze_hardware_task` that:
  - Fetches manifest.
  - Runs resource estimation (LLM call).
  - Runs simulation (if enabled).
  - Evaluates safety rules.
  - Stores results in HardwareAudit.
  - Returns findings to main analysis task to be merged into final PR comment.

## 10. Testing & observability
- Unit tests for each rule, estimator, simulator mock.
- Integration test: full PR webhook with a sample manifest and Arduino code.
- Add Prometheus metrics: `hardware_estimation_duration_seconds`, `hardware_simulation_success_total`, `hardware_rule_violations_total`.
- Log all hardware audits to `hardware_audit_logs` table.

## 11. Documentation
- `docs/hardware.md`: how to write a hardware manifest, example for Arduino Uno + servo, how to set up Wokwi API key.
- `docs/hardware-rules.md`: list of safety rules and how to extend.

# OUTPUT FORMAT
Generate all new files (as listed above) with complete implementations. Do NOT remove or break existing IntelliReview functionality. Where external APIs require keys (Wokwi, Llama 3.1, Qwen), use environment variables: `WOKWI_API_KEY`, `LLAMA_API_BASE`, `QWEN_API_BASE` with sensible fallbacks (e.g., mock for development).

After writing all files, produce a summary:
- How to create a hardware profile via API or UI.
- Example manifest JSON for a servo + Arduino.
- Example `curl` to trigger a hardware‑aware review.
- How to configure the GitHub webhook to auto‑detect hardware manifests.

The final system must be **production‑ready** – all new endpoints tested, all new agents fault‑tolerant, and the 60‑second SLA enforced via Celery timeouts and async simulation limits.

Now begin extending IntelliReview with HAMAD.