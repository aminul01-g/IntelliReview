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
ai_pattern_detector = AIPatternDetector()
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


@router.post("/upload")
async def analyze_uploaded_files(
    request: Request,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db)
):
    """Analyze uploaded files or folders. Accepts multiple files via multipart upload."""
    import os
    import asyncio
    
    # Safely parse the form data directly to avoid FastAPI 400 Pydantic errors on large multipart requests
    try:
        form_data = await request.form()
        files = form_data.getlist("files")
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Failed to parse multipart form data: {str(e)}")
    
    start_time = time.time()
    results = []
    skipped = []
    errors = []
    
    # Aggressively ignore common large binary or non-code directories
    COMMON_IGNORES = [
        "node_modules", ".git", ".venv", "venv", "__pycache__", "build", "dist",
        ".next", ".nuxt", "coverage", "vendor"
    ]
    
    # Filter and process files
    valid_files = []
    for f in files:
        filename = f.filename or "unknown"
        
        # Skip binary/non-code files and ignored directories
        path_parts = filename.replace("\\", "/").split("/")
        if any(part.startswith(".") for part in path_parts if part != ".") or any(part in COMMON_IGNORES for part in path_parts) or any(part in SKIP_PATTERNS for part in path_parts):
            skipped.append({"file": filename, "reason": "Ignored folder or dotfile"})
            continue
        
        ext = os.path.splitext(filename)[1].lower()
        # Binary file extensions to skip aggressively
        if ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".mp3", ".wav", ".zip", ".tar", ".gz", ".rar", ".pdf", ".exe", ".dll", ".so", ".dylib", ".class", ".pyc"]:
            skipped.append({"file": filename, "reason": f"Binary/Unsupported extension: {ext}"})
            continue

        lang = EXT_LANG_MAP.get(ext, "unknown")
        
        # Read file content
        try:
            content = (await f.read()).decode('utf-8', errors='replace')
        except Exception as e:
            errors.append({"file": filename, "error": f"Could not read file: {str(e)}"})
            continue
        
        # Skip empty files or very large files
        line_count = len(content.split('\n'))
        if line_count == 0:
            skipped.append({"file": filename, "reason": "Empty file"})
            continue
        if line_count > 10000:
            skipped.append({"file": filename, "reason": f"Too large ({line_count} lines, max 10,000)"})
            continue
        
        valid_files.append({"filename": filename, "content": content, "language": lang, "lines": line_count})
    
    if not valid_files:
        return {
            "project_summary": {
                "total_files": 0,
                "total_issues": 0,
                "processing_time": round(time.time() - start_time, 2),
            },
            "file_results": [],
            "skipped": skipped,
            "errors": errors,
        }
    
    # Analyze each file (cap at 20 files to avoid timeout)
    for file_info in valid_files[:20]:
        try:
            code = file_info["content"]
            lang = file_info["language"]
            fname = file_info["filename"]
            
            # Parse (fallback to empty dict if no AST parser exists for language)
            parser = parsers.get(lang)
            ast = parser.parse(code, fname) if parser else {}
            
            # Run static analysis
            metrics_data = complexity_analyzer.analyze(code, lang)
            duplicates = duplication_detector.detect(code)
            antipatterns = antipattern_detector.detect(code, ast, lang)
            security_issues = security_scanner.scan(code, fname, lang)
            quality_issues = quality_detector.detect(code, fname, lang)
            
            ai_patterns = ai_pattern_detector.detect(code, fname, lang)
            all_issues = antipatterns + security_issues + quality_issues + ai_patterns
            for dup in duplicates:
                all_issues.append({
                    "type": "code_duplication",
                    "severity": "medium",
                    "line": dup["block1_start"],
                    "message": f"Duplicate code found (similarity: {dup['similarity']})",
                    "suggestion": "Consider extracting duplicated code into a reusable function"
                })
            
            # Count by severity
            severity_counts = {}
            for issue in all_issues:
                sev = issue.get("severity", "info")
                severity_counts[sev] = severity_counts.get(sev, 0) + 1
            
            metrics_dict = {
                "lines_of_code": metrics_data.get("lines_of_code", file_info["lines"]),
                "complexity": metrics_data.get("average_complexity"),
                "maintainability_index": metrics_data.get("maintainability_index"),
                "duplication_percentage": round(len(duplicates) / max(file_info["lines"], 1) * 100, 1)
            }
            
            # Save to DB
            code_hash = hashlib.sha256(code.encode()).hexdigest()
            analysis = Analysis(
                user_id=current_user.id,
                file_path=fname,
                language=lang,
                code_hash=code_hash,
                status="completed",
                issues=all_issues,
                metrics=metrics_dict,
                processing_time=round(time.time() - start_time, 2),
                completed_at=datetime.utcnow()
            )
            db.add(analysis)
            db.commit()
            db.refresh(analysis)
            
            results.append({
                "analysis_id": analysis.id,
                "file_path": fname,
                "language": lang,
                "metrics": metrics_dict,
                "issue_count": len(all_issues),
                "severity_counts": severity_counts,
                "issues": all_issues[:10],  # Return top 10 issues per file to avoid huge payloads
                "status": "completed"
            })
        
        except Exception as e:
            logger.error(f"Error analyzing {file_info['filename']}: {e}")
            errors.append({"file": file_info["filename"], "error": str(e)})
    
    # Build project-level summary
    total_issues = sum(r["issue_count"] for r in results)
    total_lines = sum(r["metrics"]["lines_of_code"] for r in results)
    lang_breakdown = {}
    for r in results:
        lang_breakdown[r["language"]] = lang_breakdown.get(r["language"], 0) + 1
    
    # Compute overall health score (simple heuristic)
    critical_high = sum(
        r["severity_counts"].get("critical", 0) + r["severity_counts"].get("high", 0)
        for r in results
    )
    if total_lines > 0:
        health_score = max(0, min(100, 100 - (critical_high / max(total_lines, 1)) * 1000))
    else:
        health_score = 100
    
    project_summary_data = {
        "total_files": len(results),
        "total_lines": total_lines,
        "total_issues": total_issues,
        "health_score": round(health_score, 1),
        "language_breakdown": lang_breakdown,
        "processing_time": round(time.time() - start_time, 2),
    }
    
    # Generate AI Project-Level Architectural Review
    ai_project_review = None
    if results:
        try:
            # Build file manifest with code content for the AI agent
            file_manifest = []
            for i, r in enumerate(results):
                manifest_entry = {
                    "file_path": r["file_path"],
                    "language": r["language"],
                    "lines": r["metrics"]["lines_of_code"],
                    "issue_count": r["issue_count"],
                    "severity_counts": r["severity_counts"],
                    "issues": r["issues"],
                }
                # Attach code content from valid_files for the AI to read
                if i < len(valid_files):
                    manifest_entry["content"] = valid_files[i]["content"]
                file_manifest.append(manifest_entry)
            
            ai_project_review = await suggestion_generator.generate_project_review_async(
                file_manifest, project_summary_data
            )
        except Exception as e:
            logger.warning(f"Project AI review generation failed: {e}")
            ai_project_review = None
    
    return {
        "project_summary": project_summary_data,
        "ai_project_review": ai_project_review,
        "file_results": results,
        "skipped": skipped,
        "errors": errors,
    }


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
    current_user: User = Depends(get_current_user),
):
    """Review only the changed lines in a git diff.

    Accepts a unified diff (from `git diff`) and analyzes only the added/changed
    lines, producing a focused report on the delta quality.
    """
    parsed = _parse_unified_diff(request.diff)

    if not parsed:
        return {"message": "No parseable changes found in the diff", "files": []}

    results = []

    for entry in parsed:
        fname = entry["file"]
        ext = "." + fname.rsplit(".", 1)[-1] if "." in fname else ""
        lang = EXT_LANG_MAP.get(ext.lower())
        if not lang:
            continue

        # Build code from added lines across all hunks
        added_code = "\n".join(
            line for hunk in entry["hunks"] for line in hunk["added_lines"]
        )
        if not added_code.strip():
            continue

        # Run static analysis on the added code
        parser = parsers.get(lang)
        try:
            ast = parser.parse(added_code, fname) if parser else {}
            antipatterns = antipattern_detector.detect(added_code, ast, lang)
            security_issues = security_scanner.scan(added_code, fname, lang)
            quality_issues = quality_detector.detect(added_code, fname, lang)
            ai_patterns = ai_pattern_detector.detect(added_code, fname, lang)

            all_issues = antipatterns + security_issues + quality_issues + ai_patterns

            # Adjust line numbers to be relative to hunk start
            for hunk in entry["hunks"]:
                for issue in all_issues:
                    if issue["line"] <= len(hunk["added_lines"]):
                        issue["line"] = hunk["start"] + issue["line"] - 1

            if all_issues:
                results.append({
                    "file": fname,
                    "language": lang,
                    "added_lines": len(added_code.split("\n")),
                    "issues": all_issues[:15],
                    "issue_count": len(all_issues),
                })
        except Exception as e:
            logger.warning(f"Diff analysis failed for {fname}: {e}")

    # Score the diff quality
    total_issues = sum(r["issue_count"] for r in results)
    total_added = sum(r["added_lines"] for r in results)
    quality_verdict = "✅ Clean" if total_issues == 0 else (
        "⚠️ Needs attention" if total_issues < 5 else "🔴 Review required"
    )

    return {
        "verdict": quality_verdict,
        "total_added_lines": total_added,
        "total_issues": total_issues,
        "files_reviewed": len(results),
        "file_results": results,
    }


# ─── Custom Rules Endpoint ──────────────────────────────────────────

from analyzer.rules.custom_rules import CustomRuleEngine

class CustomRulesRequest(BaseModel):
    code: str
    language: str
    filename: str = "unknown"
    rules: List[dict]  # List of rule definitions

@router.post("/custom-rules")
async def run_custom_rules(
    request: CustomRulesRequest,
    current_user: User = Depends(get_current_user),
):
    """Evaluate custom YAML-style rules against code.

    Accepts a list of rule definitions and evaluates them against the
    provided code. Useful for enforcing team-specific conventions.
    """
    engine = CustomRuleEngine(rules=request.rules)
    issues = engine.evaluate(request.code, request.filename, request.language)

    return {
        "filename": request.filename,
        "language": request.language,
        "rules_evaluated": len(request.rules),
        "issues_found": len(issues),
        "issues": issues,
    }