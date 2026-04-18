from fastapi import APIRouter, Depends, HTTPException
import json
import redis
from config.settings import settings
from api.auth import get_current_user
from api.models.user import User

router = APIRouter()

@router.get("/queue-status")
async def get_queue_status(current_user: User = Depends(get_current_user)):
    """Fetch the current depth of Celery processing queues."""
    try:
        redis_client = redis.Redis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
        
        # Celery natively stores priority queues as lists or hashes depending on the broker config.
        # Typically, the name of the queue is the key.
        bulk_depth = redis_client.llen("bulk")
        express_depth = redis_client.llen("express")
        default_depth = redis_client.llen("celery")
        
        return {
            "status": "online",
            "queues": {
                "bulk": bulk_depth,
                "express": express_depth,
                "default": default_depth
            },
            "total_pending": bulk_depth + express_depth + default_depth
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to connect to Redis broker: {str(e)}")
