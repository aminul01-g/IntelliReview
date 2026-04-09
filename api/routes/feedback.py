from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.user import User
from api.auth import get_current_user
from ml_models.pattern_learner import PatternLearner

router = APIRouter()

# Initialize pattern learner
pattern_learner = PatternLearner()

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
    """Submit feedback on a suggestion."""
    
    # Record feedback
    pattern_learner.record_feedback(
        suggestion_id=feedback.suggestion_id,
        accepted=feedback.accepted,
        issue_type=feedback.issue_type,
        code_context=""  # Add actual code context if available
    )
    
    return {
        "message": "Feedback recorded successfully",
        "suggestion_id": feedback.suggestion_id,
        "accepted": feedback.accepted
    }

@router.get("/stats")
async def get_feedback_stats(
    current_user: User = Depends(get_current_user)
):
    """Get feedback statistics."""
    stats = pattern_learner.get_statistics()
    
    return {
        "statistics": stats,
        "total_issue_types": len(stats)
    }
