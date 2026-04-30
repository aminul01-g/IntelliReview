"""
AST Diff Mapper
================
Maps raw git diff hunks to the logical function/class boundaries that were
modified.  This is IntelliReview's core contribution — it ensures the LLM
only receives the precise scope of the change instead of the whole file.

Supports:
    - Python: Full AST via ``ast.parse`` (ClassDef, FunctionDef, AsyncFunctionDef,
      nested scopes, decorators).
    - JavaScript: Regex-based extraction of ``function``, arrow functions, class
      methods, and ``class`` declarations.
    - Java / C / C++: Regex-based extraction of methods and classes.

Each extracted context carries metadata:
    - ``scope_path``: Fully-qualified scope, e.g. ``MyClass.my_method``
    - ``scope_type``: ``FunctionDef | AsyncFunctionDef | ClassDef | Statements | raw_block``
    - ``confidence``: ``1.0`` for AST-verified, ``0.7`` for regex-matched, ``0.3`` for raw block
    - ``extraction_method``: ``ast | regex | fallback``
"""

import ast
import re
from typing import List, Dict, Optional
import logging

logger = logging.getLogger(__name__)


# ── Python AST Extraction ───────────────────────────────────────────────

def _extract_python_scopes(code_snippet: str) -> List[Dict]:
    """
    Parse a Python code snippet using ``ast`` and extract every function and
    class scope with fully-qualified scope paths (e.g. ``MyClass.my_method``).

    Falls back to a dummy-wrapper trick when the snippet is an incomplete
    fragment (common for diff hunks).
    """
    tree = None
    wrapper_offset = 0

    try:
        tree = ast.parse(code_snippet)
    except SyntaxError:
        try:
            wrapped = "def __dummy_wrapper__():\n" + "\n".join(
                f"    {line}" for line in code_snippet.split("\n")
            )
            tree = ast.parse(wrapped)
            wrapper_offset = 1  # lines shifted by 1 due to wrapper
        except SyntaxError:
            return []

    scopes: List[Dict] = []
    lines = code_snippet.split("\n")

    class ScopeExtractor(ast.NodeVisitor):
        """Walk the AST, tracking parent class to build scope paths."""

        def __init__(self):
            self._class_stack: List[str] = []

        # ── ClassDef ──
        def visit_ClassDef(self, node: ast.ClassDef):
            if node.name == "__dummy_wrapper__":
                self.generic_visit(node)
                return

            start = max(1, getattr(node, "lineno", 1) - wrapper_offset)
            end = max(start, getattr(node, "end_lineno", start) - wrapper_offset)
            body = "\n".join(lines[max(0, start - 1): min(end, len(lines))])

            scope_path = ".".join(self._class_stack + [node.name])
            scopes.append({
                "name": node.name,
                "scope_path": scope_path,
                "scope_type": "ClassDef",
                "body": body,
                "start_line": start,
                "end_line": end,
                "confidence": 1.0,
                "extraction_method": "ast",
            })

            self._class_stack.append(node.name)
            self.generic_visit(node)
            self._class_stack.pop()

        # ── FunctionDef / AsyncFunctionDef ──
        def _visit_func(self, node, scope_type: str):
            if node.name == "__dummy_wrapper__":
                self.generic_visit(node)
                return

            start = max(1, getattr(node, "lineno", 1) - wrapper_offset)
            end = max(start, getattr(node, "end_lineno", start) - wrapper_offset)
            body = "\n".join(lines[max(0, start - 1): min(end, len(lines))])

            scope_path = ".".join(self._class_stack + [node.name])
            scopes.append({
                "name": node.name,
                "scope_path": scope_path,
                "scope_type": scope_type,
                "body": body,
                "start_line": start,
                "end_line": end,
                "confidence": 1.0,
                "extraction_method": "ast",
            })

            # Track nested functions (push current name as parent scope)
            self._class_stack.append(node.name)
            self.generic_visit(node)
            self._class_stack.pop()

        def visit_FunctionDef(self, node):
            self._visit_func(node, "FunctionDef")

        def visit_AsyncFunctionDef(self, node):
            self._visit_func(node, "AsyncFunctionDef")

    extractor = ScopeExtractor()
    extractor.visit(tree)
    return scopes


# ── JavaScript Regex Extraction ─────────────────────────────────────────

# Matches:  function myFunc(...)  |  async function myFunc(...)
_JS_FUNC_RE = re.compile(
    r"(?:export\s+)?(?:async\s+)?function\s+(\w+)\s*\(", re.MULTILINE
)
# Matches:  class MyClass  |  export class MyClass extends Base
_JS_CLASS_RE = re.compile(
    r"(?:export\s+)?class\s+(\w+)", re.MULTILINE
)
# Matches:  methodName(...) {  (inside a class body — heuristic)
_JS_METHOD_RE = re.compile(
    r"^\s+(?:async\s+)?(\w+)\s*\([^)]*\)\s*\{", re.MULTILINE
)
# Matches:  const myFunc = (...) =>  |  const myFunc = async (...) =>
_JS_ARROW_RE = re.compile(
    r"(?:const|let|var)\s+(\w+)\s*=\s*(?:async\s+)?\(?[^)]*\)?\s*=>", re.MULTILINE
)


def _extract_javascript_scopes(code_snippet: str) -> List[Dict]:
    """Regex-based scope extraction for JavaScript / TypeScript."""
    scopes: List[Dict] = []
    lines = code_snippet.split("\n")

    for match in _JS_CLASS_RE.finditer(code_snippet):
        line_num = code_snippet[: match.start()].count("\n") + 1
        scopes.append({
            "name": match.group(1),
            "scope_path": match.group(1),
            "scope_type": "ClassDef",
            "body": _extract_body_around(lines, line_num, 30),
            "start_line": line_num,
            "end_line": min(line_num + 30, len(lines)),
            "confidence": 0.7,
            "extraction_method": "regex",
        })

    for match in _JS_FUNC_RE.finditer(code_snippet):
        line_num = code_snippet[: match.start()].count("\n") + 1
        scopes.append({
            "name": match.group(1),
            "scope_path": match.group(1),
            "scope_type": "FunctionDef",
            "body": _extract_body_around(lines, line_num, 20),
            "start_line": line_num,
            "end_line": min(line_num + 20, len(lines)),
            "confidence": 0.7,
            "extraction_method": "regex",
        })

    for match in _JS_ARROW_RE.finditer(code_snippet):
        line_num = code_snippet[: match.start()].count("\n") + 1
        scopes.append({
            "name": match.group(1),
            "scope_path": match.group(1),
            "scope_type": "FunctionDef",
            "body": _extract_body_around(lines, line_num, 15),
            "start_line": line_num,
            "end_line": min(line_num + 15, len(lines)),
            "confidence": 0.7,
            "extraction_method": "regex",
        })

    for match in _JS_METHOD_RE.finditer(code_snippet):
        line_num = code_snippet[: match.start()].count("\n") + 1
        name = match.group(1)
        # Skip control-flow keywords that look like methods
        if name in ("if", "else", "for", "while", "switch", "catch", "return"):
            continue
        scopes.append({
            "name": name,
            "scope_path": name,
            "scope_type": "FunctionDef",
            "body": _extract_body_around(lines, line_num, 15),
            "start_line": line_num,
            "end_line": min(line_num + 15, len(lines)),
            "confidence": 0.7,
            "extraction_method": "regex",
        })

    return scopes


# ── Java Regex Extraction ───────────────────────────────────────────────

_JAVA_CLASS_RE = re.compile(
    r"(?:public\s+)?(?:abstract\s+)?class\s+(\w+)", re.MULTILINE
)
_JAVA_METHOD_RE = re.compile(
    r"(?:public|private|protected|static|\s)+[\w<>\[\]]+\s+(\w+)\s*\([^)]*\)\s*"
    r"(?:throws\s+[\w\s,]+)?\s*\{",
    re.MULTILINE,
)


def _extract_java_scopes(code_snippet: str) -> List[Dict]:
    """Regex-based scope extraction for Java."""
    scopes: List[Dict] = []
    lines = code_snippet.split("\n")

    for match in _JAVA_CLASS_RE.finditer(code_snippet):
        line_num = code_snippet[: match.start()].count("\n") + 1
        scopes.append({
            "name": match.group(1),
            "scope_path": match.group(1),
            "scope_type": "ClassDef",
            "body": _extract_body_around(lines, line_num, 40),
            "start_line": line_num,
            "end_line": min(line_num + 40, len(lines)),
            "confidence": 0.7,
            "extraction_method": "regex",
        })

    for match in _JAVA_METHOD_RE.finditer(code_snippet):
        line_num = code_snippet[: match.start()].count("\n") + 1
        scopes.append({
            "name": match.group(1),
            "scope_path": match.group(1),
            "scope_type": "FunctionDef",
            "body": _extract_body_around(lines, line_num, 20),
            "start_line": line_num,
            "end_line": min(line_num + 20, len(lines)),
            "confidence": 0.7,
            "extraction_method": "regex",
        })

    return scopes


# ── C / C++ Regex Extraction ────────────────────────────────────────────

_CPP_CLASS_RE = re.compile(
    r"(?:class|struct)\s+(\w+)\s*(?::\s*[\w\s,:]+)?\s*\{", re.MULTILINE
)
_CPP_FUNC_RE = re.compile(
    r"(?:[\w&*<>]+(?:\s+[\w&*<>]+)*\s+)?(\w+)\s*\([^)]*\)\s*"
    r"(?:const|override|noexcept|\s)*\s*\{",
    re.MULTILINE,
)


def _extract_cpp_scopes(code_snippet: str) -> List[Dict]:
    """Regex-based scope extraction for C / C++."""
    scopes: List[Dict] = []
    lines = code_snippet.split("\n")

    for match in _CPP_CLASS_RE.finditer(code_snippet):
        line_num = code_snippet[: match.start()].count("\n") + 1
        scopes.append({
            "name": match.group(1),
            "scope_path": match.group(1),
            "scope_type": "ClassDef",
            "body": _extract_body_around(lines, line_num, 40),
            "start_line": line_num,
            "end_line": min(line_num + 40, len(lines)),
            "confidence": 0.7,
            "extraction_method": "regex",
        })

    for match in _CPP_FUNC_RE.finditer(code_snippet):
        line_num = code_snippet[: match.start()].count("\n") + 1
        name = match.group(1)
        if name in ("if", "else", "while", "for", "switch", "catch", "return"):
            continue
        scopes.append({
            "name": name,
            "scope_path": name,
            "scope_type": "FunctionDef",
            "body": _extract_body_around(lines, line_num, 20),
            "start_line": line_num,
            "end_line": min(line_num + 20, len(lines)),
            "confidence": 0.7,
            "extraction_method": "regex",
        })

    return scopes


# ── Helpers ─────────────────────────────────────────────────────────────

def _extract_body_around(lines: List[str], center_line: int, radius: int) -> str:
    """Extract a window of code around a given line number."""
    start = max(0, center_line - 1)
    end = min(len(lines), center_line - 1 + radius)
    return "\n".join(lines[start:end])


_LANGUAGE_ALIASES = {
    "python": "python", ".py": "python", "py": "python",
    "javascript": "javascript", ".js": "javascript", "js": "javascript",
    "typescript": "javascript", ".ts": "javascript", "ts": "javascript",
    ".jsx": "javascript", ".tsx": "javascript",
    "java": "java", ".java": "java",
    "c": "cpp", ".c": "cpp",
    "cpp": "cpp", ".cpp": "cpp", "c++": "cpp", ".cc": "cpp",
    ".cxx": "cpp", ".hpp": "cpp", ".h": "cpp",
}


# ── Public API ──────────────────────────────────────────────────────────

def extract_functions_from_snippet(
    code_snippet: str,
    language: str = "python",
) -> List[Dict]:
    """
    Attempts to parse a code snippet and extract logical scopes (functions,
    classes, methods).

    Returns a list of scope dicts with keys:
        ``name``, ``scope_path``, ``scope_type``, ``body``,
        ``start_line``, ``end_line``, ``confidence``, ``extraction_method``

    Backward-compatible: the ``type`` and ``name`` keys from the old API are
    preserved for callers that depend on them.
    """
    lang = _LANGUAGE_ALIASES.get(language.lower(), language.lower())

    if lang == "python":
        scopes = _extract_python_scopes(code_snippet)
    elif lang == "javascript":
        scopes = _extract_javascript_scopes(code_snippet)
    elif lang == "java":
        scopes = _extract_java_scopes(code_snippet)
    elif lang == "cpp":
        scopes = _extract_cpp_scopes(code_snippet)
    else:
        scopes = []

    # If no scopes found, return the raw snippet so the LLM still has context
    if not scopes:
        return [{
            "name": "module_level_statements" if lang == "python" else "snippet",
            "scope_path": "module_level",
            "scope_type": "Statements" if lang == "python" else "raw_block",
            "type": "Statements" if lang == "python" else "raw_block",
            "body": code_snippet,
            "start_line": 1,
            "end_line": len(code_snippet.split("\n")),
            "confidence": 0.3,
            "extraction_method": "fallback",
        }]

    # Add backward-compat ``type`` key
    for scope in scopes:
        scope.setdefault("type", scope["scope_type"])

    return scopes


def map_diff_to_ast_context(hunks: List[Dict], language: str) -> List[Dict]:
    """
    Given parsed diff hunks containing 'added_lines' and 'context',
    combines them to extract the logical function boundaries that were modified.

    Returns a list of context dicts with keys:
        ``hunk_index``, ``context_name``, ``context_type``, ``code``,
        ``scope_path``, ``confidence``, ``extraction_method``
    """
    extracted_contexts = []
    for index, hunk in enumerate(hunks):
        # We merge context lines + added lines to give the parser maximum
        # chance of succeeding
        reconstructed = []
        context_lines = hunk.get("context", [])
        context_count = len(context_lines)
        mid = context_count // 2

        pre_context = context_lines[:mid]
        post_context = context_lines[mid:]

        reconstructed.extend(pre_context)
        reconstructed.extend(hunk.get("added_lines", []))
        reconstructed.extend(post_context)

        snippet = "\n".join(reconstructed)
        if not snippet.strip():
            continue

        scopes = extract_functions_from_snippet(snippet, language)
        for scope in scopes:
            extracted_contexts.append({
                "hunk_index": index,
                "context_name": scope["name"],
                "context_type": scope.get("scope_type", scope.get("type", "unknown")),
                "code": scope["body"],
                "scope_path": scope.get("scope_path", scope["name"]),
                "confidence": scope.get("confidence", 0.3),
                "extraction_method": scope.get("extraction_method", "fallback"),
            })

    return extracted_contexts
