from sqlalchemy import Column, Integer, String, DateTime, Boolean, ForeignKey, JSON, Enum as SQLEnum
from sqlalchemy.sql import func
from sqlalchemy.orm import relationship
from api.database import Base
import enum

class UserRole(str, enum.Enum):
    admin = "admin"
    reviewer = "reviewer"
    developer = "developer"

class Team(Base):
    """Team model."""
    __tablename__ = "teams"
    
    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(100), unique=True, index=True, nullable=False)
    custom_rules = Column(JSON, nullable=True) # Team-specific rule customization
    created_at = Column(DateTime(timezone=True), server_default=func.now())

class User(Base):
    """User model."""
    __tablename__ = "users"
    
    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(50), unique=True, index=True, nullable=False)
    email = Column(String(100), unique=True, index=True, nullable=False)
    hashed_password = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_superuser = Column(Boolean, default=False)
    role = Column(SQLEnum(UserRole), default=UserRole.developer, nullable=False)
    team_id = Column(Integer, ForeignKey("teams.id"), nullable=True)
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    # Relationships
    team = relationship("Team", backref="members")

