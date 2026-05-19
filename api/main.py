from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse, Response
import os
import uuid
import logging
from contextlib import asynccontextmanager
import uvicorn
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from api.middleware.auth_middleware import AuthMiddleware
from api.middleware.rate_limit import RateLimitMiddleware
from api.middleware.logging_middleware import LoggingMiddleware
from api.middleware.resilience import LLMResilienceMiddleware
from api.logging import setup_logging
from config.settings import settings

# Initialize structured logging
logger = setup_logging()

from api.routes import analysis, auth, metrics, feedback, webhooks, history, oauth_device, review_feedback, policies, queue_status, research, websocket
from api.database import engine, Base

# Ensure all models are loaded before create_all
import api.models.user
import api.models.analysis
import api.models.feedback
import api.models.audit

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
except Exception as e:
    print(f"Warning: Could not initialize database tables: {e}")

# Initialize Limiter
limiter = Limiter(key_func=get_remote_address)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup
    print("🚀 Starting IntelliReview API...")
    _validate_spa_assets()
    _check_redis_on_startup()
    yield
    # Shutdown
    print("👋 Shutting down IntelliReview API...")

# Initialize FastAPI app
app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    description="AI-Powered Code Review Assistant API",
    lifespan=lifespan
)

# Add Limiter to app state
app.state.limiter = limiter
app.add_exception_handler(RateLimitExceeded, _rate_limit_exceeded_handler)
app.add_middleware(SlowAPIMiddleware)

# ── Pydantic Validation Error Handler ────────────────────────────────────────
# Catches Pydantic validation errors and returns a structured 422 instead of 500.
from pydantic import ValidationError as PydanticValidationError

@app.exception_handler(PydanticValidationError)
async def pydantic_validation_exception_handler(request: Request, exc: PydanticValidationError):
    """Return 422 with validation details when Pydantic models reject input."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    _logger = logging.getLogger("api.validation")
    _logger.warning(
        "Pydantic validation error on %s %s [request_id=%s]: %s",
        request.method, request.url.path, request_id, exc.error_count(),
    )
    return JSONResponse(
        status_code=422,
        content={
            "detail": "Validation error",
            "errors": exc.errors(),
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )

# ── Global Exception Handler ────────────────────────────────────────────────
# Catches ALL unhandled exceptions to prevent stack trace leakage.
@app.exception_handler(Exception)
async def global_exception_handler(request: Request, exc: Exception):
    """Catch-all handler for unhandled exceptions. Returns a structured JSON 500
    with a unique request ID for correlation, without leaking internal details."""
    request_id = request.headers.get("X-Request-ID", str(uuid.uuid4()))
    _logger = logging.getLogger("api.global_error")
    _logger.exception(
        "Unhandled exception on %s %s [request_id=%s]",
        request.method, request.url.path, request_id,
    )
    return JSONResponse(
        status_code=500,
        content={
            "detail": "Internal server error",
            "request_id": request_id,
        },
        headers={"X-Request-ID": request_id},
    )

# CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.ALLOWED_ORIGINS.split(","),
    allow_credentials=True,
    allow_methods=["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    allow_headers=["*"],
)

# LLM Resilience middleware — translates upstream 429/503/504 into structured errors
app.add_middleware(LLMResilienceMiddleware)

# Custom middleware
app.add_middleware(LoggingMiddleware)
app.add_middleware(AuthMiddleware)
app.add_middleware(RateLimitMiddleware, limiter=limiter)

from api.auth import get_current_user

# Include public routers
app.include_router(auth.router, prefix=f"{settings.API_PREFIX}/auth", tags=["Authentication"])
app.include_router(webhooks.router, prefix=f"{settings.API_PREFIX}/webhooks", tags=["Webhooks"])
app.include_router(oauth_device.router, prefix=f"{settings.API_PREFIX}/oauth", tags=["OAuth Device Flow"])

# Include protected routers
protected_dependencies = [Depends(get_current_user)]
app.include_router(analysis.router, prefix=f"{settings.API_PREFIX}/analysis", tags=["Analysis"], dependencies=protected_dependencies)
app.include_router(metrics.router, prefix=f"{settings.API_PREFIX}/metrics", tags=["Metrics"], dependencies=protected_dependencies)
app.include_router(feedback.router, prefix=f"{settings.API_PREFIX}/feedback", tags=["Feedback"], dependencies=protected_dependencies)
app.include_router(history.router, prefix=f"{settings.API_PREFIX}/history", tags=["History"], dependencies=protected_dependencies)
app.include_router(review_feedback.router, prefix=f"{settings.API_PREFIX}/review-feedback", tags=["Review Feedback"], dependencies=protected_dependencies)
app.include_router(policies.router, prefix=f"{settings.API_PREFIX}/policies", tags=["Policies"], dependencies=protected_dependencies)
app.include_router(queue_status.router, prefix=f"{settings.API_PREFIX}/queue_status", tags=["System"], dependencies=protected_dependencies)
app.include_router(research.router, prefix=f"{settings.API_PREFIX}/research", tags=["Research"], dependencies=protected_dependencies)
app.include_router(websocket.router, tags=["Real-time Updates"])


# ── Prometheus Metrics (public, root-level) ──────────────────────────────────
@app.get("/metrics")
async def prometheus_metrics():
    """Expose Prometheus metrics at /metrics (standard scrape path, no auth)."""
    from prometheus_client import generate_latest, CONTENT_TYPE_LATEST
    return Response(content=generate_latest(), media_type=CONTENT_TYPE_LATEST)


# ── Health Checks ────────────────────────────────────────────────────────────
@app.get("/health/live")
async def liveness_probe():
    """Liveness probe for Kubernetes/Docker."""
    return {"status": "live"}

@app.get("/health/ready")
async def readiness_probe(request: Request):
    """Readiness probe: Checks Redis connectivity."""
    try:
        import redis
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
        )
        r.ping()
        return {"status": "ready"}
    except Exception:
        # Redis unavailable is not necessarily fatal (SQLite mode)
        return {"status": "ready", "redis": "unavailable"}

@app.get("/health")
@limiter.limit("60/minute")
async def health_check(request: Request):
    """Health check endpoint."""
    return {"status": "healthy"}

@app.get("/health/spa")
async def spa_health():
    """Verify frontend SPA assets are present and consistent."""
    index_path = os.path.join("dashboard/dist", "index.html")
    if not os.path.isfile(index_path):
        return JSONResponse(
            status_code=503,
            content={"status": "missing", "detail": "index.html not found"},
        )
    
    # Check that referenced JS assets actually exist on disk
    missing = _find_missing_spa_assets(index_path)
    if missing:
        return JSONResponse(
            status_code=503,
            content={
                "status": "stale",
                "detail": "Referenced assets missing after rebuild",
                "missing_assets": missing,
            },
        )
    return {"status": "ok", "index": index_path}


# ── Serve Frontend SPA ───────────────────────────────────────────────────────
FRONTEND_DIST = "dashboard/dist"
if os.path.exists(FRONTEND_DIST):
    print(f"✅ Frontend assets found at {FRONTEND_DIST}. Enabling SPA hosting.")
    # Mount Vite's generated assets directory
    app.mount("/assets", StaticFiles(directory=os.path.join(FRONTEND_DIST, "assets")), name="assets")

    @app.get("/{full_path:path}")
    async def serve_spa(request: Request, full_path: str):
        # 1. Ignore actual API paths, docs, and assets (assets handled by mount)
        api_prefix = settings.API_PREFIX.lstrip("/")
        if (full_path.startswith(api_prefix) or 
            full_path.startswith("docs") or 
            full_path.startswith("openapi.json") or
            full_path.startswith("assets/")):
            raise HTTPException(status_code=404, detail="Not Found")
            
        # 2. Serve exact file if it exists at the root of dist (e.g. favicon.ico, vite.svg)
        file_path = os.path.join(FRONTEND_DIST, full_path)
        if full_path and os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # 3. Fallback to SPA entrypoint for UI routes
        # IMPORTANT: If the path looks like a file (has an extension) but wasn't found, 
        # do NOT return index.html as it causes 'Unexpected token <' errors in the browser.
        if "." in full_path.split("/")[-1] and not full_path.endswith(".html"):
            raise HTTPException(status_code=404, detail="Static asset not found")

        # Serve index.html with no-cache so browsers always get the latest after rebuilds
        return FileResponse(
            os.path.join(FRONTEND_DIST, "index.html"),
            headers={"Cache-Control": "no-cache, no-store, must-revalidate"},
        )
else:
    print(f"⚠️ Frontend assets NOT found at {FRONTEND_DIST}. Running in API-only mode.")
    @app.get("/")
    @limiter.limit("60/minute")
    async def root(request: Request):
        """API Root endpoint for when the frontend is unbuilt."""
        return {
            "name": settings.APP_NAME,
            "version": settings.APP_VERSION,
            "status": "running",
            "message": "Frontend not built. To view the UI, build the frontend first."
        }


# ── SPA Asset Validation Helpers ─────────────────────────────────────────────
def _find_missing_spa_assets(index_path: str) -> list[str]:
    """Parse index.html for <script src="..."> and <link href="..."> tags
    and verify each referenced file exists on disk."""
    import re
    missing = []
    try:
        with open(index_path, "r") as f:
            html = f.read()
        # Match src="/assets/..." and href="/assets/..."
        refs = re.findall(r'(?:src|href)="(/assets/[^"]+)"', html)
        for ref in refs:
            # ref is like "/assets/index-BfVSQqAk.js"
            disk_path = os.path.join("dashboard/dist", ref.lstrip("/"))
            if not os.path.isfile(disk_path):
                missing.append(ref)
    except Exception:
        pass
    return missing


def _validate_spa_assets():
    """Startup check: warn loudly if SPA assets are stale."""
    index_path = os.path.join("dashboard/dist", "index.html")
    if not os.path.isfile(index_path):
        return
    missing = _find_missing_spa_assets(index_path)
    if missing:
        _logger = logging.getLogger("api.spa")
        _logger.error(
            "SPA ASSET MISMATCH: index.html references assets that don't exist on disk: %s. "
            "This usually means the frontend was rebuilt but the server is serving a stale index.html.",
            missing,
        )

def _check_redis_on_startup():
    """Non-blocking Redis connectivity check at startup.
    Logs a warning if Redis is unreachable but does NOT prevent the API from starting."""
    _logger = logging.getLogger("api.startup")
    try:
        import redis
        r = redis.Redis(
            host=settings.REDIS_HOST,
            port=settings.REDIS_PORT,
            db=settings.REDIS_DB,
            socket_timeout=2.0,
            socket_connect_timeout=2.0,
        )
        r.ping()
        _logger.info("✅ Redis is reachable at %s:%s", settings.REDIS_HOST, settings.REDIS_PORT)
    except Exception as exc:
        _logger.warning(
            "⚠️  Redis is NOT reachable at %s:%s — queue features will be degraded. Error: %s",
            settings.REDIS_HOST, settings.REDIS_PORT, exc,
        )


if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )