# IntelliReview Security

## Threat Model
- **Insider**: Developer with read access could query embeddings. Mitigated by RBAC.
- **MITM**: All comms over HTTPS. Webhook signature verification prevents spoofing.
- **API Key Leak**: Secrets stored in `.env` and injected via K8s Secrets. No hardcoding.

## Secret Rotation
1. Update `.env` file with new keys.
2. Restart all containers: `docker-compose down && docker-compose up -d`.
3. Verify health: `curl http://localhost:8000/health`.

## Audit Logs
All state-changing actions are logged in `AuditLog` table via `api/models/audit.py`. Logs retained for 90 days by default.

## Data Retention
- **Analysis Results**: Retained for 1 year (configurable).
- **Feedback**: Retained indefinitely to power the learning loop.
- **Embeddings**: Retained as long as the project exists.