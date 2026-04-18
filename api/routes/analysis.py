from fastapi import APIRouter, Depends, HTTPException, status, BackgroundTasks, UploadFile, File, Request
from sqlalchemy.orm import Session
from typing import List, Optional
import hashlib
from datetime import datetime
import time
import logging

logger = logging.getLogger(__name__)

from api.database import get_db
from api.models.user import User
from api.models.analysis import Analysis
from api.models.project import Project
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
from analyzer.detectors.ai_patterns import AIPatternDetector
from analyzer.context.project_context import ProjectContextBuilder
from ml_models.generators.suggestion_generator import SuggestionGenerator

router = APIRouter()

def _generate_issue_id(issue: dict) -> str:
    """Generate a deterministic ID for an issue so feedback telemetry is stable."""
    raw = f"{issue.get('type', '')}:{issue.get('line', 0)}:{issue.get('message', '')}"
    return hashlib.sha256(raw.encode()).hexdigest()[:12]

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
ai_pattern_detector = AIPatternDetector()
project_context_builder = ProjectContextBuilder()
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
    
    # Language defaults to unknown if not mapped, but we don't reject it anymore!
    if not request.language:
        request.language = "unknown"
    
    # Create analysis record
    code_hash = hashlib.sha256(request.code.encode()).hexdigest()
    
    analysis = Analysis(
        user_id=current_user.id,
        file_path=request.file_path or "unknown",
        language=request.language,
        code_hash=code_hash,
        original_code=request.code,
        status="pending"
    )
    
    db.add(analysis)
    db.commit()
    db.refresh(analysis)
    
    try:
        # Parse code if we have a parser for the language
        parser = parsers.get(request.language)
        ast = parser.parse(request.code, request.file_path or "temp") if parser else {}
        
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
        ai_patterns = ai_pattern_detector.detect(request.code, request.file_path or "unknown", request.language)
        all_issues = antipatterns + security_issues + quality_issues + ai_patterns
        
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

        # Generate a single executive-level AI overview for the whole file
        try:
            ai_overview_text = await suggestion_generator.generate_general_review_async(
                request.code, all_issues, request.language
            )
        except Exception as e:
            logger.warning(f"AI overview generation failed: {e}")
            ai_overview_text = None

        # Inject it as a special issue at the top of the list
        if ai_overview_text:
            overview_issue = {
                "type": "ai_overview",
                "severity": "info",
                "line": 0,
                "message": "Executive AI Code Review",
                "suggestion": ai_overview_text
            }
            enhanced_issues = [overview_issue] + enhanced_issues

        # === AUTO-FIX: Generate unified diff patches for files with critical/high issues ===
        auto_fixes = []
        try:
            critical_count = sum(1 for i in enhanced_issues if i.get("severity") in ["critical", "high"])
            if critical_count > 0:
                fix_patch = await suggestion_generator.generate_auto_fix_async(
                    code=request.code,
                    issues=enhanced_issues,
                    language=request.language,
                    filename=request.file_path or "unknown",
                    plan_md=None
                )
                if fix_patch and fix_patch.get("diff"):
                    auto_fixes.append(fix_patch)
        except Exception as e:
            logger.warning(f"Auto-fix generation failed: {e}")

        # Generate deterministic IDs for all issues
        for issue in enhanced_issues:
            if not issue.get("id"):
                issue["id"] = _generate_issue_id(issue)

        # Update analysis record
        metrics_dict = {
            "lines_of_code": metrics_data.get("lines_of_code", len(request.code.split('\n'))),
            "complexity": metrics_data.get("average_complexity"),
            "maintainability_index": metrics_data.get("maintainability_index"),
            "duplication_percentage": len(duplicates) / max(len(request.code.split('\n')), 1) * 100
        }

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
            processing_time=round(time.time() - start_time, 2),
            auto_fixes=auto_fixes
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
    project_id: int = None,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get user's analysis history.
    
    By default, returns only 'loose file' analyses (standalone snippets
    that were NOT uploaded as part of a project folder).
    Pass project_id to get analyses for a specific project instead.
    """
    query = db.query(Analysis).filter(
        Analysis.user_id == current_user.id
    )
    
    if project_id is not None:
        # Return analyses belonging to a specific project
        query = query.filter(Analysis.project_id == project_id)
    else:
        # Default: return only loose files (no project association)
        query = query.filter(Analysis.project_id.is_(None))
    
    analyses = query.order_by(Analysis.created_at.desc()).limit(limit).all()
    
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

@router.get("/projects")
async def get_projects_history(
    limit: int = 10,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Get persistent smart-tabs of uploaded projects."""
    projects = db.query(Project).filter(
        Project.user_id == current_user.id
    ).order_by(Project.created_at.desc()).limit(limit).all()
    
    return [
        {
            "id": p.id,
            "name": p.name,
            "plan_md": p.plan_md,
            "created_at": p.created_at
        } for p in projects
    ]

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


# Extension to language mapping
EXT_LANG_MAP = {
    '.py': 'python',
    '.js': 'javascript', '.jsx': 'javascript', '.mjs': 'javascript',
    '.ts': 'javascript', '.tsx': 'javascript',
    '.java': 'java',
    '.c': 'c', '.h': 'c',
    '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp', '.hpp': 'cpp',
}

# Files/dirs to always skip
SKIP_PATTERNS = {
    'node_modules', '__pycache__', '.git', '.venv', 'venv', 'dist', 'build',
    '.next', '.nuxt', 'target', 'bin', 'obj', '.idea', '.vscode',
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
}


import asyncio

# In-memory dictionary to hold statuses for tasks executing locally via fallback
local_task_states = {}

@router.post("/upload")
async def analyze_uploaded_files(
    request: Request,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user)
):
    """Analyze uploaded files asynchronously via Celery, falling back to BackgroundTasks if unreachable."""
    import os
    import uuid
    from api.tasks.analysis_tasks import process_upload_task, _process_upload_async
    
    try:
        form_data = await request.form()
        files = form_data.getlist("files")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse multipart form data: {str(e)}")
        
    task_id = str(uuid.uuid4())
    task_dir = os.path.join("scratch", "uploads", task_id)
    os.makedirs(task_dir, exist_ok=True)
    
    for f in files:
        filename = f.filename or "unknown"
        content = await f.read()
        file_path = os.path.join(task_dir, filename)
        os.makedirs(os.path.dirname(file_path), exist_ok=True)
        with open(file_path, "wb") as out:
            out.write(content)
            
    # Step 1: Attempt Celery enqueue
    try:
        task = process_upload_task.apply_async(args=[task_id, current_user.id], task_id=task_id)
        return {"task_id": task.id, "status": "processing"}
    except Exception as e:
        logger.warning(f"Celery enqueue failed, falling back to local BackgroundTasks: {e}")
        
    # Step 2: Fallback to local background task execution
    local_task_states[task_id] = {"status": "PENDING", "info": "Queued for local processing..."}
    
    async def fallback_worker(tid: str, uid: int):
        class DummyTask:
            def update_state(self, state, meta=None):
                local_task_states[tid]["status"] = state
                if meta and 'status' in meta:
                    local_task_states[tid]["info"] = meta['status']
                    
        try:
            res = await _process_upload_async(DummyTask(), tid, uid)
            local_task_states[tid]["status"] = "SUCCESS"
            local_task_states[tid]["result"] = res
        except Exception as exc:
            logger.exception("Local fallback task failed")
            local_task_states[tid]["status"] = "FAILURE"
            local_task_states[tid]["error"] = str(exc)
            
    # Execute immediately in background, returning task_id to frontend
    background_tasks.add_task(fallback_worker, task_id, current_user.id)
    
    return {"task_id": task_id, "status": "processing", "fallback": True}

@router.get("/upload/status/{task_id}")
async def get_upload_status(task_id: str):
    """Poll Celery task status, or check local fallback states."""
    # First check fallback dictionary
    if task_id in local_task_states:
        state = local_task_states[task_id]
        if state["status"] == "PENDING":
            return {"status": state["status"], "info": state.get("info", "Queued waiting for workers...")}
        elif state["status"] not in ["FAILURE", "SUCCESS"]:
            return {"status": state["status"], "info": state.get("info", "Processing...")}
        elif state["status"] == "SUCCESS":
            return {"status": "SUCCESS", "info": state.get("info"), "result": state.get("result")}
        else:
            return {"status": "FAILURE", "error": state.get("error", "Unknown internal error")}
            
    # Query celery
    try:
        from api.celery_app import celery_app
        task_result = celery_app.AsyncResult(task_id)
        
        if task_result.state == 'PENDING':
            response = {"status": task_result.state, "info": "Queued waiting for workers..."}
        elif task_result.state != 'FAILURE':
            response = {"status": task_result.state, "info": task_result.info.get('status', '') if isinstance(task_result.info, dict) else str(task_result.info)}
            if task_result.state == 'SUCCESS':
                response["result"] = task_result.get()
        else:
            response = {"status": task_result.state, "error": str(task_result.info)}
        return response
    except Exception as e:
        logger.warning(f"Error querying celery result store: {e}")
        # Could be an old task that celery lost connection to
        return {"status": "FAILURE", "error": f"Lost connection to task backend: {e}"}


# ─── Diff Review Mode ───────────────────────────────────────────────
# Reviews only the changed lines in a unified diff, producing focused
# analysis on what actually changed rather than the entire file.

from pydantic import BaseModel

class DiffReviewRequest(BaseModel):
    diff: str  # Unified diff text (output of `git diff`)
    context_lines: int = 3  # Extra context lines around changes

def _parse_unified_diff(diff_text: str) -> List[dict]:
    """Parse a unified diff into a list of changed file entries."""
    files = []
    current_file = None
    current_hunks = []

    for line in diff_text.split("\n"):
        # New file header
        if line.startswith("+++ b/"):
            fname = line[6:]
            if current_file:
                files.append({"file": current_file, "hunks": current_hunks})
            current_file = fname
            current_hunks = []
        elif line.startswith("@@"):
            # Hunk header like @@ -10,5 +10,8 @@
            import re
            match = re.search(r'\+(\d+)', line)
            start_line = int(match.group(1)) if match else 1
            current_hunks.append({"start": start_line, "added_lines": [], "context": []})
        elif current_hunks:
            if line.startswith("+") and not line.startswith("+++"):
                current_hunks[-1]["added_lines"].append(line[1:])
            elif line.startswith(" "):
                current_hunks[-1]["context"].append(line[1:])

    if current_file:
        files.append({"file": current_file, "hunks": current_hunks})

    return files


@router.post("/diff-review")
async def review_diff(
    request: DiffReviewRequest,
    background_tasks: BackgroundTasks,
    current_user: User = Depends(get_current_user),
):
    """Review only the changed lines in a git diff utilizing AST Tech Debt Agents mapping via Celery.
    
    Accepts a unified diff (from `git diff`) and triggers a background 
    Language Chain agent to do focused Tech Debt analysis on the mutated logic blocks.
    Falls back to normal asyncio BackgroundTasks if Celery/Redis are unreachable.
    """
    import uuid
    from api.tasks.analysis_tasks import analyze_tech_debt_task, _analyze_tech_debt_async
    
    # We heuristically guess the main language from the diff
    import re
    language = "unknown"
    match = re.search(r'\+\+\+ b/(.*?(\.[a-z]+))', request.diff)
    if match:
        ext = match.group(2).lower()
        language = EXT_LANG_MAP.get(ext, "unknown")
    
    task_id = str(uuid.uuid4())
    
    try:
        task = analyze_tech_debt_task.apply_async(args=[request.diff, language], task_id=task_id)
        return {"task_id": task.id, "status": "processing"}
    except Exception as e:
        logger.warning(f"Celery enqueue for diff-review failed, falling back locally: {e}")
        
    # Local Fallback Execution
    local_task_states[task_id] = {"status": "PENDING", "info": "Queued locally for Diff Review..."}

    async def fallback_diff_worker(tid: str):
        class DummyTask:
            def update_state(self, state, meta=None):
                local_task_states[tid]["status"] = state
                if meta and 'status' in meta:
                    local_task_states[tid]["info"] = meta['status']
                    
        try:
            res = await _analyze_tech_debt_async(DummyTask(), request.diff, language)
            local_task_states[tid]["status"] = "SUCCESS"
            local_task_states[tid]["result"] = res
        except Exception as exc:
            logger.exception("Local fallback diff task failed")
            local_task_states[tid]["status"] = "FAILURE"
            local_task_states[tid]["error"] = str(exc)
            
    background_tasks.add_task(fallback_diff_worker, task_id)
    return {"task_id": task_id, "status": "processing", "fallback": True}


# ─── Custom Rules Endpoint ──────────────────────────────────────────

from analyzer.rules.custom_rules import CustomRuleEngine

class CustomRulesRequest(BaseModel):
    code: str
    language: str
    filename: str = "unknown"
    rules: Optional[List[dict]] = None  # List of rule definitions
    rules_yaml: Optional[str] = None    # Raw YAML string from custom rules editor

@router.post("/custom-rules")
async def run_custom_rules(
    request: CustomRulesRequest,
    current_user: User = Depends(get_current_user),
):
    """Evaluate custom YAML-style rules against code.

    Accepts a list of rule definitions and evaluates them against the
    provided code. Useful for enforcing team-specific conventions.
    """
    if request.rules_yaml:
        import yaml
        from fastapi import HTTPException, status
        try:
            data = yaml.safe_load(request.rules_yaml) or {}
            parsed_rules = data.get("rules", []) if isinstance(data, dict) else data
        except Exception as e:
            raise HTTPException(status_code=status.HTTP_400_BAD_REQUEST, detail=f"Invalid YAML format: {str(e)}")
    else:
        parsed_rules = request.rules or []

    engine = CustomRuleEngine(rules=parsed_rules)
    issues = engine.evaluate(request.code, request.filename, request.language)

    return {
        "filename": request.filename,
        "language": request.language,
        "rules_evaluated": len(parsed_rules),
        "issues_found": len(issues),
        "issues": issues,
    }