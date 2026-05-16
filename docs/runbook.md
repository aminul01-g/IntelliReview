# IntelliReview Runbook

## Common Failures

### LLM API Failures
**Symptom**: Analysis fails with "Upstream 429" or "503 Service Unavailable".

**Mitigation**:
1. Check circuit breaker status in logs.
2. Fallback to deterministic rules (Bandit, Pylint) is automatic.
3. If persistent, rotate `GOOGLE_API_KEY` or `HUGGINGFACE_API_KEY`.

### Database Connection Lost
**Symptom**: 500 errors on `/api/v1/analysis/analyze`.

**Fix**:
```bash
# Check Postgres Pod
kubectl exec -it postgres-0 -- pg_isready

# Restart Backend
kubectl rollout restart deployment intellireview-backend
```

### Stuck Celery Tasks
**Symptom**: Queue depth (`/api/v1/queue_status`) keeps growing.

**Fix**:
```bash
# Inspect active tasks
celery -A api.celery_app inspect active

# Purge queue (DANGEROUS - only for unblocking)
celery -A api.celery_app purge
```

## Backup & Restore
```bash
# Backup
pg_dump -U postgres intellireview > backup.sql

# Restore
psql -U postgres intellireview < backup.sql
```