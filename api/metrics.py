import logging
from prometheus_client import Counter, Histogram, Gauge, generate_latest, CONTENT_TYPE_LATEST
from fastapi import APIRouter, Request, Response
from config.settings import settings

logger = logging.getLogger(__name__)

# Define Metrics
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "http_status"]
)
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"]
)
CELERY_TASKS_TOTAL = Counter(
    "celery_tasks_total",
    "Total number of processed Celery tasks",
    ["task_name", "status"]
)
LLM_CALL_DURATION = Histogram(
    "llm_call_duration_seconds",
    "LLM API call latency in seconds",
    ["provider", "model"]
)
ANALYSIS_QUEUE_SIZE = Gauge(
    "analysis_queue_size",
    "Number of pending analyses in Redis queue"
)

router = APIRouter()

# NOTE: The Prometheus /metrics endpoint is now served at the root level
# in api/main.py (no auth required, standard scrape path).
# This router only contains auth-protected business metrics.

def track_http_request(method: str, endpoint: str, status: int, duration: float):
    """Utility to record HTTP request metrics."""
    HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, http_status=status).inc()
    HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)

def track_celery_task(task_name: str, status: str):
    """Utility to record Celery task metrics."""
    CELERY_TASKS_TOTAL.labels(task_name=task_name, status=status).inc()

def track_llm_call(provider: str, model: str, duration: float):
    """Utility to record LLM call metrics."""
    LLM_CALL_DURATION.labels(provider=provider, model=model).observe(duration)

def update_queue_size(size: int):
    """Utility to update current queue depth."""
    ANALYSIS_QUEUE_SIZE.set(size)
