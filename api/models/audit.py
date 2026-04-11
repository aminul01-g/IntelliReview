from sqlalchemy import Column, Integer, String, DateTime, ForeignKey, JSON
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from api.database import Base

class AuditLog(Base):
    """Audit Log model to track enterprise metrics."""
    __tablename__ = "audit_logs"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True)
    action = Column(String(50), nullable=False)
    resource_type = Column(String(50), nullable=False) # e.g. "analysis", "configuration"
    resource_id = Column(String(100), nullable=True)
    details = Column(JSON, nullable=True) # E.g. {"old_severity": "high", "new_severity": "ignored"}
    timestamp = Column(DateTime(timezone=True), server_default=func.now(), index=True)
    
    # Relationships
    user = relationship("User", backref="audit_trails")
