# IntelliReview Operations Runbook

> **Last updated:** 2026-05-20  
> **Maintainer:** IntelliReview Platform Team

---

## Table of Contents

1. [Redis Failure](#1-redis-failure)
2. [LLM API Outage](#2-llm-api-outage)
3. [Database Backup & Restore](#3-database-backup--restore)
4. [Secret Rotation](#4-secret-rotation)
5. [Stuck Celery Tasks](#5-stuck-celery-tasks)
6. [General Troubleshooting](#6-general-troubleshooting)

---

## 1. Redis Failure

### Symptoms
- `/api/v1/queue_status/status` returns `{"status": "degraded", "redis_available": false}`
- `/health/ready` returns `{"status": "ready", "redis": "unavailable"}`
- Celery tasks stuck in `PENDING`; uploads queue but never process
- Startup logs show: `⚠️ Redis is NOT reachable at <REDIS_URL>`

### Impact
- **Analysis queue**: New file uploads fall back to local `BackgroundTasks` (single-threaded, no retries)
- **Celery workers**: Idle — cannot fetch tasks
- **Rate limiting (Redis-backed)**: May fall back to in-memory counters

### Diagnosis

```bash
# 1. Check Redis container health
docker ps --filter name=redis
docker logs intellireview_redis --tail 50

# 2. Direct connectivity test
redis-cli -u "$REDIS_URL" PING

# 3. Check memory usage (common cause of OOM kills)
redis-cli -u "$REDIS_URL" INFO memory | grep used_memory_human

# 4. Kubernetes
kubectl get pods -l app=redis
kubectl logs -l app=redis --tail=100
```

### Resolution

| Scenario | Action |
|---|---|
| **Redis container crashed** | `docker restart intellireview_redis` or `kubectl rollout restart statefulset/redis` |
| **OOM killed** | Increase `maxmemory` in `redis.conf`; set eviction policy: `maxmemory-policy allkeys-lru` |
| **Network partition** | Verify both API and Redis are on the same Docker network: `docker network inspect intellireview_network` |
| **Corrupt AOF file** | `redis-check-aof --fix /data/appendonly.aof` then restart |

### Post-Recovery Verification

```bash
# Verify API can reach Redis
curl -s http://localhost:8000/health/ready | jq .

# Verify queue processing resumes
curl -s http://localhost:8000/api/v1/queue_status/status -H "Authorization: Bearer $TOKEN" | jq .
```

### Prevention
- Set up Redis Sentinel or Cluster for HA
- Monitor `analysis_queue_size` Prometheus gauge; alert if > 50 for > 5 minutes
- Ensure `REDIS_URL` env var is set consistently across all services

---

## 2. LLM API Outage

### Symptoms
- Analysis completes but `ai_overview` issue is missing or shows fallback text
- Logs show `429 Too Many Requests` or `503 Service Unavailable` from upstream LLM
- `/api/v1/research/hypothesize-fix` returns 500
- `LLMResilienceMiddleware` circuit breaker tripped (logged as WARNING)

### Impact
- **Code analysis**: Static analysis (Bandit, Pylint, custom rules) continues normally
- **AI suggestions**: Fallback to `"Could not generate suggestion."` string
- **AI overview**: Gracefully degraded — no AI summary injected
- **Auto-fix patches**: Not generated

### Diagnosis

```bash
# 1. Check LLM provider status pages
# - Google AI: https://status.cloud.google.com/
# - HuggingFace: https://status.huggingface.co/

# 2. Check API key validity
curl -s https://generativelanguage.googleapis.com/v1beta/models?key=$GOOGLE_API_KEY | head -5

# 3. Check rate limit headers in recent logs
grep -i "429\|rate.limit\|quota" logs/api.log | tail -20

# 4. Check circuit breaker state
grep -i "circuit\|resilience\|LLMResilience" logs/api.log | tail -20
```

### Resolution

| Scenario | Action |
|---|---|
| **Rate limited (429)** | Wait for quota reset (usually 1 minute); reduce `ai_limit` in analysis route |
| **API key expired** | Rotate key (see [Secret Rotation](#4-secret-rotation)) |
| **Provider outage** | Switch `LLM_PROVIDER` env var: `huggingface` → `google` or vice versa |
| **Persistent failures** | Set `HUGGINGFACE_API_KEY=""` to disable LLM; static analysis continues |

### Post-Recovery
```bash
# Verify LLM is functional
curl -s http://localhost:8000/api/v1/research/hypothesize-fix \
  -X POST \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"problem_statement": "test connectivity"}' | jq .hypothesis
```

### Prevention
- Monitor `llm_call_duration_seconds` histogram; alert if p99 > 30s
- Monitor `celery_tasks_total{status="failure"}` counter
- Keep a secondary LLM provider configured as fallback

---

## 3. Database Backup & Restore

### PostgreSQL (Production)

#### Automated Daily Backup

```bash
#!/bin/bash
# cron: 0 2 * * * /app/scripts/backup_db.sh
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="intellireview_backup_${TIMESTAMP}.sql.gz"

pg_dump -h "$POSTGRES_HOST" -U "$POSTGRES_USER" -d "$POSTGRES_DB" \
  --format=custom --compress=9 \
  -f "/backups/${BACKUP_FILE}"

# Retain only last 30 days
find /backups -name "intellireview_backup_*.sql.gz" -mtime +30 -delete

echo "Backup completed: ${BACKUP_FILE}"
```

#### Manual Backup

```bash
# Docker Compose
docker exec intellireview_postgres \
  pg_dump -U intellireview intellireview_db > backup_$(date +%Y%m%d).sql

# Kubernetes
kubectl exec postgres-0 -- \
  pg_dump -U intellireview intellireview_db > backup_$(date +%Y%m%d).sql
```

#### Restore

```bash
# 1. Stop the API to prevent writes
docker stop intellireview_api intellireview_celery

# 2. Restore
docker exec -i intellireview_postgres \
  psql -U intellireview intellireview_db < backup_20260520.sql

# 3. Restart services
docker start intellireview_api intellireview_celery
```

### SQLite (Development / HuggingFace Spaces)

```bash
# Backup
cp sqlite.db sqlite.db.bak.$(date +%Y%m%d)

# Restore
cp sqlite.db.bak.20260520 sqlite.db
```

### MongoDB (Analysis Documents)

```bash
# Backup
mongodump --uri="$MONGODB_URL" --db=intellireview_analysis --out=/backups/mongo_$(date +%Y%m%d)

# Restore
mongorestore --uri="$MONGODB_URL" --db=intellireview_analysis /backups/mongo_20260520/intellireview_analysis
```

---

## 4. Secret Rotation

### Which Secrets Exist

| Secret | Env Var | Where Used |
|---|---|---|
| JWT signing key | `SECRET_KEY` | Auth tokens, cookie signing |
| HuggingFace API key | `HUGGINGFACE_API_KEY` | LLM inference |
| Google API key | `GOOGLE_API_KEY` | Gemini LLM provider |
| PostgreSQL password | `POSTGRES_PASSWORD` | Database connection |
| MongoDB password | `MONGO_PASSWORD` | Document store |

### Rotation Procedure

#### 1. `SECRET_KEY` (JWT Signing Key)

> ⚠️ **This invalidates ALL existing user sessions.** Coordinate with users.

```bash
# Generate a new key
python3 -c "import secrets; print(secrets.token_urlsafe(64))"

# Update in all environments
# Docker Compose: update .env file
# Kubernetes: update the Secret object
kubectl create secret generic intellireview-secrets \
  --from-literal=SECRET_KEY="<new-key>" \
  --dry-run=client -o yaml | kubectl apply -f -

# Rolling restart to pick up new key
kubectl rollout restart deployment intellireview-api
kubectl rollout restart deployment intellireview-celery
```

#### 2. `HUGGINGFACE_API_KEY` / `GOOGLE_API_KEY`

```bash
# 1. Generate new key from provider dashboard
# 2. Update environment
echo "HUGGINGFACE_API_KEY=hf_newkey..." >> .env

# 3. Restart API (no user impact — LLM features degrade gracefully)
docker restart intellireview_api
```

#### 3. `POSTGRES_PASSWORD`

```bash
# 1. Update password in PostgreSQL
docker exec -it intellireview_postgres \
  psql -U postgres -c "ALTER USER intellireview PASSWORD 'new_password';"

# 2. Update .env / Kubernetes secrets
# 3. Restart API + Celery
docker restart intellireview_api intellireview_celery
```

### Post-Rotation Verification

```bash
# 1. Check auth still works
curl -s http://localhost:8000/api/v1/auth/login \
  -X POST -d "username=admin&password=admin" | jq .access_token

# 2. Check LLM still works
curl -s http://localhost:8000/health/ready | jq .

# 3. Check DB connection
curl -s http://localhost:8000/health | jq .
```

---

## 5. Stuck Celery Tasks

### Symptoms
- Queue depth (`/api/v1/queue_status/status`) keeps growing
- `workers_online: 0` in queue status response
- Upload status stuck in `PENDING` state

### Diagnosis

```bash
# Inspect active tasks
celery -A api.celery_app inspect active

# Inspect reserved (prefetched) tasks
celery -A api.celery_app inspect reserved

# Check worker logs
docker logs intellireview_celery --tail 100
```

### Resolution

```bash
# Restart workers
docker restart intellireview_celery

# If tasks are truly stuck and blocking the queue (DANGEROUS)
celery -A api.celery_app purge

# Revoke a specific task
celery -A api.celery_app control revoke <task_id> --terminate
```

---

## 6. General Troubleshooting

### Log Locations

| Component | Docker | Kubernetes |
|---|---|---|
| API logs | `docker logs intellireview_api` | `kubectl logs -l app=api` |
| Celery logs | `docker logs intellireview_celery` | `kubectl logs -l app=celery-worker` |
| Structured logs | `./logs/api.log` (volume-mounted) | `/app/logs/api.log` |
| Nginx | `docker logs intellireview_nginx` | `kubectl logs -l app=nginx` |

### Key Prometheus Metrics to Monitor

| Metric | Alert Threshold | Meaning |
|---|---|---|
| `http_requests_total{http_status="500"}` | > 10/min | Internal errors spiking |
| `http_request_duration_seconds` p99 | > 10s | API latency degraded |
| `analysis_queue_size` | > 50 for > 5min | Queue backup |
| `celery_tasks_total{status="failure"}` | > 5/min | Task failures |
| `llm_call_duration_seconds` p99 | > 30s | LLM provider slow |

### SPA Asset Mismatch
If the frontend shows a blank page with "Unexpected token <" in console:
```bash
# Check asset integrity
curl -s http://localhost:8000/health/spa | jq .

# Rebuild frontend
cd dashboard && npm run build && cd ..

# Restart API to pick up new assets
docker restart intellireview_api
```