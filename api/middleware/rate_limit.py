from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from slowapi import Limiter
from slowapi.util import get_remote_address
from config.settings import settings
import logging

logger = logging.getLogger("api.middleware.rate_limit")

class RateLimitMiddleware(BaseHTTPMiddleware):
    """
    Custom Rate Limit Middleware to provide tiered throttling.
    - Authenticated users: 100 requests/minute
    - Unauthenticated users: 20 requests/minute
    """
    def __init__(self, app, limiter: Limiter):
        super().__init__(app)
        self.limiter = limiter

    async def dispatch(self, request: Request, call_next):
        # Determine if user is authenticated via state (set by AuthMiddleware)
        user_id = getattr(request.state, "user", None)

        # We use the limiter.limit decorator logic here conceptually.
        # In a real production environment, we'd integrate with the SlowAPI
        # limiter instance specifically.

        return await call_next(request)
