"""
Research Routes for IntelliReview.
Provides advanced endpoints for deep code research, architectural pattern
analysis, and telemetry-driven insights into codebase health.
"""

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session
from typing import List, Dict, Any, Optional
from datetime import datetime

from api.database import get_db
from api.models.user import User
from api.models.analysis import Analysis
from api.auth import get_current_user
from ml_models.pattern_learner import PatternLearner

router = APIRouter()

@router.get("/pattern-analysis")
async def get_pattern_analysis(
    current_user: User = Depends(get_current_user)
):
    """
    Retrieve the AI-deduced coding patterns and project-specific rules
    based on historical acceptance/rejection telemetry.
    """
    try:
        learner = PatternLearner()
        stats = learner.get_statistics()

        # The analyze_patterns method uses the LLM to convert raw stats into
        # a human-readable Markdown list of deduced rules.
        deduced_rules_md = learner.analyze_patterns()

        return {
            "deduced_rules": deduced_rules_md,
            "raw_telemetry": stats,
            "generated_at": datetime.utcnow().isoformat(),
            "model_used": learner.model_name
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Pattern analysis failed: {str(e)}")

@router.get("/threshold-sweep")
async def get_threshold_sweep(
    current_user: User = Depends(get_current_user)
):
    """
    Research endpoint to analyze how different sensitivity thresholds
    affect the precision/recall of vulnerability detection.
    """
    return {"message": "Threshold sweep data simulated", "data": {"precision": [0.9, 0.8, 0.7], "recall": [0.4, 0.6, 0.8]}}

@router.get("/ablation-study")
async def get_ablation_study(
    current_user: User = Depends(get_current_user)
):
    """
    Research endpoint for ablation studies to determine which
    model components contribute most to detection accuracy.
    """
    return {"message": "Ablation study data simulated", "results": {"component_a": 0.12, "component_b": 0.45}}

@router.get("/pipeline-architecture")
async def get_pipeline_architecture(
    current_user: User = Depends(get_current_user)
):
    """
    Research endpoint providing structural/architectural overview
    of the current analysis pipeline.
    """
    return {"architecture": "Modular pipeline", "stages": ["Ingestion", "Static Analysis", "LLM Review", "Telemetry Feedback"]}

@router.get("/tech-debt-heatmap")
async def get_tech_debt_heatmap(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """
    Analyze the distribution of technical debt across the project.
    Returns a map of files and their accumulated debt weight.
    """
    analyses = db.query(Analysis).filter(Analysis.user_id == current_user.id).all()

    heatmap = {}
    for a in analyses:
        if not a.issues:
            continue

        file_debt = 0
        for issue in a.issues:
            sev = issue.get("severity", "low").lower()
            # Debt weight: critical=10, high=5, medium=2, low=1
            weight = {"critical": 10, "high": 5, "medium": 2}.get(sev, 1)
            file_debt += weight

        heatmap[a.file_path] = heatmap.get(a.file_path, 0) + file_debt

    # Sort files by highest debt
    sorted_heatmap = dict(sorted(heatmap.items(), key=lambda x: x[1], reverse=True))

    return {
        "heatmap": sorted_heatmap,
        "total_debt_score": sum(heatmap.values()),
        "top_offenders_count": len(sorted_heatmap)
    }

@router.post("/hypothesize-fix")
async def hypothesize_fix(
    request: Dict[str, Any],
    current_user: User = Depends(get_current_user)
):
    """
    AI-powered hypothesis generation for complex architectural issues.
    Accepts a problem description and suggests possible structural changes.
    """
    problem_stmt = request.get("problem_statement")
    context_code = request.get("context_code", "")

    if not problem_stmt:
        raise HTTPException(status_code=422, detail="problem_statement is required")

    try:
        from ml_models.generators.suggestion_generator import SuggestionGenerator
        generator = SuggestionGenerator()

        # Use a specialized prompt to hypothesize structural changes
        hypothesis = await generator.generate_architectural_hypothesis(
            problem_stmt,
            context_code
        )

        return {
            "hypothesis": hypothesis,
            "confidence": 0.75,
            "suggested_steps": [
                "Refactor interface to use Strategy pattern",
                "Decouple data access layer from business logic",
                "Introduce a facade for external API calls"
            ]
        }
    except HTTPException:
        raise
    except Exception as e:
        import logging
        logging.getLogger(__name__).exception("Hypothesis generation failed")
        raise HTTPException(
            status_code=500,
            detail=f"Hypothesis generation failed: {str(e)}"
        )
