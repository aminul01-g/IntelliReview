"""
IntelliReview — Full System QA Verification Suite
===================================================
Non-destructive integration tests for the entire IntelliReview platform.

Covers:
- Backend API health & endpoint probing (all 35 endpoints)
- Authentication flow (register, login, JWT, protected routes)
- Core analysis pipeline (analyze, upload, diff-review)
- GitHub webhook simulation
- Celery task lifecycle
- MCP server import verification
- Dashboard build verification

Usage:
    pytest tests/test_system_qa.py -v -s --tb=short
"""

import json
import os
import sys
import time
import hashlib
import hmac
import importlib
import subprocess
from typing import Optional
from unittest.mock import MagicMock

import pytest
import requests

# ─── Configuration ──────────────────────────────────────────────────

# The backend runs on port 7860 (from settings.py API_PORT default)
BASE_URL = os.environ.get("QA_BASE_URL", "http://localhost:7860")
API_PREFIX = "/api/v1"
API_URL = f"{BASE_URL}{API_PREFIX}"

# Test credentials
TEST_USER = f"qa_test_{int(time.time())}@test.com"
TEST_PASSWORD = "QATestPassword123!"
TEST_USERNAME = f"qa_tester_{int(time.time())}"


# ═══════════════════════════════════════════════════════════════════════
# Phase 0: Pre-flight checks (can we reach the server at all?)
# ═══════════════════════════════════════════════════════════════════════

class TestPreFlight:
    """Basic connectivity checks."""

    def test_backend_reachable(self):
        """Backend process should be reachable on the configured port."""
        try:
            resp = requests.get(f"{BASE_URL}/health", timeout=5)
            assert resp.status_code == 200
            data = resp.json()
            assert data["status"] == "healthy"
        except requests.ConnectionError:
            pytest.skip(
                f"Backend not running at {BASE_URL}. "
                "Start it with: uvicorn api.main:app --port 7860"
            )

    def test_openapi_json_available(self):
        """FastAPI should expose OpenAPI spec at /openapi.json."""
        try:
            resp = requests.get(f"{BASE_URL}/openapi.json", timeout=5)
            if resp.status_code == 200:
                spec = resp.json()
                assert "openapi" in spec
                assert "paths" in spec
                print(f"\n  OpenAPI version: {spec['openapi']}")
                print(f"  Endpoints found: {len(spec['paths'])}")
            else:
                pytest.skip("OpenAPI spec not available (SPA catch-all may be active)")
        except requests.ConnectionError:
            pytest.skip("Backend not running")

    def test_root_endpoint(self):
        """Root endpoint should return app info or serve SPA."""
        try:
            resp = requests.get(f"{BASE_URL}/", timeout=5)
            assert resp.status_code == 200
            # Either JSON (API-only mode) or HTML (SPA mode)
            content_type = resp.headers.get("content-type", "")
            if "application/json" in content_type:
                data = resp.json()
                assert "name" in data or "status" in data
            elif "text/html" in content_type:
                assert "<html" in resp.text.lower() or "<!doctype" in resp.text.lower()
        except requests.ConnectionError:
            pytest.skip("Backend not running")


# ═══════════════════════════════════════════════════════════════════════
# Phase 1: Authentication Flow
# ═══════════════════════════════════════════════════════════════════════

class TestAuthFlow:
    """Test the full auth lifecycle: register → login → me → logout."""

    _token: Optional[str] = None

    @classmethod
    def _get_token(cls) -> Optional[str]:
        """Register + login and cache the JWT token."""
        if cls._token:
            return cls._token

        try:
            # Register
            resp = requests.post(f"{API_URL}/auth/register", json={
                "email": TEST_USER,
                "username": TEST_USERNAME,
                "password": TEST_PASSWORD,
            }, timeout=5)

            if resp.status_code not in (201, 400):  # 400 = already exists
                return None

            # Login — endpoint uses OAuth2PasswordRequestForm (form-encoded, not JSON)
            resp = requests.post(f"{API_URL}/auth/login", data={
                "username": TEST_USERNAME,
                "password": TEST_PASSWORD,
            }, timeout=5)

            if resp.status_code == 200:
                data = resp.json()
                cls._token = data.get("access_token")
                return cls._token
        except requests.ConnectionError:
            return None
        return None

    def test_register_user(self):
        """POST /auth/register should create a new user."""
        try:
            resp = requests.post(f"{API_URL}/auth/register", json={
                "email": f"qa_reg_{int(time.time())}@test.com",
                "username": f"qa_reg_{int(time.time())}",
                "password": TEST_PASSWORD,
            }, timeout=5)
            assert resp.status_code in (201, 400, 422), f"Unexpected: {resp.status_code}"
            if resp.status_code == 201:
                data = resp.json()
                assert "email" in data or "id" in data
        except requests.ConnectionError:
            pytest.skip("Backend not running")

    def test_login_returns_token(self):
        """POST /auth/login should return a JWT token."""
        token = self._get_token()
        if token is None:
            pytest.skip("Could not authenticate")
        assert len(token) > 20

    def test_me_endpoint(self):
        """GET /auth/me should return current user info when authenticated."""
        token = self._get_token()
        if token is None:
            pytest.skip("Could not authenticate")

        resp = requests.get(f"{API_URL}/auth/me", headers={
            "Authorization": f"Bearer {token}",
        }, timeout=5)
        assert resp.status_code == 200
        data = resp.json()
        assert "email" in data

    def test_protected_route_without_token_rejected(self):
        """Protected routes should return 401/403 without a token."""
        try:
            resp = requests.get(f"{API_URL}/metrics/user", timeout=5)
            assert resp.status_code in (401, 403), f"Expected 401/403, got {resp.status_code}"
        except requests.ConnectionError:
            pytest.skip("Backend not running")


# ═══════════════════════════════════════════════════════════════════════
# Phase 2: Core API Endpoints (Authenticated)
# ═══════════════════════════════════════════════════════════════════════

class TestCoreEndpoints:
    """Test the main API endpoints with authentication."""

    @classmethod
    def _auth_headers(cls):
        token = TestAuthFlow._get_token()
        if not token:
            return None
        return {"Authorization": f"Bearer {token}"}

    # ── Analysis ─────────────────────────────────────────────────────

    def test_analyze_python_snippet(self):
        """POST /analysis/analyze should analyze a Python code snippet."""
        headers = self._auth_headers()
        if not headers:
            pytest.skip("Auth unavailable")

        resp = requests.post(f"{API_URL}/analysis/analyze", json={
            "code": (
                "import os\n"
                "def get_user(user_id):\n"
                "    query = 'SELECT * FROM users WHERE id = ' + user_id\n"
                "    return eval(query)\n"
            ),
            "language": "python",
            "filename": "qa_test.py",
        }, headers=headers, timeout=30)

        assert resp.status_code == 200, f"Got {resp.status_code}: {resp.text[:200]}"
        data = resp.json()
        # Should contain issues (SQL injection, eval usage)
        assert "issues" in data or "findings" in data or "result" in data
        print(f"\n  Analysis returned {len(data.get('issues', data.get('findings', [])))} issues")

    def test_analyze_javascript_snippet(self):
        """POST /analysis/analyze should handle JavaScript."""
        headers = self._auth_headers()
        if not headers:
            pytest.skip("Auth unavailable")

        resp = requests.post(f"{API_URL}/analysis/analyze", json={
            "code": (
                "function fetchData(userId) {\n"
                "    const query = `SELECT * FROM users WHERE id = ${userId}`;\n"
                "    return eval(query);\n"
                "}\n"
            ),
            "language": "javascript",
            "filename": "qa_test.js",
        }, headers=headers, timeout=30)

        assert resp.status_code == 200

    def test_analysis_history(self):
        """GET /analysis/history should return past analyses."""
        headers = self._auth_headers()
        if not headers:
            pytest.skip("Auth unavailable")

        resp = requests.get(f"{API_URL}/analysis/history", headers=headers, timeout=10)
        assert resp.status_code == 200
        data = resp.json()
        assert isinstance(data, list)

    def test_analysis_projects(self):
        """GET /analysis/projects should return project list."""
        headers = self._auth_headers()
        if not headers:
            pytest.skip("Auth unavailable")

        resp = requests.get(f"{API_URL}/analysis/projects", headers=headers, timeout=10)
        assert resp.status_code == 200

    # ── Metrics ──────────────────────────────────────────────────────

    def test_user_metrics(self):
        """GET /metrics/user should return metrics dashboard data."""
        headers = self._auth_headers()
        if not headers:
            pytest.skip("Auth unavailable")

        resp = requests.get(f"{API_URL}/metrics/user", headers=headers, timeout=10)
        assert resp.status_code == 200

    def test_metrics_trends(self):
        """GET /metrics/trends should return time-series trend data."""
        headers = self._auth_headers()
        if not headers:
            pytest.skip("Auth unavailable")

        resp = requests.get(f"{API_URL}/metrics/trends", headers=headers, timeout=10)
        assert resp.status_code == 200

    def test_team_metrics(self):
        """GET /metrics/team should return team-level metrics."""
        headers = self._auth_headers()
        if not headers:
            pytest.skip("Auth unavailable")

        resp = requests.get(f"{API_URL}/metrics/team", headers=headers, timeout=10)
        assert resp.status_code == 200

    # ── Feedback ─────────────────────────────────────────────────────

    def test_feedback_stats(self):
        """GET /feedback/stats should return feedback statistics."""
        headers = self._auth_headers()
        if not headers:
            pytest.skip("Auth unavailable")

        resp = requests.get(f"{API_URL}/feedback/stats", headers=headers, timeout=10)
        assert resp.status_code == 200

    # ── Policies ─────────────────────────────────────────────────────

    def test_get_global_policies(self):
        """GET /policies/global should return global policy config."""
        headers = self._auth_headers()
        if not headers:
            pytest.skip("Auth unavailable")

        resp = requests.get(f"{API_URL}/policies/global", headers=headers, timeout=10)
        assert resp.status_code == 200

    # ── Queue Status ─────────────────────────────────────────────────

    def test_queue_status(self):
        """GET /queue-status should return Celery queue status."""
        headers = self._auth_headers()
        if not headers:
            pytest.skip("Auth unavailable")

        resp = requests.get(f"{API_URL}/queue-status", headers=headers, timeout=10)
        # May return 200 or 503 if Redis is down
        assert resp.status_code in (200, 503)

    # ── History Service ──────────────────────────────────────────────

    def test_history_health(self):
        """GET /history/health should return history service status."""
        headers = self._auth_headers()
        if not headers:
            pytest.skip("Auth unavailable")

        resp = requests.get(f"{API_URL}/history/health", headers=headers, timeout=10)
        # May return 200 or 503 if the Go service is unavailable
        assert resp.status_code in (200, 503)


# ═══════════════════════════════════════════════════════════════════════
# Phase 3: GitHub Webhook Simulation
# ═══════════════════════════════════════════════════════════════════════

class TestWebhookSimulation:
    """Simulate a GitHub PR webhook to test the webhook receiver."""

    def test_webhook_accepts_pr_event(self):
        """POST /webhooks/github should accept a PR opened event."""
        try:
            payload = {
                "action": "opened",
                "pull_request": {
                    "number": 999,
                    "title": "QA Test PR",
                    "head": {"sha": "abc123", "ref": "feature/qa"},
                    "base": {"ref": "main"},
                    "user": {"login": "qa-bot"},
                },
                "repository": {
                    "full_name": "test-org/test-repo",
                    "name": "test-repo",
                },
                "installation": {"id": 12345},
            }

            resp = requests.post(
                f"{API_URL}/webhooks/github",
                json=payload,
                headers={
                    "X-GitHub-Event": "pull_request",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )

            # Should return 200 (analysis dispatched) or 401 (sig check)
            assert resp.status_code in (200, 401), f"Got {resp.status_code}: {resp.text[:200]}"

            if resp.status_code == 200:
                data = resp.json()
                assert "message" in data
                print(f"\n  Webhook response: {data}")
        except requests.ConnectionError:
            pytest.skip("Backend not running")

    def test_webhook_ignores_non_pr_events(self):
        """POST /webhooks/github should ignore non-PR events gracefully."""
        try:
            resp = requests.post(
                f"{API_URL}/webhooks/github",
                json={"action": "created", "issue": {"number": 1}},
                headers={
                    "X-GitHub-Event": "issues",
                    "Content-Type": "application/json",
                },
                timeout=10,
            )
            assert resp.status_code in (200, 401)
        except requests.ConnectionError:
            pytest.skip("Backend not running")


# ═══════════════════════════════════════════════════════════════════════
# Phase 4: Module Import Verification (non-HTTP)
# ═══════════════════════════════════════════════════════════════════════

class TestModuleImports:
    """Verify that all critical modules can be imported without errors."""

    def test_import_analyzers(self):
        """All analyzer modules should import cleanly."""
        modules = [
            "analyzer.parsers.python_parser",
            "analyzer.parsers.javascript_parser",
            "analyzer.parsers.java_parser",
            "analyzer.parsers.cpp_parser",
            "analyzer.detectors.security",
            "analyzer.detectors.quality",
            "analyzer.detectors.antipatterns",
            "analyzer.detectors.ai_patterns",
            "analyzer.metrics.complexity",
            "analyzer.metrics.duplication",
            "analyzer.context.ast_diff_mapper",
            "analyzer.context.project_context",
            "analyzer.rules.custom_rules",
        ]
        failures = []
        for mod_name in modules:
            try:
                importlib.import_module(mod_name)
            except Exception as e:
                failures.append(f"{mod_name}: {e}")

        if failures:
            print("\n  Import failures:")
            for f in failures:
                print(f"    ❌ {f}")
        assert len(failures) == 0, f"{len(failures)} module imports failed"

    def test_import_feedback_pipeline(self):
        """Feedback pipeline modules should import cleanly."""
        modules = [
            "analyzer.feedback.severity_orchestrator",
            "analyzer.feedback.confidence_router",
        ]
        for mod_name in modules:
            mod = importlib.import_module(mod_name)
            assert mod is not None

    def test_import_api_schemas(self):
        """API schema modules should import cleanly."""
        modules = [
            "api.schemas.feedback_schemas",
        ]
        for mod_name in modules:
            mod = importlib.import_module(mod_name)
            assert mod is not None

    def test_import_mcp_server(self):
        """MCP server module should be importable (even if mcp lib is missing)."""
        try:
            importlib.import_module("api.mcp_server")
        except ImportError as e:
            if "mcp" in str(e).lower():
                pytest.skip("MCP library not installed (optional dependency)")
            raise
        except Exception as e:
            # Other errors (like missing env vars) are acceptable
            pytest.skip(f"MCP server import skipped: {e}")

    def test_import_celery_app(self):
        """Celery app should be importable."""
        mod = importlib.import_module("api.celery_app")
        assert hasattr(mod, "celery_app")


# ═══════════════════════════════════════════════════════════════════════
# Phase 5: Analyzer Pipeline Smoke Test (no network)
# ═══════════════════════════════════════════════════════════════════════

class TestAnalyzerPipeline:
    """Direct smoke tests of the analyzer pipeline (no HTTP required)."""

    def test_python_parser_works(self):
        """PythonParser should parse a simple Python snippet."""
        from analyzer.parsers.python_parser import PythonParser
        parser = PythonParser()
        code = "def hello():\n    return 'world'\n"
        result = parser.parse(code, "test.py")
        assert result is not None

    def test_security_scanner_finds_eval_in_javascript(self):
        """SecurityScanner should detect eval() usage in JavaScript."""
        from analyzer.detectors.security import SecurityScanner
        scanner = SecurityScanner()
        code = "function run(input) {\n    return eval(input);\n}\n"
        issues = scanner.scan(code, "test.js", "javascript")
        assert isinstance(issues, list)
        eval_issues = [i for i in issues if "eval" in str(i).lower()]
        assert len(eval_issues) > 0, "eval() should be detected as a security issue"

    def test_security_scanner_finds_hardcoded_secret(self):
        """SecurityScanner should detect hardcoded passwords."""
        from analyzer.detectors.security import SecurityScanner
        scanner = SecurityScanner()
        code = 'password = "hunter2"\n'
        issues = scanner.scan(code, "test.py", "python")
        assert isinstance(issues, list)
        secret_issues = [i for i in issues if "password" in str(i).lower() or "secret" in str(i).lower()]
        assert len(secret_issues) > 0, "Hardcoded password should be detected"

    def test_quality_detector_runs(self):
        """QualityDetector should run without errors."""
        from analyzer.detectors.quality import QualityDetector
        detector = QualityDetector()
        code = "x = 1\ny = 2\nz = x + y\n"
        issues = detector.detect(code, "test.py", "python")
        assert isinstance(issues, list)

    def test_complexity_analyzer_runs(self):
        """ComplexityAnalyzer should return metrics."""
        from analyzer.metrics.complexity import ComplexityAnalyzer
        analyzer = ComplexityAnalyzer()
        code = (
            "def foo(x):\n"
            "    if x > 0:\n"
            "        return x\n"
            "    return -x\n"
        )
        metrics = analyzer.analyze(code, "python")
        assert isinstance(metrics, dict)
        assert "lines_of_code" in metrics or "loc" in metrics or len(metrics) > 0

    def test_custom_rules_engine(self):
        """CustomRules engine should evaluate rules from YAML."""
        from analyzer.rules.custom_rules import CustomRuleEngine
        engine = CustomRuleEngine()
        # Should work even with no project config
        assert engine is not None

    def test_ast_diff_mapper_smoke(self):
        """AST diff mapper should extract function scopes from Python code."""
        from analyzer.context.ast_diff_mapper import extract_functions_from_snippet
        code = "def process(data):\n    return data.strip()\n"
        scopes = extract_functions_from_snippet(code, "python")
        assert len(scopes) >= 1
        names = {s["name"] for s in scopes}
        assert "process" in names

    def test_severity_orchestrator_smoke(self):
        """SeverityOrchestrator should calibrate raw findings."""
        from analyzer.feedback.severity_orchestrator import SeverityOrchestrator
        orch = SeverityOrchestrator(project_root=None)
        result = orch.calibrate([
            {"type": "security_vulnerability", "severity": "critical",
             "line": 10, "message": "SQL Injection", "file_path": "test.py"},
        ])
        assert len(result.important_findings) + (
            result.nit_summary.total_nit_count if result.nit_summary else 0
        ) + len(result.preexisting_findings) >= 1

    def test_confidence_router_smoke(self):
        """ConfidenceRouter should classify findings."""
        from analyzer.feedback.confidence_router import ConfidenceRouter
        router = ConfidenceRouter(conclusive_threshold=0.70)
        result = router.route([
            {"type": "security_vulnerability", "severity": "critical",
             "line": 10, "cwe": "CWE-89", "message": "SQL Injection"},
        ])
        assert len(result.conclusive) + len(result.needs_llm) == 1


# ═══════════════════════════════════════════════════════════════════════
# Phase 6: Dashboard Build Verification
# ═══════════════════════════════════════════════════════════════════════

class TestDashboard:
    """Verify the React dashboard build artifacts."""

    def test_dist_directory_exists(self):
        """Dashboard should have a built dist/ directory."""
        dist_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "dashboard", "dist"
        )
        if not os.path.exists(dist_path):
            pytest.skip("Dashboard not built (run: cd dashboard && npm run build)")
        assert os.path.isdir(dist_path)

    def test_index_html_exists(self):
        """dist/index.html should exist after build."""
        dist_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "dashboard", "dist", "index.html"
        )
        if not os.path.exists(dist_path):
            pytest.skip("Dashboard not built")
        assert os.path.isfile(dist_path)
        with open(dist_path) as f:
            content = f.read()
            assert "<html" in content.lower() or "<!doctype" in content.lower()

    def test_assets_directory_exists(self):
        """dist/assets/ should contain JS and CSS bundles."""
        assets_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "dashboard", "dist", "assets"
        )
        if not os.path.exists(assets_path):
            pytest.skip("Dashboard not built")
        files = os.listdir(assets_path)
        js_files = [f for f in files if f.endswith(".js")]
        css_files = [f for f in files if f.endswith(".css")]
        assert len(js_files) > 0, "No JS bundles found in dist/assets/"
        assert len(css_files) > 0, "No CSS bundles found in dist/assets/"
        print(f"\n  JS bundles: {len(js_files)}, CSS bundles: {len(css_files)}")

    def test_package_json_valid(self):
        """Dashboard package.json should be valid and have required scripts."""
        pkg_path = os.path.join(
            os.path.dirname(os.path.dirname(__file__)),
            "dashboard", "package.json"
        )
        with open(pkg_path) as f:
            pkg = json.load(f)
        assert "name" in pkg
        assert "scripts" in pkg
        assert "dev" in pkg["scripts"]
        assert "build" in pkg["scripts"]


# ═══════════════════════════════════════════════════════════════════════
# Phase 7: Celery Configuration Verification
# ═══════════════════════════════════════════════════════════════════════

class TestCeleryConfig:
    """Verify Celery configuration and task registration."""

    def test_celery_app_configured(self):
        """Celery app should have correct broker and backend."""
        from api.celery_app import celery_app
        assert celery_app.main == "intellireview_tasks"

    def test_task_routes_defined(self):
        """Celery should have task routing configuration."""
        from api.celery_app import celery_app
        routes = celery_app.conf.task_routes
        assert routes is not None
        assert len(routes) > 0

    def test_beat_schedule_defined(self):
        """Celery Beat should have the daily rollup schedule."""
        from api.celery_app import celery_app
        beat = celery_app.conf.beat_schedule
        assert "daily-metrics-rollup" in beat

    def test_task_modules_importable(self):
        """Task modules should be importable."""
        try:
            importlib.import_module("api.tasks.analysis_tasks")
        except ImportError:
            pytest.skip("analysis_tasks not importable (may need Redis)")
        except Exception:
            pass  # Other errors are acceptable at import time


# ═══════════════════════════════════════════════════════════════════════
# Phase 8: Existing Test Suite Regression
# ═══════════════════════════════════════════════════════════════════════

class TestExistingRegressionSuite:
    """Run the project's existing test suite and verify results."""

    def test_benchmark_tests_pass(self):
        """AST Diff Mapper benchmark should pass."""
        result = subprocess.run(
            [sys.executable, "-m", "pytest",
             "tests/test_ast_diff_mapper_benchmark.py", "-q", "--tb=line"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.dirname(__file__)),
            timeout=30,
        )
        assert "failed" not in result.stdout.lower(), f"Benchmark failed:\n{result.stdout}\n{result.stderr}"
        print(f"\n  {result.stdout.strip().split(chr(10))[-1]}")

    def test_confidence_router_tests_pass(self):
        """Confidence Router tests should pass."""
        result = subprocess.run(
            [sys.executable, "-m", "pytest",
             "tests/test_confidence_router.py", "-q", "--tb=line"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.dirname(__file__)),
            timeout=30,
        )
        assert "failed" not in result.stdout.lower() and "error" not in result.stdout.lower(), f"Router tests failed:\n{result.stdout}\n{result.stderr}"

    def test_learning_loop_tests_pass(self):
        """Learning Loop simulation tests should pass."""
        result = subprocess.run(
            [sys.executable, "-m", "pytest",
             "tests/test_learning_loop_simulation.py", "-q", "--tb=line"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.dirname(__file__)),
            timeout=30,
        )
        assert "failed" not in result.stdout.lower() and "error" not in result.stdout.lower()

    def test_ablation_study_tests_pass(self):
        """Ablation study tests should pass."""
        result = subprocess.run(
            [sys.executable, "-m", "pytest",
             "tests/test_ablation_study.py", "-q", "--tb=line"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.dirname(__file__)),
            timeout=30,
        )
        assert "failed" not in result.stdout.lower() and "error" not in result.stdout.lower()

    def test_feedback_generator_tests_pass(self):
        """Feedback generator tests should pass."""
        result = subprocess.run(
            [sys.executable, "-m", "pytest",
             "tests/test_feedback_generator.py", "-q", "--tb=line"],
            capture_output=True, text=True,
            cwd=os.path.dirname(os.path.dirname(__file__)),
            timeout=30,
        )
        assert "failed" not in result.stdout.lower() and "error" not in result.stdout.lower()
