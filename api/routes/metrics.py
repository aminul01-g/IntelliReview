from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from sqlalchemy import func
from typing import Dict
from datetime import datetime, timedelta

from api.database import get_db
from api.models.user import User
from api.models.analysis import Analysis
from api.auth import get_current_user

router = APIRouter()

@router.get("/user", response_model=Dict)
async def get_user_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get metrics for current user."""
    
    # Total analyses
    total_analyses = db.query(func.count(Analysis.id)).filter(
        Analysis.user_id == current_user.id
    ).scalar()
    
    # Analyses this week
    week_ago = datetime.utcnow() - timedelta(days=7)
    weekly_analyses = db.query(func.count(Analysis.id)).filter(
        Analysis.user_id == current_user.id,
        Analysis.created_at >= week_ago
    ).scalar()
    
    # By language
    language_stats = db.query(
        Analysis.language,
        func.count(Analysis.id)
    ).filter(
        Analysis.user_id == current_user.id
    ).group_by(Analysis.language).all()

    # Technical Debt calculation (simplified: critical=60min, high=30min, medium=15min, low=5min)
    analyses = db.query(Analysis).filter(Analysis.user_id == current_user.id).all()
    tech_debt_minutes = 0
    for analysis in analyses:
        if analysis.issues:
            for issue in analysis.issues:
                severity = issue.get("severity", "low").lower()
                if severity == "critical": tech_debt_minutes += 60
                elif severity == "high": tech_debt_minutes += 30
                elif severity == "medium": tech_debt_minutes += 15
                else: tech_debt_minutes += 5

    return {
        "total_analyses": total_analyses,
        "weekly_analyses": weekly_analyses,
        "language_breakdown": {lang: count for lang, count in language_stats},
        "technical_debt_hours": round(tech_debt_minutes / 60, 1),
        "user_since": current_user.created_at.isoformat()
    }

@router.get("/trends")
async def get_trends(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get analysis trends over the last 30 days."""
    thirty_days_ago = datetime.utcnow() - timedelta(days=30)
    
    trends = db.query(
        func.date(Analysis.created_at).label('date'),
        func.count(Analysis.id).label('count')
    ).filter(
        Analysis.user_id == current_user.id,
        Analysis.created_at >= thirty_days_ago
    ).group_by(func.date(Analysis.created_at)).order_by(func.date(Analysis.created_at)).all()
    
    return [{"date": str(t.date), "count": t.count} for t in trends]

@router.get("/team")
async def get_team_metrics(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get metrics for the user's team."""
    if not current_user.team_id:
        return {"error": "User not in a team"}
    
    # Get all users in the team
    team_members = db.query(User).filter(User.team_id == current_user.team_id).all()
    member_ids = [u.id for u in team_members]
    
    # Team total analyses
    total_analyses = db.query(func.count(Analysis.id)).filter(
        Analysis.user_id.in_(member_ids)
    ).scalar()
    
    # Issues breakdown for team
    analyses = db.query(Analysis).filter(Analysis.user_id.in_(member_ids)).all()
    severity_counts = {"critical": 0, "high": 0, "medium": 0, "low": 0}
    
    for analysis in analyses:
        if analysis.issues:
            for issue in analysis.issues:
                sev = issue.get("severity", "low").lower()
                if sev in severity_counts:
                    severity_counts[sev] += 1
    
    return {
        "team_name": current_user.team.name if current_user.team else "Unknown",
        "total_members": len(team_members),
        "total_analyses": total_analyses,
        "issue_distribution": severity_counts
    }