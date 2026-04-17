"""
Tests for the FeedbackGenerator Module
========================================
Covers:
- Pydantic schema validation and evidence mandate
- SeverityOrchestrator calibration logic
- Nit volume cap (>5 nits collapse)
- Dataflow tracing
- Markdown rendering correctness
- Verification walkthrough generation
- FeedbackGenerator end-to-end pipeline
"""

import pytest
import json
from datetime import datetime

from api.schemas.feedback_schemas import (
    AutofixDiff,
    DataflowNode,
    DataflowTrace,
    EvidencePayload,
    FindingCategory,
    NitSummary,
    NitSummaryItem,
    PRReviewComment,
    ReproductionStep,
    ReviewFinding,
    ReviewerFeedbackRequest,
    ReviewerFeedbackResponse,
    SeverityLevel,
    SEVERITY_MARKERS,
    SEVERITY_LABELS,
    TestCase,
    VerificationEntry,
    VerificationWalkthrough,
)
from analyzer.feedback.severity_orchestrator import (
    CalibratedResult,
    SeverityOrchestrator,
)
from analyzer.feedback.feedback_generator import FeedbackGenerator
from analyzer.feedback.verification import VerificationWalkthroughGenerator


# ─── Fixture: Sample Raw Findings ─────────────────────────────────────

def _make_critical_finding(**overrides):
    """Helper: create a raw finding dict simulating a critical issue."""
    base = {
        "type": "security_vulnerability",
        "severity": "critical",
        "line": 42,
        "message": "SQL Injection: String concatenation in query detects a direct SQL Injection risk.",
        "suggestion": "Rewrite using parameterized SQL queries or a safe ORM abstraction.",
        "cwe": "CWE-89",
        "reference_url": "https://owasp.org/www-community/attacks/SQL_Injection",
        "file_path": "api/routes/users.py",
    }
    base.update(overrides)
    return base


def _make_nit_finding(index=0, **overrides):
    """Helper: create a raw finding dict simulating a nit."""
    base = {
        "type": "quality",
        "severity": "low",
        "line": 10 + index,
        "message": f"Variable naming does not follow PEP 8 convention ({index}).",
        "suggestion": "Use snake_case for variable names.",
        "file_path": "api/routes/users.py",
    }
    base.update(overrides)
    return base


def _make_preexisting_finding(**overrides):
    """Helper: create a finding with 'info' severity (maps to preexisting)."""
    base = {
        "type": "antipattern",
        "severity": "info",
        "line": 92,
        "message": "Bare except clause swallowing errors.",
        "suggestion": "Use specific exception types and log errors.",
        "file_path": "api/routes/users.py",
    }
    base.update(overrides)
    return base


# ═══════════════════════════════════════════════════════════════════════
# Schema Validation Tests
# ═══════════════════════════════════════════════════════════════════════

class TestSchemaValidation:
    """Tests for Pydantic schema correctness."""

    def test_severity_markers_mapping(self):
        """Ensure all severity levels have emoji markers."""
        for level in SeverityLevel:
            assert level in SEVERITY_MARKERS
            assert level in SEVERITY_LABELS

    def test_review_finding_roundtrip(self):
        """ReviewFinding should serialize and deserialize cleanly."""
        finding = ReviewFinding(
            id="abc123",
            severity=SeverityLevel.important,
            category=FindingCategory.security,
            title="SQL Injection",
            narrative="Untrusted input flows to execute().",
            file_path="test.py",
            line=42,
            evidence=ReproductionStep(
                title="SQLi Repro",
                payload="' OR 1=1 --",
                expected="HTTP 400",
                actual="HTTP 200 with all data",
            ),
        )
        data = finding.model_dump()
        restored = ReviewFinding(**data)
        assert restored.id == "abc123"
        assert restored.severity == SeverityLevel.important
        assert restored.evidence is not None

    def test_evidence_mandate_auto_generates(self):
        """Important findings without evidence should get auto-generated evidence."""
        finding = ReviewFinding(
            id="test123",
            severity=SeverityLevel.important,
            category=FindingCategory.security,
            title="XSS Vulnerability",
            narrative="Script injection possible.",
            file_path="test.py",
            line=10,
            evidence=None,  # No evidence provided
        )
        # The model validator should auto-generate evidence
        assert finding.evidence is not None
        assert "Auto-generated" in finding.evidence.title
        assert "manual verification" in finding.calibration_reason.lower()

    def test_nit_does_not_require_evidence(self):
        """Nit findings should NOT require evidence."""
        finding = ReviewFinding(
            id="nit001",
            severity=SeverityLevel.nit,
            category=FindingCategory.style,
            title="Naming convention nit",
            narrative="Variable uses camelCase.",
            file_path="test.py",
            line=5,
        )
        assert finding.evidence is None  # No evidence required
        assert finding.calibration_reason is None

    def test_autofix_diff_validation(self):
        """AutofixDiff should validate line numbers correctly."""
        diff = AutofixDiff(
            before="old code",
            after="new code",
            unified_diff="- old\n+ new",
            start_line=1,
            end_line=1,
        )
        assert diff.start_line >= 1
        assert diff.end_line >= 1

    def test_dataflow_trace_structure(self):
        """DataflowTrace should have source, sink, and sanitization status."""
        trace = DataflowTrace(
            source=DataflowNode(
                expression="request.args['id']",
                file_path="app.py",
                line=5,
                node_type="source",
            ),
            sink=DataflowNode(
                expression="cursor.execute(query)",
                file_path="app.py",
                line=15,
                node_type="sink",
            ),
            is_sanitized=False,
            summary="Untrusted input at L5 flows to execute at L15",
        )
        assert not trace.is_sanitized
        assert trace.source.node_type == "source"
        assert trace.sink.node_type == "sink"

    def test_pr_review_comment_auto_totals(self):
        """PRReviewComment should auto-compute total_findings."""
        finding = ReviewFinding(
            id="f1",
            severity=SeverityLevel.important,
            category=FindingCategory.security,
            title="Test",
            narrative="Test",
            file_path="test.py",
            line=1,
        )
        comment = PRReviewComment(
            review_id="r1",
            repository="org/repo",
            pr_number=1,
            important_findings=[finding],
        )
        assert comment.total_findings == 1

    def test_reviewer_feedback_request_schema(self):
        """ReviewerFeedbackRequest should validate correctly."""
        req = ReviewerFeedbackRequest(
            finding_id="abc123",
            action="ignore_pattern",
            comment="This is a false positive in our codebase.",
            repository="org/repo",
            pr_number=42,
        )
        assert req.action == "ignore_pattern"
        assert req.pr_number == 42

    def test_json_serialization(self):
        """All schemas should serialize to valid JSON."""
        finding = ReviewFinding(
            id="json_test",
            severity=SeverityLevel.nit,
            category=FindingCategory.style,
            title="JSON Test",
            narrative="Testing JSON output.",
            file_path="test.py",
            line=1,
        )
        json_str = finding.model_dump_json()
        parsed = json.loads(json_str)
        assert parsed["id"] == "json_test"
        assert parsed["severity"] == "nit"


# ═══════════════════════════════════════════════════════════════════════
# SeverityOrchestrator Tests
# ═══════════════════════════════════════════════════════════════════════

class TestSeverityOrchestrator:
    """Tests for severity calibration logic."""

    def setup_method(self):
        self.orchestrator = SeverityOrchestrator(project_root=None, nit_cap=5)

    def test_critical_maps_to_important(self):
        """Critical raw severity should map to 'important'."""
        raw = [_make_critical_finding()]
        result = self.orchestrator.calibrate(raw)
        assert len(result.important_findings) == 1
        assert result.important_findings[0].severity == SeverityLevel.important

    def test_low_maps_to_nit(self):
        """Low raw severity should map to 'nit'."""
        raw = [_make_nit_finding()]
        result = self.orchestrator.calibrate(raw)
        assert result.nit_summary is not None
        assert result.nit_summary.total_nit_count == 1

    def test_info_maps_to_preexisting(self):
        """Info raw severity should map to 'preexisting'."""
        raw = [_make_preexisting_finding()]
        result = self.orchestrator.calibrate(raw)
        assert len(result.preexisting_findings) == 1
        assert result.preexisting_findings[0].severity == SeverityLevel.preexisting

    def test_nit_volume_cap_at_5(self):
        """When >5 nits, only first 5 shown and rest collapsed."""
        raw = [_make_nit_finding(i) for i in range(8)]
        result = self.orchestrator.calibrate(raw)
        assert result.nit_summary is not None
        assert result.nit_summary.total_nit_count == 8
        assert len(result.nit_summary.shown_nits) == 5
        assert len(result.nit_summary.collapsed_nits) == 3

    def test_nit_cap_boundary_exact_5(self):
        """Exactly 5 nits should all be shown, none collapsed."""
        raw = [_make_nit_finding(i) for i in range(5)]
        result = self.orchestrator.calibrate(raw)
        assert result.nit_summary is not None
        assert result.nit_summary.total_nit_count == 5
        assert len(result.nit_summary.shown_nits) == 5
        assert len(result.nit_summary.collapsed_nits) == 0

    def test_nit_cap_boundary_4_nits(self):
        """4 nits should all be shown without collapse."""
        raw = [_make_nit_finding(i) for i in range(4)]
        result = self.orchestrator.calibrate(raw)
        assert result.nit_summary is not None
        assert len(result.nit_summary.shown_nits) == 4
        assert len(result.nit_summary.collapsed_nits) == 0

    def test_dataflow_boost_promotes_to_important(self):
        """A nit with a confirmed unsanitized dataflow trace should become important."""
        raw = [_make_nit_finding()]
        finding_id = self.orchestrator._generate_finding_id(raw[0])

        trace = DataflowTrace(
            source=DataflowNode(
                expression="request.args['id']",
                file_path="test.py",
                line=5,
                node_type="source",
            ),
            sink=DataflowNode(
                expression="cursor.execute(q)",
                file_path="test.py",
                line=15,
                node_type="sink",
            ),
            is_sanitized=False,
            summary="Tainted flow detected",
        )

        result = self.orchestrator.calibrate(raw, dataflow_traces={finding_id: trace})
        assert len(result.important_findings) == 1
        assert "Dataflow boost" in result.calibration_log[0]

    def test_sanitized_dataflow_does_not_promote(self):
        """A sanitized dataflow trace should NOT promote to important."""
        raw = [_make_nit_finding()]
        finding_id = self.orchestrator._generate_finding_id(raw[0])

        trace = DataflowTrace(
            source=DataflowNode(
                expression="request.args['id']",
                file_path="test.py",
                line=5,
                node_type="source",
            ),
            sink=DataflowNode(
                expression="cursor.execute(q)",
                file_path="test.py",
                line=15,
                node_type="sink",
            ),
            is_sanitized=True,  # Sanitized!
            summary="Sanitized flow",
        )

        result = self.orchestrator.calibrate(raw, dataflow_traces={finding_id: trace})
        # Should remain a nit since the trace is sanitized
        assert result.nit_summary is not None
        assert result.nit_summary.total_nit_count == 1

    def test_kb_demotion_with_high_rejection_rate(self):
        """Important findings with >60% rejection in KB should demote to nit."""

        class MockKB:
            def get_acceptance_rate(self, issue_type):
                return 0.30  # 70% rejection rate

            @property
            def patterns(self):
                return {
                    "security_vulnerability": {"total": 10, "accepted": 3, "rejected": 7}
                }

        raw = [_make_critical_finding()]
        result = self.orchestrator.calibrate(raw, knowledge_base=MockKB())
        assert result.nit_summary is not None
        assert result.nit_summary.total_nit_count == 1
        assert len(result.important_findings) == 0

    def test_kb_no_demotion_below_sample_threshold(self):
        """Findings with too few KB samples should NOT be demoted."""

        class MockKB:
            def get_acceptance_rate(self, issue_type):
                return 0.20  # Very high rejection rate

            @property
            def patterns(self):
                return {
                    "security_vulnerability": {"total": 3, "accepted": 1, "rejected": 2}
                }

        raw = [_make_critical_finding()]
        result = self.orchestrator.calibrate(raw, knowledge_base=MockKB())
        # Should remain important — not enough samples
        assert len(result.important_findings) == 1

    def test_mixed_severities_sorted_correctly(self):
        """Raw findings with mixed severities should be sorted into correct buckets."""
        raw = [
            _make_critical_finding(),
            _make_nit_finding(0),
            _make_nit_finding(1),
            _make_preexisting_finding(),
        ]
        result = self.orchestrator.calibrate(raw)
        assert len(result.important_findings) == 1
        assert result.nit_summary.total_nit_count == 2
        assert len(result.preexisting_findings) == 1

    def test_evidence_generated_for_important_findings(self):
        """Important findings should have evidence after calibration."""
        raw = [_make_critical_finding()]
        result = self.orchestrator.calibrate(raw)
        finding = result.important_findings[0]
        assert finding.evidence is not None


# ═══════════════════════════════════════════════════════════════════════
# FeedbackGenerator Tests
# ═══════════════════════════════════════════════════════════════════════

class TestFeedbackGenerator:
    """Tests for the core FeedbackGenerator service."""

    def setup_method(self):
        self.generator = FeedbackGenerator(project_root=None)

    def test_generate_review_produces_pr_comment(self):
        """generate_review should produce a valid PRReviewComment."""
        raw = [_make_critical_finding(), _make_nit_finding()]
        result = self.generator.generate_review(
            raw_findings=raw,
            code='cursor.execute(f"SELECT * FROM users WHERE id={user_id}")',
            language="python",
            repository="org/repo",
            pr_number=42,
        )
        assert isinstance(result, PRReviewComment)
        assert result.pr_number == 42
        assert result.repository == "org/repo"
        assert result.total_findings >= 2

    def test_verdict_fail_on_important(self):
        """Verdict should be 'fail' when important findings exist."""
        raw = [_make_critical_finding()]
        result = self.generator.generate_review(
            raw_findings=raw,
            code="test",
            language="python",
        )
        assert result.verdict == "fail"

    def test_verdict_warn_on_nits_only(self):
        """Verdict should be 'warn' when only nits exist."""
        raw = [_make_nit_finding()]
        result = self.generator.generate_review(
            raw_findings=raw,
            code="test",
            language="python",
        )
        assert result.verdict == "warn"

    def test_verdict_pass_on_clean(self):
        """Verdict should be 'pass' when no findings."""
        result = self.generator.generate_review(
            raw_findings=[],
            code="print('hello')",
            language="python",
        )
        assert result.verdict == "pass"

    def test_verification_walkthrough_generated(self):
        """Every review should include a verification walkthrough."""
        raw = [_make_critical_finding(), _make_nit_finding()]
        result = self.generator.generate_review(
            raw_findings=raw,
            code="test",
            language="python",
        )
        assert result.verification_walkthrough is not None
        assert result.verification_walkthrough.total_findings >= 2

    def test_nit_collapse_in_full_pipeline(self):
        """End-to-end: 8 nits should result in 5 shown + 3 collapsed."""
        raw = [_make_nit_finding(i) for i in range(8)]
        result = self.generator.generate_review(
            raw_findings=raw,
            code="test",
            language="python",
        )
        assert result.nit_findings is not None
        assert len(result.nit_findings.shown_nits) == 5
        assert len(result.nit_findings.collapsed_nits) == 3


# ═══════════════════════════════════════════════════════════════════════
# Markdown Rendering Tests
# ═══════════════════════════════════════════════════════════════════════

class TestMarkdownRendering:
    """Tests for Markdown output correctness."""

    def setup_method(self):
        self.generator = FeedbackGenerator(project_root=None)

    def test_render_contains_severity_markers(self):
        """Rendered Markdown should contain severity emoji markers."""
        raw = [_make_critical_finding()]
        comment = self.generator.generate_review(
            raw_findings=raw,
            code="test",
            language="python",
        )
        md = self.generator.render_markdown(comment)
        assert "🔴" in md
        assert "Important Findings" in md

    def test_render_contains_autofix_diff(self):
        """Rendered Markdown should include diff code blocks for autofixes."""
        raw = [_make_critical_finding(
            suggested_fix_diff="- old line\n+ new line"
        )]
        comment = self.generator.generate_review(
            raw_findings=raw,
            code="test",
            language="python",
        )
        md = self.generator.render_markdown(comment)
        assert "```diff" in md
        assert "Autofix" in md

    def test_render_contains_evidence_section(self):
        """Rendered Markdown should include evidence for important findings."""
        raw = [_make_critical_finding()]
        comment = self.generator.generate_review(
            raw_findings=raw,
            code="test",
            language="python",
        )
        md = self.generator.render_markdown(comment)
        assert "Evidence" in md

    def test_render_contains_cwe_reference(self):
        """Rendered Markdown should include CWE references."""
        raw = [_make_critical_finding()]
        comment = self.generator.generate_review(
            raw_findings=raw,
            code="test",
            language="python",
        )
        md = self.generator.render_markdown(comment)
        assert "CWE-89" in md

    def test_render_collapsed_nits_table(self):
        """Rendered Markdown should contain collapsed nits table for >5 nits."""
        raw = [_make_nit_finding(i) for i in range(8)]
        comment = self.generator.generate_review(
            raw_findings=raw,
            code="test",
            language="python",
        )
        md = self.generator.render_markdown(comment)
        assert "+3 more nits" in md
        assert "collapsed" in md.lower()

    def test_render_verification_walkthrough(self):
        """Rendered Markdown should include the verification walkthrough."""
        raw = [_make_critical_finding(), _make_nit_finding()]
        comment = self.generator.generate_review(
            raw_findings=raw,
            code="test",
            language="python",
        )
        md = self.generator.render_markdown(comment)
        assert "Verification Walkthrough" in md

    def test_render_verdict_in_header(self):
        """Rendered Markdown should show the verdict in the header."""
        raw = [_make_critical_finding()]
        comment = self.generator.generate_review(
            raw_findings=raw,
            code="test",
            language="python",
        )
        md = self.generator.render_markdown(comment)
        assert "FAIL" in md

    def test_render_empty_review(self):
        """A clean review should render gracefully."""
        comment = self.generator.generate_review(
            raw_findings=[],
            code="pass",
            language="python",
        )
        md = self.generator.render_markdown(comment)
        assert "PASS" in md
        assert "IntelliReview" in md


# ═══════════════════════════════════════════════════════════════════════
# Verification Walkthrough Tests
# ═══════════════════════════════════════════════════════════════════════

class TestVerificationWalkthrough:
    """Tests for verification walkthrough generation."""

    def setup_method(self):
        self.wt_gen = VerificationWalkthroughGenerator()

    def test_generates_walkthrough(self):
        """VerificationWalkthrough should be generated from findings."""
        important = [
            ReviewFinding(
                id="f1",
                severity=SeverityLevel.important,
                category=FindingCategory.security,
                title="SQL Injection",
                narrative="Tainted input.",
                file_path="test.py",
                line=1,
                evidence=ReproductionStep(
                    title="SQLi",
                    payload="test",
                    expected="safe",
                    actual="vulnerable",
                ),
            )
        ]
        wt = self.wt_gen.generate(
            important_findings=important,
            nit_summary=None,
            preexisting_findings=[],
            calibration_log=[],
        )
        assert isinstance(wt, VerificationWalkthrough)
        assert wt.important_count == 1
        assert wt.total_findings == 1
        assert len(wt.entries) == 1

    def test_walkthrough_tracks_kb_rules(self):
        """Walkthrough should track KB rules from the calibration log."""
        wt = self.wt_gen.generate(
            important_findings=[],
            nit_summary=None,
            preexisting_findings=[],
            calibration_log=[
                "KB demotion: security_vulnerability has 70% rejection rate",
                "Config override: low → important",
            ],
        )
        assert len(wt.knowledge_base_rules_applied) == 2

    def test_walkthrough_counts_dataflow_traces(self):
        """Walkthrough should count how many findings have dataflow traces."""
        trace = DataflowTrace(
            source=DataflowNode(
                expression="input",
                file_path="test.py",
                line=1,
                node_type="source",
            ),
            sink=DataflowNode(
                expression="exec",
                file_path="test.py",
                line=10,
                node_type="sink",
            ),
            is_sanitized=False,
            summary="test",
        )
        important = [
            ReviewFinding(
                id="f1",
                severity=SeverityLevel.important,
                category=FindingCategory.security,
                title="Code Injection",
                narrative="Eval used.",
                file_path="test.py",
                line=10,
                dataflow_trace=trace,
            )
        ]
        wt = self.wt_gen.generate(
            important_findings=important,
            nit_summary=None,
            preexisting_findings=[],
            calibration_log=[],
        )
        assert wt.dataflow_traces_checked == 1

    def test_render_artifact_markdown(self):
        """Walkthrough should render to valid Markdown."""
        wt = self.wt_gen.generate(
            important_findings=[],
            nit_summary=NitSummary(
                total_nit_count=8,
                shown_nits=[],
                collapsed_nits=[
                    NitSummaryItem(title="nit1", file_path="test.py", line=1, category=FindingCategory.style),
                ],
            ),
            preexisting_findings=[],
            calibration_log=[],
        )
        md = self.wt_gen.render_artifact_markdown(wt)
        assert "Verification Walkthrough" in md
        assert "Nits Collapsed" in md


# ═══════════════════════════════════════════════════════════════════════
# Dataflow Tracing Tests
# ═══════════════════════════════════════════════════════════════════════

class TestDataflowTracing:
    """Tests for the lightweight dataflow tracking in FeedbackGenerator."""

    def setup_method(self):
        self.generator = FeedbackGenerator(project_root=None)

    def test_detects_sql_injection_dataflow(self):
        """Should detect request input flowing to cursor.execute."""
        code = '''
from flask import request

def get_user():
    user_id = request.args["user_id"]
    cursor.execute(f"SELECT * FROM users WHERE id={user_id}")
    return cursor.fetchone()
'''
        raw = [_make_critical_finding(line=6)]
        traces = self.generator._compute_dataflow_traces(raw, code, "python")
        # Should find at least one trace
        assert len(traces) >= 1
        trace = list(traces.values())[0]
        assert not trace.is_sanitized

    def test_no_trace_for_non_security_findings(self):
        """Non-security findings should not generate dataflow traces."""
        code = "x = 1\ny = x + 2\n"
        raw = [_make_nit_finding()]
        traces = self.generator._compute_dataflow_traces(raw, code, "python")
        assert len(traces) == 0


# ═══════════════════════════════════════════════════════════════════════
# Interactive Feedback Schema Tests
# ═══════════════════════════════════════════════════════════════════════

class TestInteractiveFeedback:
    """Tests for the interactive feedback schemas."""

    def test_request_better_fix_schema(self):
        req = ReviewerFeedbackRequest(
            finding_id="abc123",
            action="request_better_fix",
            comment="The fix doesn't handle edge cases.",
            repository="org/repo",
            pr_number=10,
        )
        assert req.action == "request_better_fix"

    def test_ignore_pattern_schema(self):
        req = ReviewerFeedbackRequest(
            finding_id="xyz789",
            action="ignore_pattern",
            repository="org/repo",
            pr_number=10,
        )
        assert req.action == "ignore_pattern"
        assert req.comment is None

    def test_response_schema(self):
        resp = ReviewerFeedbackResponse(
            finding_id="abc123",
            action_taken="Pattern suppressed",
            knowledge_base_updated=True,
            message="Done",
        )
        assert resp.knowledge_base_updated is True
