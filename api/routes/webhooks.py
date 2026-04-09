from fastapi import APIRouter, Request, Header, HTTPException, status, BackgroundTasks
import hmac
import hashlib
import os
import requests
from typing import Optional
from github import Github
import asyncio

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
from ml_models.generators.suggestion_generator import SuggestionGenerator

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
suggestion_generator = SuggestionGenerator(provider="huggingface")


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
        
        results = []
        file_manifest = []
        total_lines = 0
        total_issues = 0
        
        # Analyze changed files
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
                    results.append({
                        "file_path": filename,
                        "language": lang,
                        "metrics": metrics_data,
                        "issue_count": issues_count,
                        "severity_counts": severity_counts,
                        "issues": all_issues
                    })
                    
                    manifest_entry = {
                        "file_path": filename,
                        "language": lang,
                        "lines": metrics_data.get("lines_of_code", line_count),
                        "issue_count": issues_count,
                        "severity_counts": severity_counts,
                        "issues": all_issues,
                        "content": code[:800] # for the AI
                    }
                    file_manifest.append(manifest_entry)
            except Exception as ex:
                print(f"Error analyzing file {filename} in PR: {ex}")
                
        # Generate PR Comment Body
        if not results:
            comment_body = "🚀 **IntelliReview PR Audit**\n\n✅ Checked changed files. No critical issues detected."
            pr.create_issue_comment(comment_body)
            return

        critical_high = sum(
            r["severity_counts"].get("critical", 0) + r["severity_counts"].get("high", 0)
            for r in results
        )
        health_score = max(0, min(100, 100 - (critical_high / max(total_lines, 1)) * 1000))
        
        project_summary_data = {
            "total_files": len(results),
            "total_lines": total_lines,
            "total_issues": total_issues,
            "health_score": round(health_score, 1),
            "language_breakdown": {}
        }
        
        # Get AI Project-Level architectural review
        ai_review = await suggestion_generator.generate_project_review_async(file_manifest, project_summary_data)
        
        comment_body = f"🚀 **IntelliReview PR Audit**\n\n"
        comment_body += f"> Analyzed {len(results)} files. Overall Health Delta: **{round(health_score,1)}%**\n\n"
        
        comment_body += "<details open>\n<summary><b>🤖 AI Architectural Review</b></summary>\n\n"
        comment_body += f"{ai_review}\n\n</details>\n\n"
        
        comment_body += "<details>\n<summary><b>📄 Specific Issues</b></summary>\n\n"
        for r in results:
            if r["issue_count"] > 0:
                comment_body += f"### `{r['file_path']}`\n"
                for iss in r['issues'][:5]:
                    comment_body += f"- **L{iss.get('line', '?')}** [{iss.get('severity', 'info').upper()}]: {iss.get('message', '')}  \n"
                if r["issue_count"] > 5:
                    comment_body += f"  - *...and {r['issue_count'] - 5} more issues.*\n"
                comment_body += "\n"
        comment_body += "</details>\n"
        
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
