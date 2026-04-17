"""
Resilience Middleware — FastAPI layer for catching upstream LLM API failures.

Intercepts responses and translates upstream provider errors (429 Rate Limit,
503 Unavailable, timeouts) into structured JSON that the frontend Toast system
can render with proper context, rather than leaking raw stack traces.
"""
import time
import logging
import json
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import JSONResponse, Response

logger = logging.getLogger(__name__)

# Sentinel header attached when a 429 originates from an upstream LLM service
# (not our own SlowAPI throttle). The frontend checks for this header to decide
# which toast variant to show.
UPSTREAM_LLM_RATE_LIMIT_HEADER = "X-IntelliReview-Engine-Error"


class LLMResilienceMiddleware(BaseHTTPMiddleware):
    """
    Catches LLM-related error payloads bubbling up from analysis routes and
    normalises them into a predictable envelope:

        {
          "error_code":  "LLM_RATE_LIMITED" | "LLM_TIMEOUT" | "LLM_UNAVAILABLE",
          "message":     <human-readable string>,
          "retry_after": <seconds | null>,
          "service":     "Analysis Engine"
        }
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        start = time.monotonic()
        try:
            response = await call_next(request)
        except Exception as exc:
            elapsed = round(time.monotonic() - start, 3)
            logger.exception("Unhandled exception in request pipeline after %.3fs", elapsed)
            return self._engine_error("LLM_UNAVAILABLE", str(exc), retry_after=None)

        # Pass non-analysis paths straight through
        if not request.url.path.startswith("/api/v1/analysis"):
            return response

        # Detect upstream 429 re-raised as 502 (our tasks wrap them)
        if response.status_code in (429, 502, 503, 504):
            body = b""
            async for chunk in response.body_iterator:  # type: ignore[attr-defined]
                body += chunk

            try:
                payload = json.loads(body)
            except Exception:
                payload = {}

            detail: str = payload.get("detail", "")
            error_code, retry_after = _classify_error(response.status_code, detail)

            logger.warning(
                "LLM service error detected: status=%s code=%s path=%s",
                response.status_code,
                error_code,
                request.url.path,
            )

            return self._engine_error(error_code, detail or "The Analysis Engine encountered an upstream error.", retry_after)

        return response

    @staticmethod
    def _engine_error(error_code: str, message: str, retry_after) -> JSONResponse:
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


def _classify_error(status_code: int, detail: str) -> tuple[str, int | None]:
    """Map HTTP status + detail text to our error taxonomy."""
    detail_lower = detail.lower()

    if status_code == 429 or "rate limit" in detail_lower or "429" in detail_lower:
        # Try to extract Retry-After value embedded in the message
        import re
        m = re.search(r"retry.?after[:\s]+(\d+)", detail_lower)
        retry_after = int(m.group(1)) if m else 60
        return "LLM_RATE_LIMITED", retry_after

    if "timeout" in detail_lower or status_code == 504:
        return "LLM_TIMEOUT", None

    return "LLM_UNAVAILABLE", None
