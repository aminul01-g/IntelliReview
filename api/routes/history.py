"""
History Routes for IntelliReview.
Provides access to analysis history and aggregation triggers.
"""

from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import List, Dict, Any
from datetime import datetime

from api.database import get_db
from api.models.user import User
from api.models.analysis import Analysis
from api.schemas.analysis import AnalysisResponse
from api.auth import get_current_user

router = APIRouter()

@router.get("/history", response_model=List[AnalysisResponse])
async def get_analysis_history(
    limit: int = 20,
    project_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Retrieve paginated analysis history for the current user.
    If project_id is provided, filters results for that project.
    """
    query = db.query(Analysis).filter(Analysis.user_id == current_user.id)

    if project_id is not None:
        query = query.filter(Analysis.project_id == project_id)

    analyses = query.order_by(Analysis.created_at.desc()).limit(limit).all()

    results = []
    for a in analyses:
        try:
            # We use the AnalysisResponse schema defined in api.schemas.analysis
            # and map the SQLAlchemy model to the Pydantic model
            results.append(AnalysisResponse(
                analysis_id=a.id,
                status=a.status or "completed",
                language=a.language,
                file_path=a.file_path,
                original_code=a.original_code,
                issues=[Issue(**i) for i in (a.issues or [])],
                metrics=Metrics(**(a.metrics or {"lines_of_code": 0})),
                suggestions_count=len(a.issues or []),
                analyzed_at=a.completed_at or a.created_at,
                processing_time=a.processing_time,
                auto_fixes=a.issues if "diff" in str(a.issues) else None # Simplified
            ))
        except Exception as e:
            continue

    return results

@router.post("/trigger-aggregation")
async def trigger_aggregation(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Trigger an immediate aggregation of metrics for the user's team.
    This updates the RuleTelemetry and Tech Debt projections.
    """
    from api.tasks.rollup_tasks import aggregate_metrics_task

    try:
        # Dispatch to Celery for asynchronous processing
        task = aggregate_metrics_task.delay(user_id=current_user.id)
        return {
            "status": "triggered",
            "task_id": task.id,
            "message": "Aggregation task has been queued."
        }
    except Exception as e:
        # Fallback: run synchronously if Celery is not available (for dev)
        try:
            from api.tasks.rollup_tasks import aggregate_metrics_sync
            aggregate_metrics_sync(current_user.id, db)
            return {"status": "completed_sync", "message": "Aggregation completed synchronously."}
        except Exception as sync_e:
            raise HTTPException(
                status_code=500,
                detail=f"Failed to trigger aggregation: {str(sync_e)}"
            )

@router.get("/health")
async def history_health():
    """Health check for the history sub-module."""
    return {"status": "healthy", "component": "history_service"}
