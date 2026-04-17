from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from typing import List, Dict, Any

from analyzer.rules.policy_engine import engine
from api.models.user import User
from api.auth import get_current_user

router = APIRouter()

class GlobalPoliciesRequest(BaseModel):
    rules: List[Dict[str, Any]]

@router.get("/global")
async def get_global_policies(current_user: User = Depends(get_current_user)):
    """Retrieve org-level policy rules."""
    return engine.global_policies

@router.put("/global", status_code=status.HTTP_200_OK)
async def update_global_policies(
    request: GlobalPoliciesRequest,
    current_user: User = Depends(get_current_user)
):
    """
    Update org-level global policies.
    Only admins should be able to do this, in a real system we'd check current_user.role
    """
    engine.set_global_policies(request.rules)
    return {"message": "Global policies updated successfully", "rules_count": len(request.rules)}
