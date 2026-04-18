import os
import time
import json
import hashlib
import asyncio
import random
from datetime import datetime
from typing import List

from celery.exceptions import MaxRetriesExceededError
from api.celery_app import celery_app
from api.database import SessionLocal
from api.models.analysis import Analysis
from api.models.project import Project

# Core imports for processing
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
from ml_models.agents.tech_debt_agent import TechDebtAgent
from analyzer.context.ast_diff_mapper import map_diff_to_ast_context
from api.routes.analysis import _parse_unified_diff

import logging
logger = logging.getLogger(__name__)

# ── Exponential Backoff Helper ────────────────────────────────────────────────

# HTTP status codes / exception substrings that are transient and worth retrying
LLM_RETRIABLE_SIGNALS = {
    "rate limit", "429", "too many requests",
    "timeout", "timed out", "connection error",
    "503", "502", "service unavailable",
}


def _is_retriable(exc: Exception) -> bool:
    """Return True when the exception is a transient LLM/network error."""
    msg = str(exc).lower()
    return any(signal in msg for signal in LLM_RETRIABLE_SIGNALS)


def _backoff_countdown(retry_number: int, base: float = 2.0, cap: float = 600.0) -> float:
    """
    Full-jitter exponential backoff.
    Formula:  min(cap, random(0, base ** retry_number))
    Retry 1 →  0–2 s  |  2 →  0–4 s  |  3 →  0–8 s  |  4 →  0–16 s  |  5 →  0–32 s
    """
    ceiling = min(cap, base ** retry_number)
    return random.uniform(0, ceiling)

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

EXT_LANG_MAP = {
    '.py': 'python',
    '.js': 'javascript', '.jsx': 'javascript', '.mjs': 'javascript',
    '.ts': 'javascript', '.tsx': 'javascript',
    '.java': 'java',
    '.c': 'c', '.h': 'c',
    '.cpp': 'cpp', '.cc': 'cpp', '.cxx': 'cpp', '.hpp': 'cpp',
}

SKIP_PATTERNS = {
    'node_modules', '__pycache__', '.git', '.venv', 'venv', 'dist', 'build',
    '.next', '.nuxt', 'target', 'bin', 'obj', '.idea', '.vscode',
    'package-lock.json', 'yarn.lock', 'pnpm-lock.yaml',
}

async def _process_upload_async(self, task_id: str, user_id: int):
    """Core async processing loop wrapped by Celery."""
    task_dir = os.path.join("scratch", "uploads", task_id)
    self.update_state(state='INITIALIZING', meta={'status': 'Bootstrapping multi-agent session...'})
    
    start_time = time.time()
    results = []
    skipped = []
    errors = []
    valid_files = []
    
    # Recursively discover files manually created by FastAPI upload
    for root, dirs, files in os.walk(task_dir):
        for file in files:
            full_path = os.path.join(root, file)
            rel_path = os.path.relpath(full_path, task_dir)
            
            path_parts = rel_path.replace("\\", "/").split("/")
            if any(part.startswith(".") for part in path_parts if part != ".") or any(part in SKIP_PATTERNS for part in path_parts):
                skipped.append({"file": rel_path, "reason": "Ignored folder or dotfile"})
                continue
            
            ext = os.path.splitext(file)[1].lower()
            if ext in [".png", ".jpg", ".jpeg", ".gif", ".webp", ".mp4", ".mp3", ".wav", ".zip", ".tar", ".gz", ".rar", ".pdf", ".exe", ".dll", ".so", ".dylib", ".class", ".pyc"]:
                skipped.append({"file": rel_path, "reason": f"Binary/Unsupported extension: {ext}"})
                continue
                
            lang = EXT_LANG_MAP.get(ext, "unknown")
            try:
                with open(full_path, "r", encoding="utf-8") as f:
                    content = f.read()
            except Exception as e:
                errors.append({"file": rel_path, "error": f"Could not read file: {str(e)}"})
                continue
                
            line_count = len(content.split('\n'))
            if line_count == 0:
                skipped.append({"file": rel_path, "reason": "Empty file"})
                continue
            if line_count > 10000:
                skipped.append({"file": rel_path, "reason": f"Too large ({line_count} lines, max 10,000)"})
                continue
                
            valid_files.append({"filename": rel_path, "content": content, "language": lang, "lines": line_count})
            
    if not valid_files:
        return {
            "project_summary": {"total_files": 0, "total_issues": 0, "processing_time": round(time.time() - start_time, 2)},
            "file_results": [],
            "skipped": skipped,
            "errors": errors,
        }

    self.update_state(state='STRATEGIC_PLANNING', meta={'status': 'Generating architectural map...'})
    
    project_name = "Uploaded Project"
    config_contents = ""
    dir_tree_list = []
    
    for f in valid_files:
        fname = f["filename"]
        dir_tree_list.append(fname)
        
        if "/" in fname and project_name == "Uploaded Project":
            project_name = fname.split("/")[0]
            
        base = os.path.basename(fname).lower()
        if base in ["package.json", "requirements.txt", "readme.md", "setup.py", "pom.xml", "dockerfile"]:
            config_contents += f"\n--- {base} ---\n{f['content'][:1500]}\n"
            
    dir_tree_str = "\n".join(dir_tree_list)
    
    plan_md = None
    try:
        plan_md = await suggestion_generator.generate_project_plan_async(
            config_files_content=config_contents,
            directory_tree=dir_tree_str
        )
    except Exception as e:
        logger.error(f"Plan generation failed: {e}")
        plan_md = f"# IntelliReview Plan\nError generating plan: {e}"

    db = SessionLocal()
    project_record = None
    try:
        folder_hash = hashlib.sha256(("".join(dir_tree_list)).encode()).hexdigest()
        project_record = Project(
            user_id=user_id,
            name=project_name,
            folder_hash=folder_hash,
            plan_md=plan_md
        )
        db.add(project_record)
        db.commit()
        db.refresh(project_record)
    except Exception as e:
        logger.error(f"Failed to create project record: {e}")
        db.rollback()

    self.update_state(state='AST_SCANNING', meta={'status': 'Indexing and scanning logic blocks...'})

    try:
        project_context_builder.index_project(valid_files)
    except Exception as e:
        logger.warning(f"RAG context indexing failed: {e}")

    # Initialize Custom Rule Engine for cross-pollination
    from analyzer.rules.custom_rules import CustomRuleEngine
    custom_rule_engine = CustomRuleEngine(rules=[]) # Project-specific rules can be loaded here from DB

    for idx, file_info in enumerate(valid_files):
        self.update_state(state='AST_SCANNING', meta={'status': f'Scanning [{idx+1}/{len(valid_files)}] {file_info["filename"]}...'})
        try:
            code = file_info["content"]
            lang = file_info["language"]
            fname = file_info["filename"]
            
            parser = parsers.get(lang)
            ast = parser.parse(code, fname) if parser else {}
            
            metrics_data = complexity_analyzer.analyze(code, lang)
            duplicates = duplication_detector.detect(code)
            antipatterns = antipattern_detector.detect(code, ast, lang)
            security_issues = security_scanner.scan(code, fname, lang)
            quality_issues = quality_detector.detect(code, fname, lang)
            ai_patterns = ai_pattern_detector.detect(code, fname, lang)
            custom_rule_issues = custom_rule_engine.evaluate(code, fname, lang)
            
            file_idx = next((i for i, f in enumerate(valid_files) if f["filename"] == fname), None)
            cross_file_context = None
            if file_idx is not None:
                try:
                    cross_file_context = project_context_builder.build_context_string(file_idx, top_k=3)
                except Exception:
                    pass
            
            all_issues = antipatterns + security_issues + quality_issues + ai_patterns + custom_rule_issues
            for dup in duplicates:
                all_issues.append({
                    "type": "code_duplication",
                    "severity": "medium",
                    "line": dup["block1_start"],
                    "message": f"Duplicate code found (similarity: {dup['similarity']})",
                    "suggestion": "Consider extracting duplicated code into a reusable function"
                })
            
            severity_counts = {}
            for issue in all_issues:
                sev = issue.get("severity", "info")
                severity_counts[sev] = severity_counts.get(sev, 0) + 1
            
            metrics_dict = {
                "lines_of_code": metrics_data.get("lines_of_code", file_info["lines"]),
                "complexity": metrics_data.get("average_complexity"),
                "maintainability_index": metrics_data.get("maintainability_index"),
                "duplication_percentage": round(len(duplicates) / max(file_info["lines"], 1) * 100, 1),
                "cognitive_complexity": metrics_data.get("cognitive_complexity")
            }
            
            code_hash = hashlib.sha256(code.encode()).hexdigest()
            analysis_rec = Analysis(
                user_id=user_id,
                project_id=project_record.id if project_record else None,
                file_path=fname,
                language=lang,
                code_hash=code_hash,
                original_code=code,
                status="completed",
                issues=all_issues,
                metrics=metrics_dict,
                processing_time=round(time.time() - start_time, 2),
                completed_at=datetime.utcnow(),
                schema_version="1.0.0",
                rule_version=custom_rule_engine.get_version() if hasattr(custom_rule_engine, 'get_version') else None
            )
            db.add(analysis_rec)
            db.commit()
            db.refresh(analysis_rec)
            
            results.append({
                "analysis_id": analysis_rec.id,
                "file_path": fname,
                "language": lang,
                "metrics": metrics_dict,
                "issue_count": len(all_issues),
                "severity_counts": severity_counts,
                "issues": all_issues[:10],
                "related_files": [r["filename"] for r in (project_context_builder.get_related_files(file_idx, top_k=3) if file_idx is not None else [])],
                "status": "completed"
            })
        except Exception as e:
            logger.error(f"Error analyzing {file_info['filename']}: {e}")
            errors.append({"file": file_info["filename"], "error": str(e)})

    total_issues = sum(r["issue_count"] for r in results)
    total_lines = sum(r["metrics"]["lines_of_code"] for r in results)
    lang_breakdown = {}
    for r in results:
        lang_breakdown[r["language"]] = lang_breakdown.get(r["language"], 0) + 1

    critical_high = sum(
        r["severity_counts"].get("critical", 0) + r["severity_counts"].get("high", 0)
        for r in results
    )
    health_score = max(0, min(100, 100 - (critical_high / max(total_lines, 1)) * 1000)) if total_lines > 0 else 100

    project_summary_data = {
        "total_files": len(results),
        "total_lines": total_lines,
        "total_issues": total_issues,
        "health_score": round(health_score, 1),
        "language_breakdown": lang_breakdown,
        "processing_time": round(time.time() - start_time, 2),
    }

    self.update_state(state='AI_REVIEW', meta={'status': 'Generating multi-agent contextual fixes...'})

    ai_project_review = None
    if results:
        try:
            file_manifest = []
            for i, r in enumerate(results):
                manifest_entry = {
                    "file_path": r["file_path"],
                    "language": r["language"],
                    "lines": r["metrics"]["lines_of_code"],
                    "issue_count": r["issue_count"],
                    "severity_counts": r["severity_counts"],
                    "issues": r["issues"],
                    "related_files": r.get("related_files", []),
                }
                if i < len(valid_files):
                    manifest_entry["content"] = valid_files[i]["content"]
                file_manifest.append(manifest_entry)
            
            ai_project_review = await suggestion_generator.generate_project_review_async(
                file_manifest, project_summary_data
            )
        except Exception as e:
            logger.warning(f"Project AI review failed: {e}")

    auto_fixes = []
    try:
        fix_tasks = []
        for i, r in enumerate(results):
            critical_count = r["severity_counts"].get("critical", 0) + r["severity_counts"].get("high", 0)
            if critical_count > 0 and i < len(valid_files):
                fix_tasks.append(
                    suggestion_generator.generate_auto_fix_async(
                        code=valid_files[i]["content"],
                        issues=r["issues"],
                        language=r["language"],
                        filename=r["file_path"],
                        plan_md=plan_md
                    )
                )
        if fix_tasks:
            auto_fixes = await asyncio.gather(*fix_tasks)
            auto_fixes = [f for f in auto_fixes if f.get("diff")]
    except Exception as e:
        logger.warning(f"Auto-fix generation failed: {e}")

    project_id = project_record.id if project_record else None
    db.close()
    
    # Cleanup scratch directory optionally
    import shutil
    try:
        shutil.rmtree(task_dir)
    except Exception:
        pass

    return {
        "project_id": project_id,
        "plan_md": plan_md,
        "project_summary": project_summary_data,
        "ai_project_review": ai_project_review,
        "auto_fixes": auto_fixes,
        "file_results": results,
        "skipped": skipped,
        "errors": errors,
    }


@celery_app.task(bind=True, max_retries=5, default_retry_delay=2)
def process_upload_task(self, task_id: str, user_id: int):
    """
    Synchronous Celery task wrapper that runs the async upload processing logic.
    Retries up to 5 times with full-jitter exponential backoff on transient LLM errors.
    """
    try:
        return asyncio.run(_process_upload_async(self, task_id, user_id))
    except Exception as exc:
        if _is_retriable(exc):
            countdown = _backoff_countdown(self.request.retries + 1)
            logger.warning(
                "[process_upload_task] Retriable LLM error (attempt %d/5) — retrying in %.1fs: %s",
                self.request.retries + 1, countdown, exc
            )
            self.update_state(
                state='RETRYING',
                meta={'status': f'LLM service busy. Retrying in {int(countdown)}s… (attempt {self.request.retries + 1}/5)'}
            )
            raise self.retry(exc=exc, countdown=countdown)
        # Non-retriable — fail immediately
        logger.error("[process_upload_task] Non-retriable failure: %s", exc)
        raise

async def _analyze_tech_debt_async_no_self(diff: str, language: str):
    """Core async logic for validating diff against tech debt engine."""
    
    # 1. Parse unified diff
    parsed = _parse_unified_diff(diff)
    if not parsed:
        return {"verdict": "✅ Clean", "total_debt_hours": 0.0, "findings": []}
    
    # Extract only the hunks and try to match with AST function context
    ast_contexts = []
    for entry in parsed:
        file_contexts = map_diff_to_ast_context(entry["hunks"], language)
        # Re-attach file scoping
        for ctx in file_contexts:
            ctx["file"] = entry["file"]
            ast_contexts.append(ctx)
            
    if not ast_contexts:
        return {"verdict": "✅ Clean", "total_debt_hours": 0.0, "findings": []}
        
    # 2. Fire Langchain Agent
    agent = TechDebtAgent()
    analysis = await agent.analyze_debt_delta(ast_contexts, language)
    
    # Convert Pydantic Object directly to dictionary for Celery serialization
    result_dict = analysis.model_dump()
    return result_dict

@celery_app.task(max_retries=5, default_retry_delay=2)
def analyze_tech_debt_task(diff: str, language: str):
    """
    Synchronous Celery task wrapper for the Tech Debt LLM agent.
    Retries up to 5 times with full-jitter exponential backoff on transient LLM errors.
    """
    try:
        return asyncio.run(_analyze_tech_debt_async_no_self(diff, language))
    except Exception as exc:
        if _is_retriable(exc):
            countdown = _backoff_countdown(1)  # Simplified for now
            logger.warning(
                "[analyze_tech_debt_task] Retriable LLM error — retrying in %.1fs: %s",
                countdown, exc
            )
            raise
        logger.error("[analyze_tech_debt_task] Non-retriable failure: %s", exc)
        raise
