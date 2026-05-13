"""
Queue Status Routes for IntelliReview.
Provides visibility into the Celery task queue and worker health.
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import Dict, Any
import redis

from config.settings import settings
from api.auth import get_current_user
from api.models.user import User

router = APIRouter()

@router.get("/status")
async def get_queue_status(
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve the current status of the analysis queue.
    Returns queue depth, estimated wait time, and broker health.
    """
    try:
        redis_client = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB
        )

        # Celery stores priority queues as lists.
        # We check common queue names used in our celery_app.py configuration.
        bulk_depth = redis_client.llen("bulk")
        express_depth = redis_client.llen("express")
        default_depth = redis_client.llen("celery")

        total_pending = bulk_depth + express_depth + default_depth

        return {
            "status": "operational",
            "queues": {
                "bulk": bulk_depth,
                "express": express_depth,
                "default": default_depth
            },
            "total_pending": total_pending,
            "health": "green" if total_pending < 100 else "yellow"
        }
    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Failed to connect to Redis broker: {str(e)}"
        )

@router.get("/tasks/{task_id}")
async def get_task_detail(
    task_id: str,
    current_user: User = Depends(get_current_user)
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
            "status": "completed" if res.state == "SUCCESS" else "processing" if res.state == "PENDING" else "failed"
        }
    except Exception as e:
        raise HTTPException(
            status_code=404,
            detail=f"Could not retrieve task {task_id}: {str(e)}"
        )
