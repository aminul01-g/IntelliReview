# IntelliReview Architecture

## C4 Model

### Level 1: System Context
IntelliReview sits between GitHub/GitLab repositories and the development team's IDE. It receives code via webhooks or direct API, analyzes it using static analysis + AI agents, and provides feedback to the PR/Commit.

### Level 2: Containers
- **API Server (FastAPI)**: Handles auth, REST endpoints, WebSocket for live progress.
- **Celery Workers**: Execute long-running analysis tasks asynchronously.
- **React Dashboard**: Single Page Application for visualizing metrics and feedback.
- **MCP Server**: Protocol bridge for IDE integration (VSCode/Cursor).
- **PostgreSQL + pgvector**: Stores users, projects, analysis results, and code embeddings.
- **Redis**: Message broker for Celery and rate limiting.

### Level 3: Components
- `analyzer/detectors/`: Security, Quality, AI-Pattern, Anti-Pattern detectors.
- `ml_models/agents/`: LangGraph orchestrator for AI reasoning.
- `analyzer/feedback/`: Severity orchestration and learning loop.

## Data Flow
1. **Webhook Trigger**: GitHub sends `pull_request` event.
2. **FastAPI** validates signature, enqueues Celery task.
3. **Celery Worker**: Parses code → Runs detectors → Invokes AI Agents → Scores severity.
4. **Result Storage**: Persists to PostgreSQL + generates embeddings for pgvector.
5. **PR Comment**: Posts "IntelliReview AI Audit" markdown result.

## Decision Records (ADRs)
- **ADR-001**: Use Celery + Redis for async processing (SLA requirement > 60s).
- **ADR-002**: Use LangGraph for multi-agent AI orchestration.
- **ADR-003**: Use pgvector for semantic code search and duplicate detection.
- **ADR-004**: Use SlowAPI for rate limiting.