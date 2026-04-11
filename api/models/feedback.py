from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from api.database import Base

class RuleTelemetry(Base):
    """Telemetry strictly tracks rule accept/rejection rates."""
    __tablename__ = "rule_telemetry"
    
    id = Column(Integer, primary_key=True, index=True)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True, index=True)
    rule_type = Column(String(100), index=True, nullable=False) # e.g. "orm_n_plus_one"
    rule_language = Column(String(20), nullable=True)
    
    # Simple aggregations
    total_suggestions = Column(Integer, default=0)
    accepted_count = Column(Integer, default=0)
    rejected_count = Column(Integer, default=0)
    
    # Store the moving average explicitly
    current_weight = Column(Integer, default=100) # 100 = 1.0 (baseline). <50 means suppressed.
    
    last_updated = Column(DateTime(timezone=True), onupdate=func.now())
    
    team = relationship("Team", backref="rule_stats")

class SuggestionFeedback(Base):
    """Individual logs mapping down to exact rule adjustments."""
    __tablename__ = "suggestion_feedback"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    rule_type = Column(String(100), nullable=False)
    suggestion_id = Column(String(255), nullable=True)
    accepted = Column(Boolean, nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    
    user = relationship("User", backref="feedbacks")
