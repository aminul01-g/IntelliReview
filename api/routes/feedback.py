import logging
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session
from sqlalchemy import func

from api.database import get_db
from api.models.user import User
from api.models.feedback import RuleTelemetry, SuggestionFeedback
from api.auth import get_current_user

logger = logging.getLogger(__name__)

router = APIRouter()

class FeedbackRequest(BaseModel):
    """Feedback request schema."""
    suggestion_id: str
    accepted: bool
    issue_type: str
    comment: str = ""

@router.post("/submit")
async def submit_feedback(
    feedback: FeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Submit feedback on a suggestion and update rule weights."""
    
    # 1. Store the individual feedback log
    feedback_log = SuggestionFeedback(
        user_id=current_user.id,
        rule_type=feedback.issue_type,
        suggestion_id=feedback.suggestion_id,
        accepted=feedback.accepted
    )
    db.add(feedback_log)
    
    # 2. Update aggregate Rule Telemetry for the Team Level (or Global)
    telemetry = db.query(RuleTelemetry).filter(
        RuleTelemetry.team_id == current_user.team_id,
        RuleTelemetry.rule_type == feedback.issue_type
    ).first()
    
    if not telemetry:
        telemetry = RuleTelemetry(
            team_id=current_user.team_id,
            rule_type=feedback.issue_type,
            total_suggestions=0,
            accepted_count=0,
            rejected_count=0,
            current_weight=100
        )
        db.add(telemetry)
        
    telemetry.total_suggestions += 1
    if feedback.accepted:
        telemetry.accepted_count += 1
    else:
        telemetry.rejected_count += 1
        
    # Moving Average Weight tuning (Phase 3 spec)
    # If accepted < 40%, start dropping weight. If > 80%, increase.
    acceptance_rate = telemetry.accepted_count / telemetry.total_suggestions
    if telemetry.total_suggestions >= 5:
        if acceptance_rate < 0.40:
            telemetry.current_weight = max(10, telemetry.current_weight - 5)
        elif acceptance_rate > 0.80:
            telemetry.current_weight = min(150, telemetry.current_weight + 5)
            
    db.commit()
    
    return {
        "message": "Feedback recorded successfully in Postgres",
        "suggestion_id": feedback.suggestion_id,
        "accepted": feedback.accepted,
        "new_weight": telemetry.current_weight
    }

@router.get("/stats")
async def get_feedback_stats(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get dynamic database-backed feedback statistics for current team."""
    stats = db.query(RuleTelemetry).filter(
        RuleTelemetry.team_id == current_user.team_id
    ).all()
    
    result = {}
    for s in stats:
        result[s.rule_type] = {
            "total_suggestions": s.total_suggestions,
            "acceptance_rate": round(s.accepted_count / s.total_suggestions if s.total_suggestions else 0, 2),
            "rejection_rate": round(s.rejected_count / s.total_suggestions if s.total_suggestions else 0, 2),
            "current_weight": s.current_weight
        }
        
    return {
        "statistics": result,
        "total_issue_types": len(result)
    }
