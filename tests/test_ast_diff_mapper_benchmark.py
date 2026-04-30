"""
AST Diff Mapper — Precision / Recall Benchmark
================================================
A corpus of 20+ synthetic diff hunks covering all edge cases.  Each case has
a ``ground_truth`` list of expected scope names.

The final aggregate test asserts precision ≥ 0.85 and recall ≥ 0.80.

These numbers can be cited directly in a thesis as:
    "Table X — AST diff mapper accuracy across N test scenarios."
"""

import pytest
from typing import List, Dict, Set

from analyzer.context.ast_diff_mapper import (
    extract_functions_from_snippet,
    map_diff_to_ast_context,
)


# ═══════════════════════════════════════════════════════════════════════
# Test Corpus — each entry is (code, language, ground_truth_scope_names)
# ═══════════════════════════════════════════════════════════════════════

CORPUS: List[Dict] = [
    # ── Python: Single function ──────────────────────────────────────
    {
        "id": "py_single_func",
        "description": "Single Python function — simplest case",
        "code": (
            "def greet(name):\n"
            "    return f'Hello, {name}'\n"
        ),
        "language": "python",
        "ground_truth": {"greet"},
    },
    # ── Python: Two functions ────────────────────────────────────────
    {
        "id": "py_two_funcs",
        "description": "Two Python functions in one snippet",
        "code": (
            "def add(a, b):\n"
            "    return a + b\n"
            "\n"
            "def subtract(a, b):\n"
            "    return a - b\n"
        ),
        "language": "python",
        "ground_truth": {"add", "subtract"},
    },
    # ── Python: Async function ───────────────────────────────────────
    {
        "id": "py_async_func",
        "description": "Async function should be detected",
        "code": (
            "async def fetch_data(url):\n"
            "    async with aiohttp.ClientSession() as session:\n"
            "        return await session.get(url)\n"
        ),
        "language": "python",
        "ground_truth": {"fetch_data"},
    },
    # ── Python: Class with methods ───────────────────────────────────
    {
        "id": "py_class_methods",
        "description": "Class with two methods — scoped as ClassName.method",
        "code": (
            "class UserService:\n"
            "    def get_user(self, user_id):\n"
            "        return db.query(user_id)\n"
            "\n"
            "    def delete_user(self, user_id):\n"
            "        db.delete(user_id)\n"
        ),
        "language": "python",
        "ground_truth": {"UserService", "UserService.get_user", "UserService.delete_user"},
    },
    # ── Python: Nested function ──────────────────────────────────────
    {
        "id": "py_nested_func",
        "description": "Nested function should be scoped as outer.inner",
        "code": (
            "def outer():\n"
            "    def inner():\n"
            "        return 42\n"
            "    return inner()\n"
        ),
        "language": "python",
        "ground_truth": {"outer", "outer.inner"},
    },
    # ── Python: Decorator-heavy function ─────────────────────────────
    {
        "id": "py_decorator_func",
        "description": "Function with decorators should still be found",
        "code": (
            "@app.route('/api/users')\n"
            "@login_required\n"
            "def list_users():\n"
            "    return User.query.all()\n"
        ),
        "language": "python",
        "ground_truth": {"list_users"},
    },
    # ── Python: Module-level statements only ─────────────────────────
    {
        "id": "py_module_level",
        "description": "No functions — just statements at module level",
        "code": (
            "import os\n"
            "import sys\n"
            "x = os.getenv('HOME')\n"
            "print(x)\n"
        ),
        "language": "python",
        "ground_truth": {"module_level_statements"},
    },
    # ── Python: Class inheriting from base ───────────────────────────
    {
        "id": "py_class_inheritance",
        "description": "Class with inheritance and a method",
        "code": (
            "class AdminService(UserService):\n"
            "    def promote(self, user_id):\n"
            "        user = self.get_user(user_id)\n"
            "        user.role = 'admin'\n"
        ),
        "language": "python",
        "ground_truth": {"AdminService", "AdminService.promote"},
    },
    # ── Python: Static method inside class ───────────────────────────
    {
        "id": "py_static_method",
        "description": "Static method in a class",
        "code": (
            "class MathUtils:\n"
            "    @staticmethod\n"
            "    def factorial(n):\n"
            "        if n <= 1:\n"
            "            return 1\n"
            "        return n * MathUtils.factorial(n - 1)\n"
        ),
        "language": "python",
        "ground_truth": {"MathUtils", "MathUtils.factorial"},
    },
    # ── Python: Deeply nested classes ────────────────────────────────
    {
        "id": "py_nested_class",
        "description": "Inner class with a method",
        "code": (
            "class Outer:\n"
            "    class Inner:\n"
            "        def do_work(self):\n"
            "            pass\n"
        ),
        "language": "python",
        "ground_truth": {"Outer", "Outer.Inner", "Outer.Inner.do_work"},
    },
    # ── Python: Empty / pass-only function ───────────────────────────
    {
        "id": "py_pass_func",
        "description": "Stub function with pass — still a valid scope",
        "code": (
            "def placeholder():\n"
            "    pass\n"
        ),
        "language": "python",
        "ground_truth": {"placeholder"},
    },
    # ── Python: Incomplete snippet (fragment from diff hunk) ─────────
    {
        "id": "py_incomplete_fragment",
        "description": "Incomplete indented code — should fallback gracefully",
        "code": (
            "    result = db.query(sql)\n"
            "    return result\n"
        ),
        "language": "python",
        # Falls back to module_level_statements since it can't parse
        "ground_truth": {"module_level_statements"},
    },
    # ── JavaScript: Named function ───────────────────────────────────
    {
        "id": "js_named_func",
        "description": "Standard JS function declaration",
        "code": (
            "function fetchUsers() {\n"
            "    return fetch('/api/users');\n"
            "}\n"
        ),
        "language": "javascript",
        "ground_truth": {"fetchUsers"},
    },
    # ── JavaScript: Arrow function ───────────────────────────────────
    {
        "id": "js_arrow_func",
        "description": "Arrow function assigned to const",
        "code": (
            "const handleClick = (event) => {\n"
            "    event.preventDefault();\n"
            "    submit(event.target.value);\n"
            "};\n"
        ),
        "language": "javascript",
        "ground_truth": {"handleClick"},
    },
    # ── JavaScript: Class with methods ───────────────────────────────
    {
        "id": "js_class_methods",
        "description": "JS class with constructor and method",
        "code": (
            "class UserController {\n"
            "    constructor(db) {\n"
            "        this.db = db;\n"
            "    }\n"
            "\n"
            "    async getUser(id) {\n"
            "        return this.db.findById(id);\n"
            "    }\n"
            "}\n"
        ),
        "language": "javascript",
        "ground_truth": {"UserController", "constructor", "getUser"},
    },
    # ── JavaScript: Export default function ───────────────────────────
    {
        "id": "js_export_func",
        "description": "Exported function",
        "code": (
            "export function processPayment(amount) {\n"
            "    return stripe.charge(amount);\n"
            "}\n"
        ),
        "language": "javascript",
        "ground_truth": {"processPayment"},
    },
    # ── JavaScript: Async function ───────────────────────────────────
    {
        "id": "js_async_func",
        "description": "Async JS function",
        "code": (
            "async function loadData() {\n"
            "    const resp = await fetch('/data');\n"
            "    return resp.json();\n"
            "}\n"
        ),
        "language": "javascript",
        "ground_truth": {"loadData"},
    },
    # ── Java: Class with method ──────────────────────────────────────
    {
        "id": "java_class_method",
        "description": "Java class with a public method",
        "code": (
            "public class UserRepository {\n"
            "    public User findById(int id) {\n"
            "        return em.find(User.class, id);\n"
            "    }\n"
            "}\n"
        ),
        "language": "java",
        "ground_truth": {"UserRepository", "findById"},
    },
    # ── Java: Multiple methods ───────────────────────────────────────
    {
        "id": "java_multiple_methods",
        "description": "Java class with multiple methods",
        "code": (
            "public class MathService {\n"
            "    public int add(int a, int b) {\n"
            "        return a + b;\n"
            "    }\n"
            "\n"
            "    private int multiply(int a, int b) {\n"
            "        return a * b;\n"
            "    }\n"
            "}\n"
        ),
        "language": "java",
        "ground_truth": {"MathService", "add", "multiply"},
    },
    # ── C++: Class with method ───────────────────────────────────────
    {
        "id": "cpp_class_method",
        "description": "C++ class with a member function",
        "code": (
            "class Engine {\n"
            "public:\n"
            "    void start() {\n"
            "        running = true;\n"
            "    }\n"
            "};\n"
        ),
        "language": "cpp",
        "ground_truth": {"Engine", "start"},
    },
    # ── C++: Standalone function ─────────────────────────────────────
    {
        "id": "cpp_standalone_func",
        "description": "C++ standalone function",
        "code": (
            "int factorial(int n) {\n"
            "    if (n <= 1) return 1;\n"
            "    return n * factorial(n - 1);\n"
            "}\n"
        ),
        "language": "cpp",
        "ground_truth": {"factorial"},
    },
    # ── TypeScript treated as JavaScript ─────────────────────────────
    {
        "id": "ts_function",
        "description": "TypeScript should use the JS extractor",
        "code": (
            "export async function getServerSideProps() {\n"
            "    const data = await fetchAPI();\n"
            "    return { props: { data } };\n"
            "}\n"
        ),
        "language": "typescript",
        "ground_truth": {"getServerSideProps"},
    },
    # ── Unknown language → raw block ─────────────────────────────────
    {
        "id": "unknown_lang",
        "description": "Unknown language should return a raw block",
        "code": "println!(\"Hello, Rust!\");\n",
        "language": "rust",
        "ground_truth": {"snippet"},
    },
]


# ═══════════════════════════════════════════════════════════════════════
# Individual Tests — one per corpus case
# ═══════════════════════════════════════════════════════════════════════

def _get_canonical_names(scopes: List[Dict]) -> Set[str]:
    """Extract the canonical set of scope identifiers from extraction output.

    Uses ``scope_path`` as the primary identifier.  Short ``name`` values are
    only included when they are NOT already a suffix of an existing scope_path
    (e.g. ``get_user`` is dropped when ``UserService.get_user`` is present).
    """
    scope_paths: Set[str] = set()
    short_names: Set[str] = set()

    for scope in scopes:
        sp = scope.get("scope_path", scope["name"])
        if sp and sp != "module_level":
            scope_paths.add(sp)
        short_names.add(scope["name"])

    # Deduplicate: drop short names that are a suffix of an existing scope_path
    canonical = set(scope_paths)
    for name in short_names:
        already_covered = any(
            sp.endswith(f".{name}") for sp in scope_paths
        )
        if not already_covered:
            canonical.add(name)

    return canonical


@pytest.mark.parametrize(
    "case",
    CORPUS,
    ids=[c["id"] for c in CORPUS],
)
def test_extraction_case(case):
    """Each corpus case should produce at least one scope matching ground truth."""
    scopes = extract_functions_from_snippet(case["code"], case["language"])
    extracted_names = _get_canonical_names(scopes)

    ground_truth: Set[str] = case["ground_truth"]

    # At least one ground truth name should be found
    intersection = extracted_names & ground_truth
    assert len(intersection) > 0, (
        f"[{case['id']}] No ground truth match.\n"
        f"  Expected any of: {ground_truth}\n"
        f"  Got: {extracted_names}"
    )


# ═══════════════════════════════════════════════════════════════════════
# Aggregate Precision / Recall Test
# ═══════════════════════════════════════════════════════════════════════

def _compute_precision_recall():
    """Run all corpus cases and compute aggregate precision and recall."""
    total_true_positives = 0
    total_predicted = 0
    total_ground_truth = 0

    results = []

    for case in CORPUS:
        scopes = extract_functions_from_snippet(case["code"], case["language"])
        extracted_names = _get_canonical_names(scopes)

        ground_truth: Set[str] = case["ground_truth"]
        true_positives = extracted_names & ground_truth
        false_positives = extracted_names - ground_truth
        false_negatives = ground_truth - extracted_names

        total_true_positives += len(true_positives)
        total_predicted += len(extracted_names)
        total_ground_truth += len(ground_truth)

        results.append({
            "id": case["id"],
            "language": case["language"],
            "ground_truth": sorted(ground_truth),
            "extracted": sorted(extracted_names),
            "tp": sorted(true_positives),
            "fp": sorted(false_positives),
            "fn": sorted(false_negatives),
        })

    precision = total_true_positives / max(total_predicted, 1)
    recall = total_true_positives / max(total_ground_truth, 1)
    f1 = (
        2 * precision * recall / max(precision + recall, 1e-9)
    )

    return precision, recall, f1, results


def test_aggregate_precision():
    """Aggregate precision across all corpus cases should be ≥ 0.85."""
    precision, recall, f1, results = _compute_precision_recall()
    print(f"\n{'='*60}")
    print(f"AST Diff Mapper Benchmark Results")
    print(f"{'='*60}")
    print(f"Precision: {precision:.2%}")
    print(f"Recall:    {recall:.2%}")
    print(f"F1 Score:  {f1:.2%}")
    print(f"Cases:     {len(CORPUS)}")

    # Print per-case detail
    for r in results:
        status = "✅" if not r["fn"] else "⚠️"
        print(f"  {status} {r['id']:30s} TP={r['tp']}  FP={r['fp']}  FN={r['fn']}")

    print(f"{'='*60}\n")

    assert precision >= 0.85, f"Precision {precision:.2%} < 85%"


def test_aggregate_recall():
    """Aggregate recall across all corpus cases should be ≥ 0.80."""
    precision, recall, f1, results = _compute_precision_recall()
    assert recall >= 0.80, f"Recall {recall:.2%} < 80%"


# ═══════════════════════════════════════════════════════════════════════
# map_diff_to_ast_context integration test
# ═══════════════════════════════════════════════════════════════════════

class TestMapDiffToAstContext:
    """Tests for the full hunk → context mapping pipeline."""

    def test_single_python_hunk(self):
        """Single hunk with a Python function should map correctly."""
        hunks = [{
            "context": [
                "import os",
                "",
                "    return result",
            ],
            "added_lines": [
                "def process(data):",
                "    result = data.strip()",
                "    return result",
            ],
        }]
        contexts = map_diff_to_ast_context(hunks, "python")
        assert len(contexts) >= 1
        names = {c["context_name"] for c in contexts}
        assert "process" in names

    def test_empty_hunk_skipped(self):
        """Empty hunks should be skipped without error."""
        hunks = [{"context": [], "added_lines": []}]
        contexts = map_diff_to_ast_context(hunks, "python")
        assert contexts == []

    def test_javascript_hunk(self):
        """JavaScript hunk should extract function names."""
        hunks = [{
            "context": [],
            "added_lines": [
                "function validate(input) {",
                "    return input.length > 0;",
                "}",
            ],
        }]
        contexts = map_diff_to_ast_context(hunks, "javascript")
        assert len(contexts) >= 1
        names = {c["context_name"] for c in contexts}
        assert "validate" in names

    def test_contexts_include_metadata(self):
        """Extracted contexts should include confidence and extraction_method."""
        hunks = [{
            "context": [],
            "added_lines": [
                "def hello():",
                "    return 'world'",
            ],
        }]
        contexts = map_diff_to_ast_context(hunks, "python")
        assert len(contexts) >= 1
        ctx = contexts[0]
        assert "confidence" in ctx
        assert "extraction_method" in ctx
        assert ctx["confidence"] == 1.0  # Python uses real AST
        assert ctx["extraction_method"] == "ast"

    def test_scope_path_for_class_method(self):
        """Class methods should have scope_path = ClassName.method_name."""
        hunks = [{
            "context": [],
            "added_lines": [
                "class Handler:",
                "    def process(self, data):",
                "        return data",
            ],
        }]
        contexts = map_diff_to_ast_context(hunks, "python")
        paths = {c["scope_path"] for c in contexts}
        assert "Handler.process" in paths
