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
from dotenv import load_dotenv

# Ensure the root project directory is in the path
project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, project_root)

# Load environment variables
load_dotenv(os.path.join(project_root, ".env"))
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
    from analyzer.detectors.ai_patterns import AIPatternDetector
    ai_pattern_detector = AIPatternDetector()
except ImportError:
    ai_pattern_detector = _StubAnalyzer()

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
    
    # AI-generated code pattern detection
    ai_patterns = ai_pattern_detector.detect(code, filename, lang)
    all_issues.extend(ai_patterns)
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


# ─── Tool 3: Search Symbol (AST) ────────────────────────────────

@mcp.tool()
async def search_symbol(symbol_name: str, directory: str) -> str:
    """Search for a symbol's definition across the parsed AST of the project.
    
    Args:
        symbol_name: The name of the class or function to find.
        directory: The project directory to scan.
    """
    dir_path = Path(directory).resolve()
    if not dir_path.is_dir():
        return f"Error: '{directory}' is not a valid directory."
        
    found = []
    
    for fpath in sorted(dir_path.rglob("*")):
        if not fpath.is_file():
            continue
            
        ext = fpath.suffix.lower()
        lang = EXT_LANG_MAP.get(ext)
        if not lang or lang not in parsers:
            continue
            
        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
            parser = parsers[lang]
            ast = parser.parse(content, str(fpath))
            
            # Simple recursive search
            def search_node(node):
                if node.name == symbol_name:
                    found.append(f"Found '{symbol_name}' in {fpath.name} (L{node.line_start}-L{node.line_end}) as {node.type}")
                for child in node.children:
                    search_node(child)
            
            search_node(ast)
        except Exception:
            pass
            
    if not found:
        return f"Symbol '{symbol_name}' not found."
    return "\n".join(found)

# ─── Tool 4: Call Graph Analysis (AST) ──────────────────────────

@mcp.tool()
async def analyze_call_graph(file_path: str) -> str:
    """Analyze the AST to extract a primitive call graph for a file.
    
    Args:
        file_path: The absolute path to the file.
    """
    fpath = Path(file_path).resolve()
    if not fpath.is_file():
        return f"Error: '{file_path}' is not a valid file."
        
    ext = fpath.suffix.lower()
    lang = EXT_LANG_MAP.get(ext)
    
    if not lang or lang not in parsers:
        return f"Error: No AST parser for {ext}"
        
    try:
        content = fpath.read_text(encoding="utf-8", errors="ignore")
        parser = parsers[lang]
        ast = parser.parse(content, str(fpath))
        
        edges = []
        
        def traverse(node, current_func=None):
            # If we enter a function definition, update current context
            ctx = current_func
            if node.type in ["FunctionDef", "MethodDef", "FunctionDeclaration"]:
                ctx = node.name
                
            # If it's a function call, record the edge
            if "Call" in node.type or "Invocation" in node.type:
                edges.append((ctx or "global", node.name))
                
            for child in node.children:
                traverse(child, ctx)
                
        traverse(ast)
        
        if not edges:
            return f"No function calls detected in {fpath.name}."
            
        report = f"## Call Graph for {fpath.name}\n"
        for caller, callee in edges:
            report += f"- `{caller}` -> `{callee}`\n"
            
        return report
    except Exception as e:
        return f"Failed to build call graph: {e}"


# ─── Tool 5: Dataflow Tracking ──────────────────────────────────

# Sensitive sinks for dataflow analysis
_SENSITIVE_SINKS = {
    "execute", "raw", "query", "eval", "exec", "system", "popen",
    "subprocess", "os.system", "cursor.execute", "db.execute",
    "authenticate", "verify_password", "check_password",
    "open", "write", "unlink", "remove", "rmdir",
    "innerHTML", "document.write", "dangerouslySetInnerHTML",
}

# Untrusted input source patterns
_SOURCE_PATTERNS = [
    r'request\.(args|form|params|json|query|body|data)\[',
    r'request\.get\(', r'params\[', r'query\[',
    r'input\(', r'stdin', r'req\.(body|params|query)',
    r'document\.(getElementById|querySelector)',
    r'window\.location', r'argv\[',
]

@mcp.tool()
async def track_dataflow(file_path: str, source_expression: str = "") -> str:
    """Track dataflow from untrusted input sources to sensitive sinks.

    Scans a file's AST and source code to identify if untrusted client input
    (e.g., request params, user input) flows into sensitive operations
    (e.g., DB queries, eval, auth logic, file I/O) without sanitization.

    Args:
        file_path: Absolute path to the source file to analyze.
        source_expression: Optional specific expression to trace (e.g., 'request.args["user_id"]').

    Returns:
        A Markdown report of identified dataflow paths with taint status.
    """
    import re

    fpath = Path(file_path).resolve()
    if not fpath.is_file():
        return f"Error: '{file_path}' is not a valid file."

    ext = fpath.suffix.lower()
    lang = EXT_LANG_MAP.get(ext)
    if not lang:
        return f"Error: Unsupported file extension '{ext}'."

    try:
        content = fpath.read_text(encoding="utf-8", errors="ignore")
    except Exception as e:
        return f"Error reading file: {e}"

    lines = content.split("\n")
    traces = []

    # Phase 1: Find all source locations (user input entry points)
    sources = []
    for i, line in enumerate(lines, 1):
        for pattern in _SOURCE_PATTERNS:
            match = re.search(pattern, line)
            if match:
                sources.append({
                    "line": i,
                    "expression": line.strip(),
                    "pattern": pattern,
                })
                break

    if source_expression:
        # Filter to only the specified expression
        sources = [s for s in sources if source_expression in s["expression"]] or sources

    # Phase 2: Find all sink locations (sensitive operations)
    sinks = []
    for i, line in enumerate(lines, 1):
        for sink in _SENSITIVE_SINKS:
            if sink in line:
                sinks.append({
                    "line": i,
                    "expression": line.strip(),
                    "sink_type": sink,
                })
                break

    # Phase 3: Trace paths — check if any source variable name appears near a sink
    for source in sources:
        # Extract variable names from the source line
        src_vars = set(re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', source["expression"]))
        src_vars -= {"request", "args", "form", "params", "json", "query", "body",
                      "data", "get", "input", "req", "document", "window"}

        for sink in sinks:
            sink_vars = set(re.findall(r'\b([a-zA-Z_][a-zA-Z0-9_]*)\b', sink["expression"]))
            shared = src_vars & sink_vars

            if shared or (source["line"] < sink["line"] and sink["line"] - source["line"] < 50):
                # Check for sanitization between source and sink
                sanitized = False
                for j in range(source["line"], min(sink["line"], len(lines))):
                    sanitize_line = lines[j - 1].lower()
                    if any(kw in sanitize_line for kw in [
                        "sanitize", "escape", "parameterize", "validate",
                        "clean", "strip", "encode", "dompurify", "bleach"
                    ]):
                        sanitized = True
                        break

                taint_status = "✅ Sanitized" if sanitized else "⚠️ UNSANITIZED"
                traces.append({
                    "source": source,
                    "sink": sink,
                    "shared_vars": list(shared),
                    "sanitized": sanitized,
                    "taint_status": taint_status,
                })

    # Build report
    report = f"## Dataflow Analysis: `{fpath.name}`\n\n"
    report += f"| Metric | Count |\n|--------|-------|\n"
    report += f"| Sources (untrusted input) | {len(sources)} |\n"
    report += f"| Sinks (sensitive ops) | {len(sinks)} |\n"
    report += f"| Traced paths | {len(traces)} |\n\n"

    if not traces:
        report += "✅ No untrusted data flows to sensitive sinks detected.\n"
        return report

    report += "### Dataflow Traces\n\n"
    for i, trace in enumerate(traces, 1):
        report += f"#### Trace {i}: {trace['taint_status']}\n"
        report += f"- **Source** (L{trace['source']['line']}): `{trace['source']['expression']}`\n"
        report += f"- **Sink** (L{trace['sink']['line']}): `{trace['sink']['expression']}`\n"
        if trace["shared_vars"]:
            report += f"- **Shared variables:** `{', '.join(trace['shared_vars'])}`\n"
        if not trace["sanitized"]:
            report += f"- 🔴 **Action Required:** Untrusted input reaches `{trace['sink']['sink_type']}` without sanitization\n"
        report += "\n"

    return report


# ─── Tool 6: Get Callers (Reverse Call Graph) ──────────────────────

@mcp.tool()
async def get_callers(directory: str, function_name: str) -> str:
    """Find all call-sites for a given function across the project directory.

    Essential for reachability analysis — answers "who calls this vulnerable function?".

    Args:
        directory: Project directory path to scan.
        function_name: The name of the function to find callers for.

    Returns:
        A Markdown report of all files and lines where the function is called.
    """
    dir_path = Path(directory).resolve()
    if not dir_path.is_dir():
        return f"Error: '{directory}' is not a valid directory."

    callers = []
    
    # Simple regex fall-back for cross-language support
    import re
    # Match function calls like: function_name(
    # Also handles obj.function_name(
    call_pattern = re.compile(rf'\b{function_name}\s*\(')

    for fpath in sorted(dir_path.rglob("*")):
        if not fpath.is_file():
            continue
        rel = str(fpath.relative_to(dir_path))
        parts = rel.replace("\\", "/").split("/")
        if any(p in SKIP_PATTERNS for p in parts):
            continue

        ext = fpath.suffix.lower()
        if not EXT_LANG_MAP.get(ext):
            continue

        try:
            content = fpath.read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")
            
            # Simple context tracking for identifying the calling function
            current_func = "global"
            func_def_pattern = re.compile(r'^\s*(?:async\s+)?def\s+([a-zA-Z0-9_]+)\s*\(')
            
            for i, line in enumerate(lines, 1):
                func_match = func_def_pattern.match(line)
                if func_match:
                    current_func = func_match.group(1)
                    
                if call_pattern.search(line):
                    callers.append({
                        "file": rel,
                        "line": i,
                        "calling_context": current_func,
                        "code": line.strip()
                    })
        except Exception:
            pass

    if not callers:
        return f"No callers found for `{function_name}`."

    report = f"## Callers of `{function_name}`\n\n"
    for c in callers:
        report += f"- **{c['file']}:L{c['line']}** (in `{c['calling_context']}`): `{c['code']}`\n"
        
    return report

# ─── Tool 7: Semantic Reachability Analysis ────────────────────────

import re

# Entry point patterns that indicate reachable paths from the outside world
_ENTRY_POINT_PATTERNS = [
    re.compile(r'@(?:app|router|bp)\.(?:get|post|put|delete|patch)'),
    re.compile(r'def\s+main\s*\('),
    re.compile(r'if\s+__name__\s*==\s*[\'"]__main__[\'"]'),
    re.compile(r'@celery\.task'),
    re.compile(r'@.*(?:job|listener|handler)')
]

@mcp.tool()
async def check_reachability(directory: str, sink_function: str, max_depth: int = 5) -> str:
    """Perform Semantic Reachability Analysis on a sensitive sink.
    
    Traces backwards from the sink function using get_callers to see if an
    untrusted entry point (HTTP handler, CLI, event listener) can reach it.

    Args:
        directory: Project directory to analyze.
        sink_function: The vulnerable function (e.g., 'cursor.execute').
        max_depth: Maximum call-graph depth to traverse backwards.

    Returns:
        Reachability verdict and the traced paths.
    """
    dir_path = Path(directory).resolve()
    if not dir_path.is_dir():
        return f"Error: '{directory}' is not a valid directory."

    visited = set()
    found_paths = []
    
    # Extract just the function name if it's a method call (e.g., "cursor.execute" -> "execute")
    base_func = sink_function.split('.')[-1]

    async def trace_back(func_name: str, path: list, depth: int):
        if depth >= max_depth:
            return
            
        if func_name in visited:
            return
        visited.add(func_name)
        
        # Check if this function itself is an entry point by scanning the file it's in
        # (This is a simplified heuristic: we rely on looking at callers)
        
        report = await get_callers(directory, func_name)
        if "No callers found" in report:
            return
            
        # Parse callers from report
        # Format: - **file:L1** (in `ctx`): `code`
        import re
        lines = report.split("\n")
        
        caller_regex = re.compile(r'-\s+\*\*([^:]+):L(\d+)\*\*\s+\(in\s+`([^`]+)`\):\s+`(.*)`')
        
        for line in lines:
            match = caller_regex.search(line)
            if match:
                file_rel = match.group(1)
                line_idx = match.group(2)
                ctx = match.group(3)
                code = match.group(4)
                
                new_path = path + [f"{ctx} ({file_rel}:L{line_idx})"]
                
                # Check if the file/line has an entry point decorator
                is_entry = False
                if ctx == "global" and "main" not in func_name.lower():
                    # Global calls are often module-level execution (reachable if imported/run)
                    if code.startswith('if __name__'):
                        is_entry = True
                        
                for p in _ENTRY_POINT_PATTERNS:
                    if p.search(code):
                        is_entry = True
                        break
                        
                # Also check if the context name implies it's an entry point
                if any(x in ctx.lower() for x in ['cli', 'main', 'handler', 'controller', 'route', 'task']):
                    is_entry = True
                    
                if is_entry:
                    found_paths.append(new_path)
                elif ctx != "global":
                    # Recurse up the call graph
                    await trace_back(ctx, new_path, depth + 1)
                    
    # Start trace
    await trace_back(base_func, [f"{base_func} (sink)"], 0)
    
    if found_paths:
        report = f"## 🔴 Reachability Verdict: **REACHABLE**\n\n"
        report += f"Found {len(found_paths)} path(s) from an external entry point to `{sink_function}`:\n\n"
        for i, path in enumerate(found_paths, 1):
            report += f"### Path {i}\n"
            # Reverse path so it flows from Trigger -> Sink
            path_rev = path[::-1]
            for step in path_rev:
                report += f"⬇️ `{step}`\n"
    else:
        report = f"## 🟢 Reachability Verdict: **UNREACHABLE**\n\n"
        report += f"No path found from an external entry point to `{sink_function}` within depth {max_depth}.\n"
        report += "This vulnerability is likely theoretical, dead code, or only reachable internally."
        
    return report

# ─── Entry point ─────────────────────────────────────────────────

if __name__ == "__main__":
    mcp.run()
