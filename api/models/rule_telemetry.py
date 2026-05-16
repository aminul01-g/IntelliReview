from sqlalchemy import Column, Integer, String, DateTime, Float, ForeignKey, JSON, Boolean
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from api.database import Base


class RuleTelemetry(Base):
    """
    Tracks rule evaluation telemetry for learning and optimization.
    Stores per-rule statistics including false positive rates, processing time,
    and rejection rates to feed the learning loop.
    """
    __tablename__ = "rule_telemetry"

    id = Column(Integer, primary_key=True, index=True)
    rule_name = Column(String(100), index=True, nullable=False)
    file_path = Column(String(500), nullable=True)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="SET NULL"), nullable=True)

    # Evaluation stats
    was_triggered = Column(Boolean, default=False, nullable=False)
    was_correct = Column(Boolean, nullable=True)  # null = not yet judged
    confidence = Column(Float, nullable=True)  # 0.0 to 1.0

    # Timing
    evaluation_time_ms = Column(Float, nullable=True)

    # Context
    severity_override = Column(JSON, nullable=True)  # Any config overrides applied
    context_hash = Column(String(64), nullable=True)  # Hash of code context for deduplication

    # Timestamps
    created_at = Column(DateTime(timezone=True), server_default=func.now())

    # Relationships
    user = relationship("User", backref="rule_telemetry")
    project = relationship("Project", backref="rule_telemetry")