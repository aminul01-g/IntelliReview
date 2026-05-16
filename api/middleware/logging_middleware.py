import time
import uuid
import structlog
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from api.metrics import track_http_request

logger = structlog.get_logger()

class LoggingMiddleware(BaseHTTPMiddleware):
    """
    Middleware for structured logging and performance tracking.
    Injects a unique request ID into every request and logs
    the completion of every HTTP transaction.
    """
    async def dispatch(self, request: Request, call_next):
        request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
        structlog.contextvars.bind_contextvars(request_id=request_id)

        start_time = time.perf_counter()

        try:
            response = await call_next(request)
            process_time = time.perf_counter() - start_time

            # Record Prometheus metrics
            track_http_request(
                method=request.method,
                endpoint=request.url.path,
                status=response.status_code,
                duration=process_time
            )

            logger.info(
                "http_request_completed",
                method=request.method,
                path=request.url.path,
                status=response.status_code,
                duration=f"{process_time:.4f}s"
            )

            response.headers["X-Request-ID"] = request_id
            return response

        except Exception as e:
            process_time = time.perf_counter() - start_time
            logger.error(
                "http_request_failed",
                method=request.method,
                path=request.url.path,
                error=str(e),
                duration=f"{process_time:.4f}s"
            )
            raise e
