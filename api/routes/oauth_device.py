from fastapi import APIRouter, Depends, HTTPException, status, Form
from sqlalchemy.orm import Session
from datetime import datetime, timedelta
import secrets
import string

from api.database import get_db
from api.models.user import OAuthDeviceCode, User
from api.auth import create_access_token, get_current_user

router = APIRouter()

def generate_user_code(length=8):
    """Generate a readable user verification code (e.g., A1B2C3D4)."""
    chars = string.ascii_uppercase + string.digits
    return ''.join(secrets.choice(chars) for _ in range(length))

@router.post("/device/code")
async def request_device_code(db: Session = Depends(get_db)):
    """Step 1: CLI requests a device code."""
    device_code = secrets.token_urlsafe(32)
    user_code = generate_user_code()
    
    expires_at = datetime.utcnow() + timedelta(minutes=15)
    
    new_code = OAuthDeviceCode(
        device_code=device_code,
        user_code=user_code,
        expires_at=expires_at
    )
    db.add(new_code)
    db.commit()
    
    return {
        "device_code": device_code,
        "user_code": user_code,
        "verification_uri": "http://localhost:3000/profile/device",
        "verification_uri_complete": f"http://localhost:3000/profile/device?code={user_code}",
        "expires_in": 900,
        "interval": 5
    }

@router.post("/device/verify")
async def verify_device_code(
    user_code: str = Form(...),
    db: Session = Depends(get_db),
    current_user: User = Depends(get_current_user)
):
    """Step 2: User approves the CLI session via their browser."""
    code_obj = db.query(OAuthDeviceCode).filter(
        OAuthDeviceCode.user_code == user_code
    ).first()
    
    if not code_obj:
        raise HTTPException(status_code=404, detail="Invalid user code.")
        
    if code_obj.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="User code expired.")
        
    if code_obj.is_authorized:
        raise HTTPException(status_code=400, detail="Code already authorized.")
        
    code_obj.is_authorized = True
    code_obj.user_id = current_user.id
    db.commit()
    
    return {"message": "Device successfully authorized. You can now return to your CLI."}

@router.post("/token")
async def poll_device_token(
    grant_type: str = Form(...),
    device_code: str = Form(None),
    db: Session = Depends(get_db)
):
    """Step 3: CLI polls for the access token."""
    if grant_type != "urn:ietf:params:oauth:grant-type:device_code":
        raise HTTPException(status_code=400, detail="unsupported_grant_type")
        
    if not device_code:
        raise HTTPException(status_code=400, detail="invalid_request")
        
    code_obj = db.query(OAuthDeviceCode).filter(
        OAuthDeviceCode.device_code == device_code
    ).first()
    
    if not code_obj:
        raise HTTPException(status_code=400, detail="invalid_grant")
        
    if code_obj.expires_at < datetime.utcnow():
        raise HTTPException(status_code=400, detail="expired_token")
        
    if not code_obj.is_authorized:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="authorization_pending"
        )
        
    # Get user to create token
    user = db.query(User).filter(User.id == code_obj.user_id).first()
    if not user:
        raise HTTPException(status_code=500, detail="Authorized user not found")
        
    access_token = create_access_token(data={"sub": user.username})
    
    # Cleanup used code
    db.delete(code_obj)
    db.commit()
    
    return {
        "access_token": access_token,
        "token_type": "bearer",
        "expires_in": 86400
    }
