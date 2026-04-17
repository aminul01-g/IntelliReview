"""
Interactive Review Feedback Routes
====================================
Allows human reviewers to interact with IntelliReview's findings:
- Request a better autofix for a specific finding
- Mark a pattern for future suppression in the Knowledge Base

Both actions update the PatternLearner knowledge base and the
RuleTelemetry table in Postgres.
"""

import logging
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session

from api.database import get_db
from api.models.user import User
from api.auth import get_current_user
from api.schemas.feedback_schemas import (
    ReviewerFeedbackRequest,
    ReviewerFeedbackResponse,
    AutofixDiff,
)

logger = logging.getLogger(__name__)

router = APIRouter()


# ─── Lazy-loaded pattern learner singleton ────────────────────────────

_pattern_learner = None


def _get_pattern_learner():
    """Lazy-load the PatternLearner to avoid circular imports."""
    global _pattern_learner
    if _pattern_learner is None:
        try:
            from ml_models.pattern_learner import PatternLearner
            _pattern_learner = PatternLearner()
        except ImportError:
            logger.warning("PatternLearner not available")
            _pattern_learner = None
    return _pattern_learner


# ─── Route 1: Request Better Fix ─────────────────────────────────────

@router.post("/request-better-fix", response_model=ReviewerFeedbackResponse)
async def request_better_fix(
    feedback: ReviewerFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Human reviewer requests an improved autofix for a specific finding.

    This records the feedback in the Knowledge Base and optionally triggers
    a re-generation of the autofix with additional reviewer context.
    """
    if feedback.action != "request_better_fix":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint only handles 'request_better_fix' actions",
        )

    # Record feedback in the pattern learner
    kb = _get_pattern_learner()
    kb_updated = False

    if kb:
        try:
            kb.record_feedback(
                suggestion_id=feedback.finding_id,
                accepted=False,  # Requesting a better fix = implicit rejection
                issue_type="autofix_quality",
                code_context=feedback.comment or "",
            )
            kb_updated = True
        except Exception as e:
            logger.warning(f"Failed to record feedback in KB: {e}")

    # Update Postgres telemetry if available
    try:
        from api.models.feedback import RuleTelemetry, SuggestionFeedback

        feedback_log = SuggestionFeedback(
            user_id=current_user.id,
            rule_type="autofix_quality",
            suggestion_id=feedback.finding_id,
            accepted=False,
        )
        db.add(feedback_log)
        db.commit()
    except Exception as e:
        logger.warning(f"Failed to record feedback in Postgres: {e}")
        db.rollback()

    return ReviewerFeedbackResponse(
        status="accepted",
        finding_id=feedback.finding_id,
        action_taken="Feedback recorded. Autofix quality flagged for improvement.",
        knowledge_base_updated=kb_updated,
        updated_fix=None,  # Future: trigger LLM re-generation here
        message=(
            f"Feedback recorded for finding {feedback.finding_id}. "
            "The agent will improve its autofix patterns based on your input."
        ),
    )


# ─── Route 2: Ignore Pattern ─────────────────────────────────────────

@router.post("/ignore-pattern", response_model=ReviewerFeedbackResponse)
async def ignore_pattern(
    feedback: ReviewerFeedbackRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Human reviewer marks a finding pattern for future suppression.

    The agent will learn to suppress similar patterns in future reviews
    by recording multiple rejections in the Knowledge Base, which triggers
    the SeverityOrchestrator's demotion logic.
    """
    if feedback.action != "ignore_pattern":
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="This endpoint only handles 'ignore_pattern' actions",
        )

    kb = _get_pattern_learner()
    kb_updated = False

    if kb:
        try:
            # Record strong rejection signal to trigger demotion
            kb.record_feedback(
                suggestion_id=feedback.finding_id,
                accepted=False,
                issue_type=f"suppressed:{feedback.finding_id}",
                code_context=feedback.comment or "Pattern suppressed by reviewer",
            )
            kb_updated = True
        except Exception as e:
            logger.warning(f"Failed to record suppression in KB: {e}")

    # Update Postgres telemetry
    try:
        from api.models.feedback import RuleTelemetry, SuggestionFeedback

        feedback_log = SuggestionFeedback(
            user_id=current_user.id,
            rule_type=f"suppressed:{feedback.finding_id}",
            suggestion_id=feedback.finding_id,
            accepted=False,
        )
        db.add(feedback_log)

        # Also update team-level telemetry to increase rejection rate
        telemetry = db.query(RuleTelemetry).filter(
            RuleTelemetry.team_id == current_user.team_id,
            RuleTelemetry.rule_type == f"suppressed:{feedback.finding_id}",
        ).first()

        if not telemetry:
            telemetry = RuleTelemetry(
                team_id=current_user.team_id,
                rule_type=f"suppressed:{feedback.finding_id}",
                total_suggestions=0,
                accepted_count=0,
                rejected_count=0,
                current_weight=100,
            )
            db.add(telemetry)

        telemetry.total_suggestions += 1
        telemetry.rejected_count += 1
        # Aggressive weight reduction for explicit suppression
        telemetry.current_weight = max(0, telemetry.current_weight - 20)

        db.commit()
    except Exception as e:
        logger.warning(f"Failed to update Postgres telemetry: {e}")
        db.rollback()

    return ReviewerFeedbackResponse(
        status="accepted",
        finding_id=feedback.finding_id,
        action_taken="Pattern marked for suppression in future reviews.",
        knowledge_base_updated=kb_updated,
        updated_fix=None,
        message=(
            f"Pattern associated with finding {feedback.finding_id} will be "
            "suppressed in future reviews. The agent's severity calibration "
            "has been updated."
        ),
    )


# ─── Route 3: Feedback History ────────────────────────────────────────

@router.get("/feedback-history")
async def get_review_feedback_history(
    limit: int = 20,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """
    Get recent review feedback actions for the current team.
    Shows both 'request_better_fix' and 'ignore_pattern' actions.
    """
    try:
        from api.models.feedback import SuggestionFeedback

        feedbacks = (
            db.query(SuggestionFeedback)
            .filter(SuggestionFeedback.user_id == current_user.id)
            .order_by(SuggestionFeedback.id.desc())
            .limit(limit)
            .all()
        )

        results = []
        for fb in feedbacks:
            action = "ignore_pattern" if fb.rule_type.startswith("suppressed:") else (
                "request_better_fix" if fb.rule_type == "autofix_quality" else "general_feedback"
            )
            results.append({
                "id": fb.id,
                "finding_id": fb.suggestion_id,
                "action": action,
                "rule_type": fb.rule_type,
                "accepted": fb.accepted,
            })

        return {
            "feedback_history": results,
            "total": len(results),
        }
    except Exception as e:
        logger.warning(f"Failed to retrieve feedback history: {e}")
        return {
            "feedback_history": [],
            "total": 0,
            "error": str(e),
        }
