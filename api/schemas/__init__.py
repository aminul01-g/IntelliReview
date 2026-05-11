"""
Pydantic schemas package for IntelliReview API.
"""

from api.schemas.user import UserCreate, UserLogin, UserResponse, Token, TokenPayload
from api.schemas.analysis import (
    AnalysisRequest,
    AnalysisResponse,
    Issue,
    Metrics,
    AnalysisStatus,
)
from api.schemas.feedback_schemas import (
    FeedbackSubmit,
    FeedbackStats,
    RuleStats,
    ReviewerFeedbackRequest,
    ReviewerFeedbackResponse,
    AutofixDiff,
)

__all__ = [
    # User schemas
    "UserCreate",
    "UserLogin",
    "UserResponse",
    "Token",
    "TokenPayload",
    # Analysis schemas
    "AnalysisRequest",
    "AnalysisResponse",
    "Issue",
    "Metrics",
    "AnalysisStatus",
    # Feedback schemas
    "FeedbackSubmit",
    "FeedbackStats",
    "RuleStats",
]
