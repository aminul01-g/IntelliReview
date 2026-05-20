"""
Prometheus Metrics Module for IntelliReview.

Defines all application-level Prometheus metrics (counters, histograms, gauges)
and provides utility functions to record them from middleware, routes, and
background tasks.

The `/metrics` scrape endpoint itself is mounted at the root level in
`api/main.py` (no auth required, standard Prometheus scrape path).

This module also integrates `prometheus-fastapi-instrumentator` for automatic
HTTP request instrumentation when `setup_instrumentator()` is called.
"""

import logging

from prometheus_client import (
    Counter,
    Gauge,
    Histogram,
    generate_latest,
    CONTENT_TYPE_LATEST,
)

logger = logging.getLogger(__name__)

# ── HTTP Metrics ─────────────────────────────────────────────────────────────
HTTP_REQUESTS_TOTAL = Counter(
    "http_requests_total",
    "Total number of HTTP requests",
    ["method", "endpoint", "http_status"],
)
HTTP_REQUEST_DURATION = Histogram(
    "http_request_duration_seconds",
    "HTTP request latency in seconds",
    ["method", "endpoint"],
)

# ── Celery Task Metrics ──────────────────────────────────────────────────────
CELERY_TASKS_TOTAL = Counter(
    "celery_tasks_total",
    "Total number of processed Celery tasks",
    ["task_name", "status"],
)

# ── LLM Call Metrics ─────────────────────────────────────────────────────────
LLM_CALL_DURATION = Histogram(
    "llm_call_duration_seconds",
    "LLM API call latency in seconds",
    ["provider", "model"],
)

# ── Queue Depth Gauge ────────────────────────────────────────────────────────
ANALYSIS_QUEUE_SIZE = Gauge(
    "analysis_queue_size",
    "Number of pending analyses in Redis queue",
)

# ── Active WebSocket connections ─────────────────────────────────────────────
ACTIVE_WS_CONNECTIONS = Gauge(
    "active_websocket_connections",
    "Number of currently active WebSocket connections",
)


# ── Utility Functions ────────────────────────────────────────────────────────

def track_http_request(method: str, endpoint: str, status: int, duration: float) -> None:
    """Record HTTP request metrics (called from LoggingMiddleware)."""
    HTTP_REQUESTS_TOTAL.labels(method=method, endpoint=endpoint, http_status=status).inc()
    HTTP_REQUEST_DURATION.labels(method=method, endpoint=endpoint).observe(duration)


def track_celery_task(task_name: str, status: str) -> None:
    """Record Celery task completion metrics."""
    CELERY_TASKS_TOTAL.labels(task_name=task_name, status=status).inc()


def track_llm_call(provider: str, model: str, duration: float) -> None:
    """Record LLM call latency."""
    LLM_CALL_DURATION.labels(provider=provider, model=model).observe(duration)


def update_queue_size(size: int) -> None:
    """Update current queue depth gauge."""
    ANALYSIS_QUEUE_SIZE.set(size)


# ── prometheus-fastapi-instrumentator Integration ────────────────────────────

_instrumentator = None


def setup_instrumentator(app):  # noqa: ANN001
    """Attach the prometheus-fastapi-instrumentator to a FastAPI app.

    This adds automatic per-route latency histograms and request counts
    on top of the manually tracked metrics above.

    Safe to call multiple times — instruments only once.
    """
    global _instrumentator  # noqa: PLW0603
    if _instrumentator is not None:
        return _instrumentator

    try:
        from prometheus_fastapi_instrumentator import Instrumentator

        _instrumentator = Instrumentator(
            should_group_status_codes=True,
            should_ignore_untemplated=True,
            excluded_handlers=["/health", "/health/live", "/health/ready", "/metrics"],
        )
        _instrumentator.instrument(app)
        logger.info("prometheus-fastapi-instrumentator attached successfully")
        return _instrumentator
    except ImportError:
        logger.warning(
            "prometheus-fastapi-instrumentator not installed; "
            "automatic HTTP instrumentation disabled"
        )
        return None
    except Exception:
        logger.exception("Failed to set up prometheus-fastapi-instrumentator")
        return None
