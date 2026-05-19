"""
Queue Status Routes for IntelliReview.
Provides visibility into the Celery task queue and worker health.
Hardened with timeouts, Redis health checks, and graceful fallbacks.
"""

import time
import logging
from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any, Optional

from config.settings import settings
from api.auth import get_current_user
from api.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

# ── Constants ────────────────────────────────────────────────────────────────
REDIS_SOCKET_TIMEOUT = 3.0          # seconds – per-command timeout
REDIS_CONNECT_TIMEOUT = 2.0         # seconds – initial connection
CELERY_INSPECTOR_TIMEOUT = 5.0      # seconds – inspector RPC timeout


def _get_redis_client():
    """Create a Redis client with explicit timeouts to prevent hanging."""
    import redis
    return redis.Redis(
        host=settings.REDIS_HOST,
        port=settings.REDIS_PORT,
        db=settings.REDIS_DB,
        socket_timeout=REDIS_SOCKET_TIMEOUT,
        socket_connect_timeout=REDIS_CONNECT_TIMEOUT,
        decode_responses=True,
    )


def _ping_redis(client) -> dict:
    """Verify Redis is reachable before doing heavier queries.

    Retries up to 3 times with exponential backoff (0.1s, 0.2s, 0.4s).
    Returns {"ok": True} on success or {"ok": False, "reason": "..."} on failure.
    """
    import time as _time
    max_retries = 3
    for attempt in range(max_retries):
        try:
            if client.ping():
                return {"ok": True}
        except TimeoutError:
            if attempt < max_retries - 1:
                _time.sleep(0.1 * (2 ** attempt))
                continue
            return {"ok": False, "reason": "Redis slow to respond (timeout after retries)"}
        except Exception as exc:
            if attempt < max_retries - 1:
                _time.sleep(0.1 * (2 ** attempt))
                continue
            return {"ok": False, "reason": f"Redis connection error: {exc}"}
    return {"ok": False, "reason": "Redis unreachable after retries"}


@router.get("/status")
async def get_queue_status(
    current_user: Optional[User] = Depends(get_current_user),
):
    """
    Retrieve the current status of the analysis queue.
    Returns queue depth, estimated wait time, and broker health.

    Gracefully degrades when Redis or Celery workers are unreachable.
    """
    start = time.monotonic()

    # ── 1. Redis connectivity check ──────────────────────────────────────
    try:
        redis_client = _get_redis_client()
    except Exception as exc:
        logger.exception("Failed to initialise Redis client")
        return _fallback_response(reason=f"Redis client init error: {exc}")

    ping_result = _ping_redis(redis_client)
    if not ping_result["ok"]:
        reason = ping_result.get("reason", "Redis broker unreachable")
        logger.warning("Redis health check: %s", reason)
        return _fallback_response(reason=reason)

    # ── 2. Queue depths ──────────────────────────────────────────────────
    try:
        bulk_depth = redis_client.llen("bulk") or 0
        express_depth = redis_client.llen("express") or 0
        default_depth = redis_client.llen("celery") or 0
        total_pending = bulk_depth + express_depth + default_depth
    except Exception as exc:
        logger.exception("Error reading queue depths from Redis")
        return _fallback_response(reason=f"Queue depth query failed: {exc}")

    # ── 3. Active worker inspection (best-effort) ────────────────────────
    active_tasks = 0
    scheduled_tasks = 0
    worker_count = 0
    try:
        from api.celery_app import celery_app

        inspector = celery_app.control.inspect(timeout=CELERY_INSPECTOR_TIMEOUT)
        active = inspector.active()
        scheduled = inspector.scheduled()

        if active:
            worker_count = len(active)
            active_tasks = sum(len(tasks) for tasks in active.values())
        if scheduled:
            scheduled_tasks = sum(len(tasks) for tasks in scheduled.values())
    except Exception as exc:
        # Inspector failures are non-fatal – we still have queue depth data
        logger.warning("Celery inspector failed (timeout or connectivity): %s", exc)

    # ── 4. Update Prometheus gauge ───────────────────────────────────────
    try:
        from api.metrics import update_queue_size
        update_queue_size(total_pending)
    except Exception:
        pass  # metrics are best-effort

    elapsed = round(time.monotonic() - start, 3)

    return {
        "status": "operational",
        "queues": {
            "bulk": bulk_depth,
            "express": express_depth,
            "default": default_depth,
        },
        "total_pending": total_pending,
        "active_tasks": active_tasks,
        "scheduled_tasks": scheduled_tasks,
        "workers_online": worker_count,
        "health": _compute_health(total_pending, worker_count),
        "response_time_ms": int(elapsed * 1000),
    }


@router.get("/tasks/{task_id}")
async def get_task_detail(
    task_id: str,
    current_user: User = Depends(get_current_user),
):
    """
    Retrieve the current state and result of a specific analysis task.
    Queries the Celery result backend.
    """
    try:
        from api.celery_app import celery_app

        res = celery_app.AsyncResult(task_id)

        return {
            "task_id": task_id,
            "state": res.state,
            "result": res.result if res.ready() else None,
            "timestamp": res.date,
            "status": (
                "completed"
                if res.state == "SUCCESS"
                else "processing"
                if res.state == "PENDING"
                else "failed"
            ),
        }
    except Exception as e:
        logger.exception("Failed to retrieve task %s", task_id)
        raise HTTPException(
            status_code=404,
            detail=f"Could not retrieve task {task_id}: {str(e)}",
        )


# ── Helpers ──────────────────────────────────────────────────────────────────

def _fallback_response(reason: str) -> Dict[str, Any]:
    """Return a degraded-but-valid response when infrastructure is down."""
    return {
        "status": "degraded",
        "redis_available": False,
        "reason": reason,
        "queues": {"bulk": 0, "express": 0, "default": 0},
        "total_pending": 0,
        "active_tasks": 0,
        "scheduled_tasks": 0,
        "workers_online": 0,
        "health": "unknown",
        "response_time_ms": 0,
    }


def _compute_health(total_pending: int, worker_count: int) -> str:
    """Simple traffic-light health based on queue backlog."""
    if worker_count == 0 and total_pending > 0:
        return "red"
    if total_pending >= 100:
        return "yellow"
    return "green"
