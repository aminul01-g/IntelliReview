"""
History routes — Lightweight FastAPI proxy for the Go-based
analysis-history service.

Provides REST endpoints that the React dashboard can call through
the existing FastAPI auth layer, while the Go service handles the
heavy lifting of aggregation and GraphQL queries.
"""

from fastapi import APIRouter, Depends, HTTPException, Request
from typing import Optional
import httpx
import logging

from api.auth import get_current_user
from api.models.user import User

logger = logging.getLogger(__name__)

router = APIRouter()

# Internal URL for the Go analysis-history service
# In Docker Compose, services communicate via container names
ANALYSIS_HISTORY_URL = "http://analysis-history:4000"


@router.post("/trigger-aggregation")
async def trigger_aggregation(
    current_user: User = Depends(get_current_user),
):
    """
    Trigger an immediate aggregation pass in the Go analysis-history service.
    
    This is useful after a batch of analyses complete, to ensure the
    metrics_history table is updated without waiting for the next
    scheduled aggregation cycle.
    """
    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(f"{ANALYSIS_HISTORY_URL}/trigger")
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError:
        logger.warning("Analysis history service not reachable — is it running?")
        return {
            "status": "service_unavailable",
            "message": "Analysis history service is not running. "
                       "Aggregation will occur automatically when the service starts."
        }
    except Exception as e:
        logger.error(f"Failed to trigger aggregation: {e}")
        raise HTTPException(status_code=502, detail=f"Aggregation trigger failed: {str(e)}")


@router.get("/health")
async def history_service_health():
    """Check the health of the Go analysis-history service."""
    try:
        async with httpx.AsyncClient(timeout=5.0) as client:
            response = await client.get(f"{ANALYSIS_HISTORY_URL}/health")
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError:
        return {"status": "unavailable", "service": "analysis-history"}
    except Exception as e:
        return {"status": "error", "service": "analysis-history", "detail": str(e)}


@router.post("/graphql")
async def graphql_proxy(
    request: Request,
    current_user: User = Depends(get_current_user),
):
    """
    Proxy GraphQL requests to the Go analysis-history service.
    
    This allows the React dashboard to make GraphQL queries through
    the FastAPI auth layer without needing separate authentication
    for the Go service.
    """
    try:
        body = await request.body()
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                f"{ANALYSIS_HISTORY_URL}/graphql",
                content=body,
                headers={"Content-Type": "application/json"},
            )
            response.raise_for_status()
            return response.json()
    except httpx.ConnectError:
        raise HTTPException(
            status_code=503,
            detail="Analysis history service is not available"
        )
    except Exception as e:
        logger.error(f"GraphQL proxy failed: {e}")
        raise HTTPException(status_code=502, detail=f"GraphQL proxy error: {str(e)}")
