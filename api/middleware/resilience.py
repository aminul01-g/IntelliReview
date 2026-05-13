"""
Resilience Middleware for IntelliReview.
Implements a circuit breaker and specialized error translation for LLM providers.
Translates upstream 429 (Rate Limit) and 5xx (Server Error) into structured API responses.
"""

import time
import logging
import json
import re
from typing import Optional
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

from config.settings import settings

logger = logging.getLogger(__name__)

# Sentinel header attached when a 429 originates from an upstream LLM service
UPSTREAM_LLM_RATE_LIMIT_HEADER = "X-IntelliReview-Engine-Error"

class LLMResilienceMiddleware(BaseHTTPMiddleware):
    """
    Middleware to catch LLM-related failures and provide consistent error responses.
    Combines error normalization with a circuit breaker to prevent cascading failures.
    """
    def __init__(self, app):
        super().__init__(app)
        # Circuit Breaker State
        self.circuit_open = False
        self.failure_count = 0
        self.failure_threshold = 5
        self.recovery_timeout = 60  # seconds
        self.last_failure_time = 0

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.monotonic()

        # 1. Circuit Breaker Check
        if self.circuit_open:
            if time.time() - self.last_failure_time > self.recovery_timeout:
                logger.info("Circuit Breaker: Attempting recovery (half-open state)")
                self.circuit_open = False
            else:
                return self._engine_error(
                    "LLM_UNAVAILABLE",
                    "The AI reasoning engine is currently experiencing high load. Please try again in a few minutes.",
                    retry_after=int(self.recovery_timeout - (time.time() - self.last_failure_time))
                )

        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed = round(time.monotonic() - start, 3)
            self._record_failure()
            logger.exception("Unhandled exception in request pipeline after %.3fs", elapsed)
            return self._engine_error("LLM_UNAVAILABLE", str(exc))

        # 2. Pass non-analysis paths straight through
        if not request.url.path.startswith(settings.API_PREFIX) or \
           not any(p in request.url.path for p in ["/analysis", "/feedback"]):
            return response

        # 3. Detect and Normalize Upstream Errors
        if response.status_code in (429, 500, 502, 503, 504):
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            try:
                payload = json.loads(body)
            except Exception:
                payload = {}

            detail: str = payload.get("detail", "")
            error_code, retry_after = self._classify_error(response.status_code, detail)

            self._record_failure()
            logger.warning(
                "LLM service error detected: status=%s code=%s path=%s",
                response.status_code,
                error_code,
                request.url.path,
            )

            return self._engine_error(error_code, detail or "The Analysis Engine encountered an upstream error.", retry_after)

        return response

    def _record_failure(self):
        """Update circuit breaker state."""
        self.failure_count += 1
        self.last_failure_time = time.time()
        if self.failure_count >= self.failure_threshold:
            logger.error(f"Circuit Breaker OPENED after {self.failure_count} consecutive failures")
            self.circuit_open = True

    @staticmethod
    def _classify_error(status_code: int, detail: str) -> tuple[str, Optional[int]]:
        """Map HTTP status + detail text to our error taxonomy."""
        detail_lower = detail.lower()

        if status_code == 429 or "rate limit" in detail_lower or "429" in detail_lower:
            m = re.search(r"retry.?after[:\s]+(\d+)", detail_lower)
            retry_after = int(m.group(1)) if m else 60
            return "LLM_RATE_LIMITED", retry_after

        if "timeout" in detail_lower or status_code == 504:
            return "LLM_TIMEOUT", None

        return "LLM_UNAVAILABLE", None

    @staticmethod
    def _engine_error(error_code: str, message: str, retry_after: Optional[int] = None) -> JSONResponse:
        status_map = {
            "LLM_RATE_LIMITED": 429,
            "LLM_TIMEOUT": 504,
            "LLM_UNAVAILABLE": 503,
        }
        headers = {UPSTREAM_LLM_RATE_LIMIT_HEADER: error_code}
        if retry_after:
            headers["Retry-After"] = str(retry_after)

        return JSONResponse(
            status_code=status_map.get(error_code, 503),
            content={
                "error_code": error_code,
                "message": message,
                "retry_after": retry_after,
                "service": "Analysis Engine",
            },
            headers=headers,
        )
