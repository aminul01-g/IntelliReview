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
    profile = relationship("UserProfile", back_populates="user", uselist=False)

class UserProfile(Base):
    """User Profile model for IntelliReview."""
    __tablename__ = "user_profiles"
    
    id = Column(Integer, primary_key=True, index=True)
    user_id = Column(Integer, ForeignKey("users.id"), unique=True, nullable=False)
    ai_style_guides = Column(JSON, nullable=True) # Custom AI linters/tones
    notification_preferences = Column(JSON, nullable=True)
    role_mappings = Column(JSON, nullable=True) # Corporate identities linking
    created_at = Column(DateTime(timezone=True), server_default=func.now())
    updated_at = Column(DateTime(timezone=True), onupdate=func.now())
    
    user = relationship("User", back_populates="profile")

class OAuthDeviceCode(Base):
    """OAuth 2.0 Device Code flow tracking table."""
    __tablename__ = "oauth_device_codes"
    
    id = Column(Integer, primary_key=True, index=True)
    device_code = Column(String(100), unique=True, index=True, nullable=False)
    user_code = Column(String(20), unique=True, index=True, nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=True) # Null until authorized
    is_authorized = Column(Boolean, default=False)
    expires_at = Column(DateTime(timezone=True), nullable=False)
    created_at = Column(DateTime(timezone=True), server_default=func.now())

