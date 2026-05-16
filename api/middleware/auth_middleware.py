from fastapi import Request, HTTPException, status
from starlette.middleware.base import BaseHTTPMiddleware
from jose import JWTError, jwt
from config.settings import settings
import logging

logger = logging.getLogger("api.middleware.auth")

class AuthMiddleware(BaseHTTPMiddleware):
    """
    Middleware to handle JWT authentication and token validation.
    Adds the user identity to the request state for downstream use.
    """
    async def dispatch(self, request: Request, call_next):
        # Exclude public endpoints from auth check
        path = request.url.path
        public_paths = [
            f"{settings.API_PREFIX}/auth/login",
            f"{settings.API_PREFIX}/auth/register",
            "/health",
            f"{settings.API_PREFIX}/oauth"
        ]

        if any(path.startswith(p) for p in public_paths):
            return await call_next(request)

        auth_header = request.headers.get("Authorization")
        if not auth_header or not auth_header.startswith("Bearer "):
            # We don't raise 401 here to allow the route-level Depends(get_current_user)
            # to handle the error with a proper response. We just don't set the user.
            return await call_next(request)

        token = auth_header.split(" ")[1]
        try:
            payload = jwt.decode(token, settings.SECRET_KEY, algorithms=[settings.ALGORITHM])
            username: str = payload.get("sub")
            if username:
                request.state.user = username
        except JWTError as e:
            logger.warning(f"Invalid token provided: {str(e)}")
            # Allow request to proceed; Depends(get_current_user) will catch the failure

        return await call_next(request)
