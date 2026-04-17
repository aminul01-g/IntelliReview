from celery import Celery
import os
from config.settings import settings

redis_url = os.environ.get("CELERY_BROKER_URL", f"redis://{settings.REDIS_HOST}:{settings.REDIS_PORT}/0")

celery_app = Celery(
    "intellireview_tasks",
    broker=redis_url,
    backend=redis_url,
    include=["api.tasks.analysis_tasks"]
)

# Core configuration
celery_app.conf.update(
    task_serializer='json',
    accept_content=['json'],
    result_serializer='json',
    timezone='UTC',
    enable_utc=True,
    task_track_started=True,
    task_time_limit=300,       # Hard timeout: 5 minutes to prevent hung workers
    worker_prefetch_multiplier=1,  # Fair distribution for heavy analysis tasks

    # ── Retry / Resilience defaults ──────────────────────────────────
    # Individual tasks can override these via @celery_app.task(max_retries=N).
    # The exponential countdown is computed inside _backoff_countdown().
    task_acks_late=True,       # Re-queue task if worker dies mid-flight
    task_reject_on_worker_lost=True,
)
