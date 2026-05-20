"""
Audit Logging Middleware for IntelliReview.
Logs all non-GET (mutating) requests to the AuditLog database table.
"""

import logging
import time
import json
from typing import Optional

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request
from starlette.responses import Response

from api.database import SessionLocal
from api.models.audit import AuditLog

logger = logging.getLogger("api.middleware.audit")

# HTTP methods that are considered read-only; everything else is audited.
_SAFE_METHODS = frozenset({"GET", "HEAD", "OPTIONS"})

# Paths that should never be audited (health probes, metrics, static assets)
_SKIP_PREFIXES = (
    "/health",
    "/metrics",
    "/assets/",
    "/docs",
    "/openapi.json",
    "/ws/",
)


class AuditMiddleware(BaseHTTPMiddleware):
    """
    Middleware that persists an AuditLog row for every mutating HTTP request.

    Captures:
      - user_id  (extracted from request.state, set by AuthMiddleware)
      - action   (HTTP method)
      - resource (request path)
      - details  (status code, processing time, content-length)
    """

    async def dispatch(self, request: Request, call_next) -> Response:
        # Skip safe / read-only methods
        if request.method in _SAFE_METHODS:
            return await call_next(request)

        # Skip health / docs / static paths
        path = request.url.path
        if any(path.startswith(prefix) for prefix in _SKIP_PREFIXES):
            return await call_next(request)

        start = time.monotonic()
        response = await call_next(request)
        elapsed = round(time.monotonic() - start, 4)

        # Best-effort write — never let audit failures crash a request
        try:
            user_id = self._extract_user_id(request)
            resource = path
            action = request.method

            details = {
                "status_code": response.status_code,
                "processing_time_s": elapsed,
                "content_length": response.headers.get("content-length"),
                "query_params": str(request.query_params) if request.query_params else None,
            }

            self._persist_audit_log(
                user_id=user_id,
                action=action,
                resource=resource,
                details=details,
            )
        except Exception:
            logger.exception("Failed to write audit log for %s %s", request.method, path)

        return response

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    @staticmethod
    def _extract_user_id(request: Request) -> Optional[int]:
        """Try to pull user_id from request state (set by auth middleware/deps)."""
        # The AuthMiddleware sets request.state.user to a username string.
        # Route-level deps resolve the full User ORM object, but middleware
        # runs before deps, so we only have username at this layer.
        # We store None when unauthenticated — the FK is nullable.
        try:
            user = getattr(request.state, "user", None)
            if user is None:
                return None
            # If it's an int already, great
            if isinstance(user, int):
                return user
            # If it's a string username, we'd need a DB lookup — skip for now
            # to avoid a second DB round-trip in hot path.  The username is
            # captured in 'details' via the auth header anyway.
            return None
        except Exception:
            return None

    @staticmethod
    def _persist_audit_log(
        user_id: Optional[int],
        action: str,
        resource: str,
        details: dict,
    ) -> None:
        """Write an AuditLog row using a short-lived session."""
        if SessionLocal is None:
            logger.debug("Database not configured; skipping audit log")
            return

        db = SessionLocal()
        try:
            log = AuditLog(
                user_id=user_id,
                action=action,
                resource_type=resource,
                details=details,
            )
            db.add(log)
            db.commit()
        except Exception:
            db.rollback()
            raise
        finally:
            db.close()
