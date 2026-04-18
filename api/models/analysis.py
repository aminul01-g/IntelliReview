from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, Text, JSON, Float
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from api.database import Base

class Analysis(Base):
    """Analysis model."""
    __tablename__ = "analyses"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id", ondelete="CASCADE"), nullable=False)
    project_id = Column(Integer, ForeignKey("projects.id", ondelete="CASCADE"), nullable=True)
    file_path = Column(String(500), nullable=False)
    language = Column(String(50), nullable=False)
    code_hash = Column(String(64), index=True)
    status = Column(String(20), default="pending")  # pending, completed, failed
    issues = Column(JSON, nullable=True)
    metrics = Column(JSON, nullable=True)
    original_code = Column(Text, nullable=True)
    processing_time = Column(Float, nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    completed_at = Column(DateTime(timezone=True))
    
    # Versioning
    rule_version = Column(String(50), nullable=True)
    schema_version = Column(String(50), nullable=False, server_default="1.0.0")
    
    # Relationships
    user = relationship("User", backref="analyses")
    project = relationship("Project", backref="analyses")
