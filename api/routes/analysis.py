from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks
from sqlalchemy.orm import Session
from typing import List
import hashlib
from datetime import datetime
import time
import logging

logger = logging.getLogger(__name__)

from api.database import get_db
from api.models.user import User
from api.models.analysis import Analysis
from api.schemas.analysis import AnalysisRequest, AnalysisResponse, Issue, Metrics
from api.auth import get_current_user
from analyzer.parsers.python_parser import PythonParser
from analyzer.parsers.javascript_parser import JavaScriptParser
from analyzer.parsers.java_parser import JavaParser
from analyzer.parsers.cpp_parser import CppParser
from analyzer.metrics.complexity import ComplexityAnalyzer
from analyzer.metrics.duplication import DuplicationDetector
from analyzer.detectors.antipatterns import AntiPatternDetector
from analyzer.detectors.security import SecurityScanner
from analyzer.detectors.quality import QualityDetector
from ml_models.generators.suggestion_generator import SuggestionGenerator

router = APIRouter()

# Initialize analyzers
parsers = {
    "python": PythonParser(),
    "javascript": JavaScriptParser(),
    "java": JavaParser(),
    "cpp": CppParser(),
    "c": CppParser(),
}

complexity_analyzer = ComplexityAnalyzer()
duplication_detector = DuplicationDetector()
antipattern_detector = AntiPatternDetector()
security_scanner = SecurityScanner()
quality_detector = QualityDetector()
suggestion_generator = SuggestionGenerator(provider="huggingface")


@router.post("/analyze", response_model=AnalysisResponse)
async def analyze_code(
    request: AnalysisRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze code and return issues and suggestions."""
    start_time = time.time()
    
    # Technical Constraint: Max 10,000 lines
    line_count = len(request.code.split('\n'))
    if line_count > 10000:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="File too large. Maximum supported size is 10,000 lines."
        )
    
    # Validate language
    if request.language not in parsers:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Language '{request.language}' not supported"
        )
    
    # Create analysis record
    code_hash = hashlib.sha256(request.code.encode()).hexdigest()
    
    analysis = Analysis(
        user_id=current_user.id,
        file_path=request.file_path or "unknown",
        language=request.language,
        code_hash=code_hash,
        status="pending"
    )
    
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    
    try:
        # Parse code
        parser = parsers[request.language]
        ast = parser.parse(request.code, request.file_path or "temp")
        
        # Parallelize independent detectors
        import asyncio
        
        # 1. Run all static scanners in parallel
        static_tasks = [
            asyncio.to_thread(complexity_analyzer.analyze, request.code, request.language),
            asyncio.to_thread(duplication_detector.detect, request.code),
            asyncio.to_thread(antipattern_detector.detect, request.code, ast, request.language),
            asyncio.to_thread(security_scanner.scan, request.code, request.file_path or "temp.py", request.language),
            asyncio.to_thread(quality_detector.detect, request.code, request.file_path or "temp.py", request.language)
        ]
        
        metrics_data, duplicates, antipatterns, security_issues, quality_issues = await asyncio.gather(*static_tasks)
        
        # Combine all issues
        all_issues = antipatterns + security_issues + quality_issues
        
        # Add duplication issues
        for dup in duplicates:
            all_issues.append({
                "type": "code_duplication",
                "severity": "medium",
                "line": dup["block1_start"],
                "message": f"Duplicate code found (similarity: {dup['similarity']})",
                "suggestion": "Consider extracting duplicated code into a reusable function"
            })
        
        # Prepare issues and parallelize AI suggestions
        from ml_models.pattern_learner import PatternLearner
        pattern_learner = PatternLearner()
        
        filtered_issues = []
        ai_tasks = []
        
        # High severity issue limit for AI suggestions
        ai_limit = 5
        ai_count = 0

        for issue in all_issues:
            if not pattern_learner.should_suggest(issue.get("type", "unknown")):
                continue
                
            if issue.get("severity") in ["critical", "high"] and ai_count < ai_limit:
                ai_tasks.append(suggestion_generator.generate_suggestion_async(
                    request.code,
                    issue,
                    request.language
                ))
                ai_count += 1
                # Use a flag to identify this issue needs AI update
                issue["_needs_ai"] = True
            
            filtered_issues.append(issue)

        # Run AI suggestions in parallel
        if ai_tasks:
            ai_results = await asyncio.gather(*ai_tasks)
            
            # Map results back to issues
            res_idx = 0
            for issue in filtered_issues:
                if issue.get("_needs_ai"):
                    ai_suggestion = ai_results[res_idx]
                    issue["suggestion"] = ai_suggestion.get("suggestion", issue.get("suggestion"))
                    issue["confidence"] = ai_suggestion.get("confidence", 0.5)
                    del issue["_needs_ai"]
                    res_idx += 1
        
        enhanced_issues = filtered_issues

        # Update analysis record
        metrics_dict = {
            "lines_of_code": metrics_data.get("lines_of_code", len(request.code.split('\n'))),
            "complexity": metrics_data.get("average_complexity"),
            "maintainability_index": metrics_data.get("maintainability_index"),
            "duplication_percentage": len(duplicates) / max(len(request.code.split('\n')), 1) * 100
        }

        # Update analysis record
        analysis.status = "completed"
        analysis.completed_at = datetime.utcnow()
        analysis.issues = enhanced_issues
        analysis.metrics = metrics_dict
        analysis.processing_time = round(time.time() - start_time, 2)
        db.commit()
        
        return AnalysisResponse(
            analysis_id=analysis.id,
            status="completed",
            language=request.language,
            file_path=request.file_path,
            issues=[Issue(**i) for i in enhanced_issues],
            metrics=Metrics(**metrics_dict),
            suggestions_count=len(enhanced_issues),
            analyzed_at=analysis.completed_at,
            processing_time=round(time.time() - start_time, 2)
        )
    
    except Exception as e:
        logger.exception(f"Analysis failed: {str(e)}")
        analysis.status = "failed"
        db.commit()
        
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail=f"Analysis failed: {str(e)}"
        )


@router.get("/history", response_model=List[AnalysisResponse])
async def get_analysis_history(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's analysis history."""
    analyses = db.query(Analysis).filter(
        Analysis.user_id == current_user.id
    ).order_by(Analysis.created_at.desc()).limit(limit).all()
    
    results = []
    for a in analyses:
        try:
            results.append(AnalysisResponse(
                analysis_id=a.id,
                status=a.status or "completed",
                language=a.language,
                file_path=a.file_path,
                issues=[Issue(**i) for i in (a.issues or [])],
                metrics=Metrics(**(a.metrics or {"lines_of_code": 0})),
                suggestions_count=len(a.issues or []),
                analyzed_at=a.completed_at or a.created_at,
                processing_time=a.processing_time
            ))
        except Exception as e:
            logger.error(f"Error mapping analysis {a.id}: {e}")
            continue
            
    return results


@router.get("/history/{analysis_id}", response_model=AnalysisResponse)
async def get_analysis_result(
    analysis_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get detailed results for a specific analysis."""
    analysis = db.query(Analysis).filter(
        Analysis.id == analysis_id,
        Analysis.user_id == current_user.id
    ).first()
    
    if not analysis:
        raise HTTPException(status_code=404, detail="Analysis not found")
        
    return AnalysisResponse(
        analysis_id=analysis.id,
        status=analysis.status,
        language=analysis.language,
        file_path=analysis.file_path,
        issues=[Issue(**i) for i in (analysis.issues or [])],
        metrics=Metrics(**(analysis.metrics or {"lines_of_code": 0})),
        suggestions_count=len(analysis.issues or []),
        analyzed_at=analysis.completed_at or analysis.created_at,
        processing_time=analysis.processing_time
    )