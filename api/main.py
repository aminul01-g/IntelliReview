from fastapi import FastAPI, HTTPException, Depends, status, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import JSONResponse, FileResponse
import os
from contextlib import asynccontextmanager
import uvicorn
from slowapi import Limiter, _rate_limit_exceeded_handler
from slowapi.util import get_remote_address
from slowapi.errors import RateLimitExceeded
from slowapi.middleware import SlowAPIMiddleware
from api.middleware.resilience import LLMResilienceMiddleware

from config.settings import settings
from api.routes import analysis, auth, metrics, feedback, webhooks, history, oauth_device, review_feedback, policies, queue_status
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
app.include_router(queue_status.router, prefix=f"{settings.API_PREFIX}", tags=["System"], dependencies=protected_dependencies)

@app.get("/health")
@limiter.limit("60/minute")
async def health_check(request: Request):
    """Health check endpoint."""
    return {"status": "healthy"}

# Serve Frontend SPA
if os.path.exists("dashboard/dist"):
    # Mount Vite's generated assets directory caching
    app.mount("/assets", StaticFiles(directory="dashboard/dist/assets"), name="assets")

    # Catch-all route to support React Router SPA behavior
    @app.get("/{full_path:path}")
    async def serve_spa(full_path: str):
        # Ignore actual API paths
        if full_path.startswith("api/v1/") or full_path.startswith("docs") or full_path.startswith("openapi.json"):
            raise HTTPException(status_code=404, detail="Not Found")
            
        # Serve exact file if it exists (e.g. /favicon.ico, /vite.svg)
        file_path = os.path.join("dashboard/dist", full_path)
        if os.path.isfile(file_path):
            return FileResponse(file_path)
            
        # Fallback to SPA entrypoint
        return FileResponse("dashboard/dist/index.html")
else:
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

if __name__ == "__main__":
    uvicorn.run(
        "api.main:app",
        host=settings.API_HOST,
        port=settings.API_PORT,
        reload=settings.DEBUG
    )