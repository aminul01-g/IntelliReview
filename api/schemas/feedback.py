from pydantic import BaseModel, Field
from typing import Optional, Dict
from datetime import datetime

class FeedbackSubmit(BaseModel):
    """Request schema for submitting feedback on a suggestion."""
    suggestion_id: str = Field(..., description="The unique identifier of the suggestion")
    accepted: bool = Field(..., description="Whether the suggestion was accepted")
    issue_type: str = Field(..., description="The type of issue being feedbacked")
    comment: Optional[str] = Field(None, description="Optional reviewer comment")

class RuleStats(BaseModel):
    """Stats for a specific rule's performance."""
    total_suggestions: int
    acceptance_rate: float
    rejection_rate: float
    current_weight: int

class FeedbackStats(BaseModel):
    """Aggregate feedback statistics for a team."""
    statistics: Dict[str, RuleStats]
    total_issue_types: int
