"""
Authentication and Authorization logic for IntelliReview.
Implements JWT-based authentication and GitHub OAuth integration.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional

from jose import JWTError, jwt
import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import OAuth2PasswordBearer
from sqlalchemy.orm import Session

from config.settings import settings
from api.database import get_db
from api.models.user import User, UserRole

oauth2_scheme = OAuth2PasswordBearer(tokenUrl=f"{settings.API_PREFIX}/auth/login")

def verify_password(plain_password: str, hashed_password: str) -> bool:
    """Verify a plain password against a hashed password."""
    # bcrypt requires bytes input
    return bcrypt.checkpw(plain_password.encode('utf-8'), hashed_password.encode('utf-8'))

def get_password_hash(password: str) -> str:
    """Generate a bcrypt hash from a password."""
    # bcrypt returns bytes, decode to string
    return bcrypt.hashpw(password.encode('utf-8'), bcrypt.gensalt()).decode('utf-8')

def create_access_token(data: dict, expires_delta: Optional[timedelta] = None) -> str:
    """Create a JWT access token."""
    to_encode = data.copy()
    expire = datetime.now(timezone.utc) + (expires_delta or timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES))
    to_encode.update({"exp": expire})
    return jwt.encode(to_encode, settings.SECRET_KEY, algorithm=settings.ALGORITHM)

async def get_current_user(request: Request, token: Optional[str] = None, db: Session = Depends(get_db), verify_expiry: bool = True) -> User:
    """
    Extract and validate the JWT token to return the current user.
    Checks both Authorization header and auth_token cookie.
    """
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )

    # Prioritize explicit token, then header, fallback to cookie
    final_token = token
    if not final_token and request:
        auth_header = request.headers.get("Authorization")
        if auth_header and auth_header.startswith("Bearer "):
            final_token = auth_header.split(" ")[1]
        elif not final_token:
            final_token = request.cookies.get("auth_token")

    if not final_token:
        raise credentials_exception

    try:
        # If verify_expiry is False, we ignore the expiration check
        payload = jwt.decode(
            final_token,
            settings.SECRET_KEY,
            algorithms=[settings.ALGORITHM],
            options={"verify_exp": verify_expiry}
        )
        username: str = payload.get("sub")
        if username is None:
            print(f"DEBUG: Token decoded but 'sub' is missing. Payload: {payload}")
            raise credentials_exception
    except JWTError as e:
        print(f"DEBUG: JWTError during decode: {str(e)} | token: {final_token[:10]}... | verify_expiry: {verify_expiry}")
        raise credentials_exception

    user = db.query(User).filter(User.username == username).first()
    if user is None:
        raise credentials_exception
    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )
    return user

async def get_admin_user(current_user: User = Depends(get_current_user)) -> User:
    """
    Ensure the current user has administrative privileges.
    """
    if current_user.role != UserRole.admin and not current_user.is_superuser:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrative access required"
        )
    return current_user
