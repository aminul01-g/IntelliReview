"""
IntelliReview MCP Server
========================
Exposes IntelliReview's code analysis engine as MCP tools for AI agents.

Usage:
    python api/mcp_server.py

Configuration (Claude Desktop / Cursor):
    Add to your MCP settings JSON:
    {
      "mcpServers": {
        "intellireview": {
          "command": "python",
          "args": ["<path-to>/intellireview/api/mcp_server.py"]
        }
      }
    }
"""

from mcp.server.fastmcp import FastMCP
import os
import sys
import json
from pathlib import Path

# Ensure the root project directory is in the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# ─── Resilient Imports ────────────────────────────────────────────
# Parsers may fail if optional native deps (esprima, etc.) are missing.
# We load what we can and skip the rest gracefully.

parsers = {}

try:
    from analyzer.parsers.python_parser import PythonParser
    parsers["python"] = PythonParser()
except ImportError:
    pass

try:
    from analyzer.parsers.javascript_parser import JavaScriptParser
    parsers["javascript"] = JavaScriptParser()
except ImportError:
    pass

try:
    from analyzer.parsers.java_parser import JavaParser
    parsers["java"] = JavaParser()
except ImportError:
    pass

try:
    from analyzer.parsers.cpp_parser import CppParser
    parsers["cpp"] = CppParser()
    parsers["c"] = CppParser()
except ImportError:
    pass

class _StubAnalyzer:
    """Fallback stub for analyzers with missing dependencies."""
    def analyze(self, *a, **kw): return {}
    def detect(self, *a, **kw): return []
    def scan(self, *a, **kw): return []

try:
    from analyzer.metrics.complexity import ComplexityAnalyzer
    complexity_analyzer = ComplexityAnalyzer()
except ImportError:
    complexity_analyzer = _StubAnalyzer()

try:
    from analyzer.metrics.duplication import DuplicationDetector
    duplication_detector = DuplicationDetector()
except ImportError:
    duplication_detector = _StubAnalyzer()

try:
    from analyzer.detectors.antipatterns import AntiPatternDetector
    antipattern_detector = AntiPatternDetector()
except ImportError:
    antipattern_detector = _StubAnalyzer()

try:
    from analyzer.detectors.security import SecurityScanner
    security_scanner = SecurityScanner()
except ImportError:
    security_scanner = _StubAnalyzer()

try:
    from analyzer.detectors.quality import QualityDetector
    quality_detector = QualityDetector()
except ImportError:
    quality_detector = _StubAnalyzer()

try:
    from ml_models.generators.suggestion_generator import SuggestionGenerator
    suggestion_generator = SuggestionGenerator(provider="huggingface")
except ImportError:
    suggestion_generator = None

# ─── MCP Server ──────────────────────────────────────────────────

mcp = FastMCP("IntelliReview")

# Extension → language mapping (mirrors the backend)
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


def _run_static_analysis(code: str, lang: str, filename: str) -> tuple:
    """Run the full static analysis stack. Returns (metrics, issues)."""
    parser = parsers.get(lang)
    ast = parser.parse(code, filename) if parser else {}

    metrics_data = complexity_analyzer.analyze(code, lang)
    duplicates = duplication_detector.detect(code)
    antipatterns = antipattern_detector.detect(code, ast, lang)
    security_issues = security_scanner.scan(code, filename, lang)
    quality_issues = quality_detector.detect(code, filename, lang)

    all_issues = antipatterns + security_issues + quality_issues
    for dup in duplicates:
        all_issues.append({
            "type": "code_duplication",
            "severity": "medium",
            "line": dup.get("block1_start", 0),
            "message": f"Duplicate code (similarity: {dup.get('similarity', '?')})",
            "suggestion": "Extract duplicated code into a reusable function"
        })

    return metrics_data, all_issues


# ─── Tool 1: Analyze a single code snippet ──────────────────────

@mcp.tool()
async def analyze_code(code: str, language: str, filename: str = "unknown") -> str:
    """Analyze a single source code snippet or file content.

    Runs static analysis (complexity, duplication, anti-patterns, security,
    quality) and generates an AI executive review.

    Args:
        code: The raw source code to analyze.
        language: Programming language (python, javascript, java, cpp, c).
        filename: Optional filename for context in security scanning.

    Returns:
        A Markdown report with metrics, issues, and an AI review.
    """
    lang = language.lower()
    supported = list(parsers.keys())

    if lang not in supported and lang not in EXT_LANG_MAP.values():
        return (f"Error: Language '{language}' is not supported. "
                f"Supported: {', '.join(sorted(set(supported)))}")

    try:
        metrics_data, all_issues = _run_static_analysis(code, lang, filename)

        # Build markdown response
        lines_of_code = metrics_data.get('lines_of_code', 0)
        complexity = metrics_data.get('average_complexity', 'N/A')
        maintainability = metrics_data.get('maintainability_index', 'N/A')

        report = f"# IntelliReview Analysis: `{filename}` ({language})\n\n"
        report += f"| Metric | Value |\n|---|---|\n"
        report += f"| Lines of Code | {lines_of_code} |\n"
        report += f"| Avg Complexity | {complexity} |\n"
        report += f"| Maintainability | {maintainability} |\n\n"

        # Severity summary
        sev_counts = {}
        for iss in all_issues:
            s = iss.get("severity", "info")
            sev_counts[s] = sev_counts.get(s, 0) + 1
        if sev_counts:
            report += "**Issue Breakdown:** "
            report += " | ".join(f"{s.upper()}: {c}" for s, c in sorted(sev_counts.items()))
            report += "\n\n"

        # Issue list
        report += f"## Issues ({len(all_issues)})\n"
        if not all_issues:
            report += "✅ No issues found!\n"
        else:
            for issue in all_issues[:20]:
                sev = issue.get('severity', 'info').upper()
                report += (f"- **L{issue.get('line', '?')}** [{sev}] "
                           f"`{issue.get('type', 'unknown')}`: "
                           f"{issue.get('message', '')}\n")
                if issue.get("suggestion"):
                    report += f"  - 💡 {issue['suggestion']}\n"
            if len(all_issues) > 20:
                report += f"\n*...and {len(all_issues) - 20} more issues.*\n"

        # AI executive review
        report += "\n## AI Executive Review\n"
        if suggestion_generator is None:
            report += "⚠️ AI review not available (SuggestionGenerator not loaded)\n"
        else:
            try:
                ai_summary = await suggestion_generator.generate_general_review_async(
                    code, all_issues, lang
                )
                report += ai_summary
            except Exception as ai_err:
                report += f"⚠️ AI review unavailable: {str(ai_err)}\n"

        return report

    except Exception as e:
        return f"Analysis failed: {str(e)}"


# ─── Tool 2: Analyze a project directory ────────────────────────

@mcp.tool()
async def analyze_project(directory: str) -> str:
    """Analyze an entire project directory for code quality.

    Recursively scans the directory for supported source files, runs static
    analysis on each, and generates a holistic AI architectural review.

    Args:
        directory: Absolute or relative path to the project directory.

    Returns:
        A Markdown project audit report with per-file summaries and an
        overall architectural review.
    """
    dir_path = Path(directory).resolve()
    if not dir_path.is_dir():
        return f"Error: '{directory}' is not a valid directory."

    # Collect files
    file_manifest = []
    skipped = []

    for fpath in sorted(dir_path.rglob("*")):
        if not fpath.is_file():
            continue
        rel = str(fpath.relative_to(dir_path))
        parts = rel.replace("\\", "/").split("/")
        if any(p in SKIP_PATTERNS for p in parts):
            continue

        ext = fpath.suffix.lower()
        lang = EXT_LANG_MAP.get(ext)
        if not lang:
            continue
        if lang not in parsers:
            skipped.append(f"{rel} (no parser for {lang})")
            continue

        try:
            content = fpath.read_text(encoding="utf-8", errors="replace")
        except Exception:
            skipped.append(f"{rel} (unreadable)")
            continue

        line_count = len(content.split("\n"))
        if line_count == 0 or line_count > 10000:
            skipped.append(f"{rel} ({'empty' if line_count == 0 else 'too large'})")
            continue

        file_manifest.append({
            "file_path": rel,
            "language": lang,
            "content": content,
            "lines": line_count,
        })

    if not file_manifest:
        return (f"No supported source files found in `{directory}`.\n"
                f"Supported extensions: {', '.join(sorted(EXT_LANG_MAP.keys()))}\n"
                f"Skipped: {len(skipped)} files")

    # Analyze each file (cap at 30)
    results = []
    total_issues = 0
    total_lines = 0

    for entry in file_manifest[:30]:
        try:
            metrics_data, issues = _run_static_analysis(
                entry["content"], entry["language"], entry["file_path"]
            )
            sev_counts = {}
            for iss in issues:
                s = iss.get("severity", "info")
                sev_counts[s] = sev_counts.get(s, 0) + 1

            loc = metrics_data.get("lines_of_code", entry["lines"])
            total_lines += loc
            total_issues += len(issues)

            results.append({
                "file_path": entry["file_path"],
                "language": entry["language"],
                "lines": loc,
                "issue_count": len(issues),
                "severity_counts": sev_counts,
                "issues": issues[:5],
                "content": entry["content"],
            })
        except Exception as e:
            skipped.append(f"{entry['file_path']} (error: {e})")

    # Build project summary
    critical_high = sum(
        r["severity_counts"].get("critical", 0) + r["severity_counts"].get("high", 0)
        for r in results
    )
    health_score = max(0, min(100, 100 - (critical_high / max(total_lines, 1)) * 1000))

    lang_breakdown = {}
    for r in results:
        lang_breakdown[r["language"]] = lang_breakdown.get(r["language"], 0) + 1

    # Build report header
    report = f"# IntelliReview Project Audit: `{dir_path.name}`\n\n"
    report += f"| Metric | Value |\n|---|---|\n"
    report += f"| Files Analyzed | {len(results)} |\n"
    report += f"| Total Lines | {total_lines:,} |\n"
    report += f"| Total Issues | {total_issues} |\n"
    report += f"| Health Score | {round(health_score, 1)}% |\n"
    report += f"| Languages | {', '.join(f'{k} ({v})' for k, v in lang_breakdown.items())} |\n\n"

    # Per-file table
    report += "## File Results\n\n"
    report += "| File | Lang | Lines | Issues | Top Severity |\n"
    report += "|------|------|-------|--------|-------------|\n"
    for r in results:
        top_sev = max(r["severity_counts"], key=lambda s: {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}.get(s, 0)) if r["severity_counts"] else "—"
        report += f"| `{r['file_path']}` | {r['language']} | {r['lines']} | {r['issue_count']} | {top_sev} |\n"
    report += "\n"

    if skipped:
        report += f"*Skipped {len(skipped)} files:* {', '.join(skipped[:10])}\n\n"

    # AI Architectural Review
    report += "## AI Architectural Review\n"
    if suggestion_generator is None:
        report += "⚠️ AI review not available (SuggestionGenerator not loaded)\n"
    else:
        try:
            project_summary = {
                "total_files": len(results),
                "total_lines": total_lines,
                "total_issues": total_issues,
                "health_score": round(health_score, 1),
                "language_breakdown": lang_breakdown,
            }
            ai_review = await suggestion_generator.generate_project_review_async(
                results, project_summary
            )
            report += ai_review
        except Exception as ai_err:
            report += f"⚠️ AI review unavailable: {str(ai_err)}\n"

    return report


# ─── Entry point ─────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
