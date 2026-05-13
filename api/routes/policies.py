"""
Policies Routes for IntelliReview.
Handles the management of team-specific and project-specific review policies,
including severity overrides and custom rule sets.
"""

from typing import List, Dict, Any, Optional
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from pydantic import BaseModel, Field

from api.database import get_db
from api.models.user import User, Team
from api.auth import get_current_user, get_admin_user

router = APIRouter()

class PolicyUpdateRequest(BaseModel):
    """Schema for updating team policies."""
    custom_rules: Optional[Dict[str, Any]] = Field(
        None, description="Map of rule IDs to their overrides (e.g. {'sql_injection': 'critical'})"
    )
    policy_name: Optional[str] = None

@router.get("/team/policy")
async def get_team_policy(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Retrieve the current review policy for the user's team."""
    if not current_user.team_id:
        return {"message": "User is not assigned to a team. Using global defaults.", "rules": {}}

    team = db.query(Team).filter(Team.id == current_user.team_id).first()
    if not team:
        raise HTTPException(status_code=404, detail="Team not found")

    return {
        "team_name": team.name,
        "custom_rules": team.custom_rules or {},
        "global_defaults": "Standard Enterprise Quality Gate"
    }

@router.post("/team/policy/update")
async def update_team_policy(
    request: PolicyUpdateRequest,
    current_user: User = Depends(get_admin_user), # Only admins can update policies
    db: Session = Depends(get_db)
):
    """Update the review policy for the current user's team."""
    if not current_user.team_id:
        raise HTTPException(status_code=400, detail="User must be assigned to a team to update policies")

    team = db.query(Team).filter(Team.id == current_user.team_id).first()

    if request.custom_rules is not None:
        # Merge existing rules with new overrides
        current_rules = team.custom_rules or {}
        current_rules.update(request.custom_rules)
        team.custom_rules = current_rules

    if request.policy_name:
        team.name = request.policy_name

    db.commit()

    return {
        "status": "success",
        "updated_rules": team.custom_rules,
        "message": f"Policy for team {team.name} has been updated."
    }

@router.get("/global/rules")
async def get_global_rules(
    current_user: User = Depends(get_current_user)
):
    """Return the set of all available system rules and their default severities."""
    # In a real system, this would load from a YAML config file in analyzer/rules/
    return {
        "security": ["sql_injection", "xss", "hardcoded_secrets", "insecure_api"],
        "performance": ["n_plus_one", "large_object_allocation", "nested_loops"],
        "style": ["naming_convention", "line_length", "docstring_missing"],
        "architecture": ["circular_dependency", "god_object", "leaky_abstraction"]
    }
