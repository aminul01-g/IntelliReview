from fastapi import APIRouter, Request, Header, HTTPException, status, BackgroundTasks
import hmac
import hashlib
import os
import requests
from typing import Optional
from github import Github
import asyncio
from dotenv import load_dotenv

# Load environment variables so background tasks have API keys
load_dotenv()

# Ensure IntelliReview imports
from api.routes.analysis import EXT_LANG_MAP, SKIP_PATTERNS
from analyzer.parsers.python_parser import PythonParser
from analyzer.parsers.javascript_parser import JavaScriptParser
from analyzer.parsers.java_parser import JavaParser
from analyzer.parsers.cpp_parser import CppParser
from analyzer.metrics.complexity import ComplexityAnalyzer
from analyzer.metrics.duplication import DuplicationDetector
from analyzer.detectors.antipatterns import AntiPatternDetector
from analyzer.detectors.security import SecurityScanner
from analyzer.detectors.quality import QualityDetector
from ml_models.agents.orchestrator import PRReviewOrchestrator
from analyzer.context.project_context import ProjectContextBuilder
from analyzer.utils.redactor import SecretRedactor
from api.schemas.feedback_schemas import SEVERITY_MARKERS

router = APIRouter()

GITHUB_WEBHOOK_SECRET = os.getenv("GITHUB_WEBHOOK_SECRET")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

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
orchestrator = PRReviewOrchestrator()
project_context_builder = ProjectContextBuilder()


async def analyze_pr_async(repo_full_name: str, pr_number: int):
    """Background task to pull PR changes, analyze, and post a review."""
    if not GITHUB_TOKEN:
        print("GITHUB_TOKEN is not set. Cannot post PR review.")
        return
        
    try:
        g = Github(GITHUB_TOKEN)
        repo = g.get_repo(repo_full_name)
        pr = repo.get_pull(pr_number)
        files = pr.get_files()
        commits = pr.get_commits()
        latest_commit = commits.reversed[0] if commits.totalCount > 0 else None
        
        results = []
        file_manifest = []
        valid_files = []
        total_lines = 0
        total_issues = 0
        
        # 1. Gather all valid PR files
        for f in files:
            # Skip deletions
            if f.status == "removed":
                continue
                
            filename = f.filename
            
            # Use SKIP_PATTERNS properly
            path_parts = filename.replace("\\", "/").split("/")
            if any(part in SKIP_PATTERNS for part in path_parts):
                continue
                
            ext = os.path.splitext(filename)[1].lower()
            lang = EXT_LANG_MAP.get(ext)
            if not lang:
                continue
                
            # Download file content
            if not f.raw_url:
                continue
            resp = requests.get(f.raw_url)
            if resp.status_code != 200:
                continue
                
            code = resp.text
            line_count = len(code.split('\n'))
            if line_count == 0 or line_count > 5000:
                continue
                
            valid_files.append({
                "filename": filename,
                "content": code,
                "language": lang,
                "lines": line_count
            })
            
        # 2. Build RAG Project Context
        if valid_files:
            try:
                project_context_builder.index_project(valid_files)
            except Exception as e:
                print(f"RAG Indexing failed in PR webhook: {e}")
                
        # 3. Analyze each file
        for file_idx, f_data in enumerate(valid_files):
            filename = f_data["filename"]
            code = f_data["content"]
            lang = f_data["language"]
            line_count = f_data["lines"]
            
            parser = parsers.get(lang)
            if not parser:
                continue
                
            try:
                ast = parser.parse(code, filename)
                metrics_data = complexity_analyzer.analyze(code, lang)
                duplicates = duplication_detector.detect(code)
                antipatterns = antipattern_detector.detect(code, ast, lang)
                security_issues = security_scanner.scan(code, filename, lang)
                quality_issues = quality_detector.detect(code, filename, lang)
                
                all_issues = antipatterns + security_issues + quality_issues
                
                severity_counts = {}
                for issue in all_issues:
                    sev = issue.get("severity", "info")
                    severity_counts[sev] = severity_counts.get(sev, 0) + 1
                    
                issues_count = len(all_issues)
                total_issues += issues_count
                total_lines += metrics_data.get("lines_of_code", line_count)
                
                if issues_count > 0:
                    related_files = []
                    try:
                        related_files = [r["filename"] for r in project_context_builder.get_related_files(file_idx, top_k=3)]
                    except Exception:
                        pass
                        
                    results.append({
                        "file_path": filename,
                        "language": lang,
                        "metrics": metrics_data,
                        "issue_count": issues_count,
                        "severity_counts": severity_counts,
                        "issues": all_issues,
                        "related_files": related_files
                    })
                    
                    manifest_entry = {
                        "file_path": filename,
                        "language": lang,
                        "lines": metrics_data.get("lines_of_code", line_count),
                        "issue_count": issues_count,
                        "severity_counts": severity_counts,
                        "issues": all_issues,
                        "related_files": related_files,
                        "content": code[:800] # for the AI
                    }
                    file_manifest.append(manifest_entry)
            except Exception as ex:
                print(f"Error analyzing file {filename} in PR: {ex}")
                
        # Generate PR Final AI Review and Inline Comments via Orchestrator
        if not results:
            comment_body = "🚀 **IntelliReview PR Audit**\n\n✅ Checked changed files. No critical issues detected."
            pr.create_issue_comment(comment_body)
            return

        # ─── FeedbackGenerator Integration ─────────────────────────────
        # Use the structured FeedbackGenerator pipeline instead of manual
        # string concatenation for world-class PR comments.
        from analyzer.feedback.feedback_generator import FeedbackGenerator
        from analyzer.feedback.verification import VerificationWalkthroughGenerator
        from analyzer.feedback.pr_gate import PRGate

        feedback_gen = FeedbackGenerator(project_root=None)

        # Aggregate all issues across files for the review
        all_pr_issues = []
        for r in results:
            for issue in r["issues"]:
                issue["file_path"] = r["file_path"]
            all_pr_issues.extend(r["issues"])

        # Build the full code context from all reviewed files
        combined_code = "\n\n".join(
            f"# --- {vf['filename']} ---\n{vf['content']}"
            for vf in valid_files
            if any(r["file_path"] == vf["filename"] for r in results)
        )

        # Generate structured review
        pr_review = feedback_gen.generate_review(
            raw_findings=all_pr_issues,
            code=combined_code,
            language="multi",
            repository=repo_full_name,
            pr_number=pr_number,
            files_reviewed=len(results),
        )

        # Render to Markdown
        comment_body = feedback_gen.render_markdown(pr_review)

        # ─── PR Gate Evaluation ───
        total_lines = sum(len(vf["content"].split("\n")) for vf in valid_files)
        pr_gate = PRGate()
        verdict = pr_gate.evaluate(pr_review, total_lines)

        # Update commit status via GitHub API
        if latest_commit:
            try:
                commit_obj = repo.get_commit(latest_commit)
                state = "success" if verdict.verdict == "pass" else ("pending" if verdict.verdict == "warn" else "failure")
                description = f"IntelliReview: {verdict.verdict.upper()} - Score: {verdict.health_score}%"
                commit_obj.create_status(
                    state=state,
                    description=description[:140],
                    context="IntelliReview Gate"
                )

                # Prepend gate verdict to comment
                gate_header = f"## 🚦 PR Quality Gate: **{verdict.verdict.upper()}**\n"
                gate_header += f"- **Health Score**: {verdict.health_score}%\n"
                gate_header += f"- **Technical Debt**: {verdict.technical_debt_hours}h\n"
                if verdict.block_reasons:
                    gate_header += "\n**Block Reasons:**\n" + "\n".join(f"- 🔴 {r}" for r in verdict.block_reasons) + "\n"
                if verdict.recommendations:
                    gate_header += "\n**Recommendations:**\n" + "\n".join(f"- 🟡 {r}" for r in verdict.recommendations) + "\n"
                gate_header += "\n---\n\n"
                
                comment_body = gate_header + comment_body
            except Exception as e:
                print(f"Failed to post commit status: {e}")

        # Post inline comments for important findings with diffs
        for finding in pr_review.important_findings:
            if finding.line > 0 and finding.autofix and latest_commit:
                try:
                    suggestion_block = f"```suggestion\n{finding.autofix.after}\n```"
                    inline_body = (
                        f"{SEVERITY_MARKERS.get(finding.severity, '⚪')} **{finding.title}**\n\n"
                        f"{finding.narrative}\n\n{suggestion_block}"
                    )
                    pr.create_review_comment(
                        body=inline_body,
                        commit_id=latest_commit,
                        path=finding.file_path,
                        line=finding.line,
                        side="RIGHT"
                    )
                except Exception as e:
                    print(f"Failed to post inline comment for {finding.file_path}:{finding.line}: {e}")

        # Generate and log the verification walkthrough
        wt_gen = VerificationWalkthroughGenerator()
        if pr_review.verification_walkthrough:
            walkthrough_md = wt_gen.render_artifact_markdown(pr_review.verification_walkthrough)
            print(f"Verification Walkthrough:\n{walkthrough_md}")

        pr.create_issue_comment(comment_body)
        print(f"Successfully posted PR review to {repo_full_name}#{pr_number}")
        
    except Exception as e:
        print(f"Failed to process PR: {str(e)}")


@router.post("/github")
async def github_webhook(
    request: Request,
    background_tasks: BackgroundTasks,
    x_hub_signature_256: Optional[str] = Header(None)
):
    """Handle GitHub PR webhooks."""
    payload = await request.body()
    
    # Verify signature if secret is set
    if GITHUB_WEBHOOK_SECRET:
        if not x_hub_signature_256:
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Signature missing")
        
        hash_object = hmac.new(
            GITHUB_WEBHOOK_SECRET.encode(),
            msg=payload,
            digestmod=hashlib.sha256
        )
        expected_signature = "sha256=" + hash_object.hexdigest()
        
        if not hmac.compare_digest(expected_signature, x_hub_signature_256):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Invalid signature")

    data = await request.json()
    event = request.headers.get("X-GitHub-Event")
    
    if event == "pull_request":
        action = data.get("action")
        if action in ["opened", "synchronize"]:
            pull_request = data.get("pull_request")
            repo = data.get("repository")
            pr_number = pull_request.get("number")
            repo_name = repo.get("full_name")
            
            print(f"Received PR {action} event for {repo_name} PR #{pr_number}")
            
            # Dispatch analysis to background so webhook returns 200 OK immediately
            background_tasks.add_task(analyze_pr_async, repo_name, pr_number)
            
            return {
                "message": "PR analysis dispatched",
                "pr": pr_number,
                "repo": repo_name
            }
            
    return {"message": "Event ignored"}
