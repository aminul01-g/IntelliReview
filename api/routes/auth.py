"""
Authentication Routes for IntelliReview.
Handles user registration, login, and token issuance.
"""

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, status, Response, Request
from fastapi.security import OAuth2PasswordRequestForm
from sqlalchemy.orm import Session
from datetime import timedelta

from api.database import get_db
from api.models.user import User, UserRole
from api.schemas.user import UserCreate, UserResponse, Token
from api.auth import (
    verify_password,
    get_password_hash,
    create_access_token,
    get_current_user,
)
from config.settings import settings

router = APIRouter()

@router.post("/register", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
async def register(user_in: UserCreate, db: Session = Depends(get_db)):
    """Register a new user."""
    # Check if user already exists
    existing_user = db.query(User).filter(
        (User.username == user_in.username) | (User.email == user_in.email)
    ).first()

    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Username or email already registered"
        )

    # Create user with hashed password
    new_user = User(
        username=user_in.username,
        email=user_in.email,
        hashed_password=get_password_hash(user_in.password),
        role=UserRole.developer,
        is_active=True
    )

    db.add(new_user)
    db.commit()
    db.refresh(new_user)
    return new_user

def _get_cookie_kwargs(value: Optional[str] = None) -> dict:
    """Helper to generate consistent cookie attributes based on environment."""
    cookie_kwargs = {
        "key": "auth_token",
        "value": value,
        "httponly": True,
    }
    if value:
        cookie_kwargs["max_age"] = settings.ACCESS_TOKEN_EXPIRE_MINUTES * 60

    samesite = settings.COOKIE_SAMESITE.lower()
    if settings.DEBUG or not settings.COOKIE_DOMAIN:
        cookie_kwargs["secure"] = False
        cookie_kwargs["samesite"] = "lax" if samesite == "lax" else samesite
    else:
        cookie_kwargs["secure"] = True
        # Browsers require Secure=True for SameSite=None
        cookie_kwargs["samesite"] = "none" if samesite == "none" else samesite
        cookie_kwargs["domain"] = settings.COOKIE_DOMAIN

    return cookie_kwargs


@router.post("/login", response_model=Token)
async def login(
    response: Response,
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    """Login and return JWT access token."""
    user = db.query(User).filter(User.username == form_data.username).first()

    if not user or not verify_password(form_data.password, user.hashed_password):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Incorrect username or password",
            headers={"WWW-Authenticate": "form-data"},
        )

    if not user.is_active:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Inactive user account"
        )

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": user.username},
        expires_delta=access_token_expires
    )

    response.set_cookie(**_get_cookie_kwargs(access_token))
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/me", response_model=UserResponse)
async def read_users_me(current_user: User = Depends(get_current_user)):
    """Get current user info."""
    return current_user

@router.post("/logout")
async def logout(response: Response):
    """Clear the auth cookie to end the session."""
    response.delete_cookie(**_get_cookie_kwargs())
    return {"message": "Logged out successfully"}

@router.post("/refresh", response_model=Token)
async def refresh_token(
    response: Response,
    request: Request,
    db: Session = Depends(get_db)
):
    """Silently refresh the JWT access token to prevent session expiry."""
    # Manually extract token from Authorization header if present
    auth_header = request.headers.get("Authorization")
    token = None
    if auth_header and auth_header.startswith("Bearer "):
        token = auth_header.split(" ")[1]

    # Use get_current_user but bypass expiration check to allow refreshing an expired token
    try:
        current_user = await get_current_user(request=request, token=token, db=db, verify_expiry=False)
    except HTTPException as e:
        print(f"DEBUG: Refresh failed at get_current_user: {e.detail} | Token provided: {bool(token)}")
        raise e

    access_token_expires = timedelta(minutes=settings.ACCESS_TOKEN_EXPIRE_MINUTES)
    access_token = create_access_token(
        data={"sub": current_user.username},
        expires_delta=access_token_expires
    )

    response.set_cookie(**_get_cookie_kwargs(access_token))
    return {"access_token": access_token, "token_type": "bearer"}

@router.get("/github/login")
async def github_login():
    """Initiate GitHub OAuth SSO Login flow."""
    return {
        "message": "SSO callback logic pending enterprise authentication service deployment.",
        "redirect_url": "https://github.com/login/oauth/authorize?client_id=xxx&scope=user,repo"
    }

@router.get("/github/callback")
async def github_callback(code: str):
    """Handle GitHub OAuth callback and exchange authorization code."""
    # TODO: Exchange code for access_token, fetch GitHub User API, and provision DB User
    raise HTTPException(
        status_code=status.HTTP_501_NOT_IMPLEMENTED,
        detail="SSO callback logic pending enterprise authentication service deployment."
    )
