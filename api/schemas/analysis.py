from pydantic import BaseModel, Field
from typing import List, Optional, Dict
from datetime import datetime

class AnalysisRequest(BaseModel):
    """Request schema for code analysis."""
    code: str = Field(..., description="Source code to analyze")
    language: str = Field(..., description="Programming language")
    file_path: Optional[str] = Field(None, description="File path (optional)")
    options: Optional[Dict] = Field(default_factory=dict, description="Analysis options")

class Issue(BaseModel):
    """Code issue schema."""
    id: Optional[str] = None
    type: str
    severity: str
    line: int
    message: str
    suggestion: Optional[str] = None
    confidence: Optional[float] = None
    quick_fix: Optional[str] = None
    cwe: Optional[str] = None
    reference_url: Optional[str] = None

class Metrics(BaseModel):
    """Code metrics schema."""
    lines_of_code: int
    complexity: Optional[float] = None
    maintainability_index: Optional[float] = None
    duplication_percentage: Optional[float] = None

class AnalysisResponse(BaseModel):
    """Response schema for analysis."""
    analysis_id: int
    status: str
    language: str
    file_path: Optional[str] = None
    original_code: Optional[str] = None
    issues: List[Issue]
    metrics: Metrics
    suggestions_count: int
    analyzed_at: datetime
    processing_time: Optional[float] = None
    auto_fixes: Optional[List[Dict]] = None
    
    class Config:
        from_attributes = True

