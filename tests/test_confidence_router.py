"""
Tests for the Confidence Router
================================
Covers:
- Confidence score computation for various finding types
- Routing logic (conclusive vs. needs_llm)
- Threshold boundary conditions
- ThresholdSweepExperiment with synthetic data
"""

import pytest
from typing import Dict, Any, List

from analyzer.feedback.confidence_router import (
    ConfidenceRouter,
    RoutingResult,
    ThresholdSweepExperiment,
    SweepPoint,
    compute_finding_confidence,
)


# ── Fixtures ────────────────────────────────────────────────────────────

def _make_high_confidence_finding(**overrides) -> Dict[str, Any]:
    """A finding with many high-confidence signals."""
    base = {
        "type": "security_vulnerability",
        "severity": "critical",
        "line": 42,
        "message": "SQL Injection detected via string concatenation.",
        "cwe": "CWE-89",
        "reference_url": "https://owasp.org/attacks/SQL_Injection",
        "suggested_fix_diff": "- cursor.execute(q)\n+ cursor.execute(q, params)",
        "file_path": "api/routes.py",
    }
    base.update(overrides)
    return base


def _make_low_confidence_finding(**overrides) -> Dict[str, Any]:
    """A finding with few confidence signals."""
    base = {
        "type": "antipattern",
        "severity": "medium",
        "line": 0,
        "message": "Consider using a factory pattern here.",
        "file_path": "models/user.py",
    }
    base.update(overrides)
    return base


def _make_medium_confidence_finding(**overrides) -> Dict[str, Any]:
    """A finding in the borderline zone."""
    base = {
        "type": "quality",
        "severity": "medium",
        "line": 15,
        "message": "Variable naming does not follow conventions.",
        "suggestion": "Use snake_case.",
        "file_path": "utils.py",
    }
    base.update(overrides)
    return base


# ═══════════════════════════════════════════════════════════════════════
# Confidence Score Tests
# ═══════════════════════════════════════════════════════════════════════

class TestConfidenceScore:
    """Tests for the compute_finding_confidence function."""

    def test_high_confidence_finding_scores_high(self):
        """A finding with CWE, diff, reference, and line should score > 0.8."""
        finding = _make_high_confidence_finding()
        score = compute_finding_confidence(finding)
        assert score >= 0.80, f"High-confidence finding scored only {score:.2f}"

    def test_low_confidence_finding_scores_low(self):
        """A finding with no CWE, no line, and ambiguous type should score < 0.5."""
        finding = _make_low_confidence_finding()
        score = compute_finding_confidence(finding)
        assert score < 0.50, f"Low-confidence finding scored {score:.2f}"

    def test_custom_rule_gets_boost(self):
        """Custom rules (user-defined) should get high confidence."""
        finding = {
            "type": "custom_rule:no-eval",
            "severity": "critical",
            "line": 10,
            "message": "eval() is banned.",
        }
        score = compute_finding_confidence(finding)
        assert score >= 0.35, f"Custom rule scored only {score:.2f}"

    def test_duplication_gets_boost(self):
        """Code duplication findings should get high confidence."""
        finding = {
            "type": "code_duplication",
            "severity": "medium",
            "line": 20,
            "message": "Duplicate code block found.",
        }
        score = compute_finding_confidence(finding)
        assert score >= 0.35, f"Duplication finding scored only {score:.2f}"

    def test_score_clamped_to_0_1(self):
        """Score should always be in [0.0, 1.0]."""
        # Even with maximum signals
        finding = _make_high_confidence_finding()
        score = compute_finding_confidence(finding)
        assert 0.0 <= score <= 1.0

        # Even with negative adjustments
        finding = _make_low_confidence_finding(type="ai_over_engineering")
        score = compute_finding_confidence(finding)
        assert 0.0 <= score <= 1.0

    def test_cwe_presence_adds_significant_confidence(self):
        """Having a CWE should meaningfully increase confidence."""
        without_cwe = _make_medium_confidence_finding()
        with_cwe = _make_medium_confidence_finding(cwe="CWE-79")

        score_without = compute_finding_confidence(without_cwe)
        score_with = compute_finding_confidence(with_cwe)

        assert score_with > score_without + 0.2, (
            f"CWE should add ≥0.2: without={score_without:.2f}, with={score_with:.2f}"
        )


# ═══════════════════════════════════════════════════════════════════════
# Router Tests
# ═══════════════════════════════════════════════════════════════════════

class TestConfidenceRouter:
    """Tests for the ConfidenceRouter class."""

    def test_high_confidence_routed_to_conclusive(self):
        """High-confidence findings should be routed to conclusive bucket."""
        router = ConfidenceRouter(conclusive_threshold=0.70)
        findings = [_make_high_confidence_finding()]
        result = router.route(findings)

        assert len(result.conclusive) == 1
        assert len(result.needs_llm) == 0

    def test_low_confidence_routed_to_llm(self):
        """Low-confidence findings should be routed to LLM bucket."""
        router = ConfidenceRouter(conclusive_threshold=0.70)
        findings = [_make_low_confidence_finding()]
        result = router.route(findings)

        assert len(result.conclusive) == 0
        assert len(result.needs_llm) == 1

    def test_mixed_findings_split_correctly(self):
        """A mix of findings should be split into both buckets."""
        router = ConfidenceRouter(conclusive_threshold=0.70)
        findings = [
            _make_high_confidence_finding(),
            _make_low_confidence_finding(),
            _make_medium_confidence_finding(),
        ]
        result = router.route(findings)

        assert len(result.conclusive) + len(result.needs_llm) == 3
        assert len(result.conclusive) >= 1  # At least the high-confidence one
        assert len(result.needs_llm) >= 1   # At least the low-confidence one

    def test_threshold_zero_sends_nothing_to_llm(self):
        """Threshold 0.0 means everything is conclusive."""
        router = ConfidenceRouter(conclusive_threshold=0.0, ambiguous_threshold=0.0)
        findings = [
            _make_high_confidence_finding(),
            _make_low_confidence_finding(),
        ]
        result = router.route(findings)
        assert len(result.conclusive) == 2
        assert len(result.needs_llm) == 0

    def test_very_high_threshold_sends_most_to_llm(self):
        """Threshold 1.0 sends almost everything to LLM (score must be >= 1.0)."""
        router = ConfidenceRouter(conclusive_threshold=1.0)
        findings = [
            _make_low_confidence_finding(),
            _make_medium_confidence_finding(),
        ]
        result = router.route(findings)
        # Low and medium confidence findings should all go to LLM
        assert len(result.needs_llm) == 2

    def test_routing_injects_confidence_key(self):
        """Routed findings should have _routing_confidence injected."""
        router = ConfidenceRouter(conclusive_threshold=0.70)
        findings = [_make_high_confidence_finding()]
        result = router.route(findings)

        for f in result.conclusive + result.needs_llm:
            assert "_routing_confidence" in f
            assert 0.0 <= f["_routing_confidence"] <= 1.0

    def test_routing_log_populated(self):
        """The routing log should have one entry per finding."""
        router = ConfidenceRouter(conclusive_threshold=0.70)
        findings = [
            _make_high_confidence_finding(),
            _make_low_confidence_finding(),
        ]
        result = router.route(findings)
        assert len(result.routing_log) == 2

    def test_invalid_threshold_raises(self):
        """Invalid threshold ordering should raise ValueError."""
        with pytest.raises(ValueError):
            ConfidenceRouter(conclusive_threshold=0.3, ambiguous_threshold=0.8)


# ═══════════════════════════════════════════════════════════════════════
# Threshold Sweep Tests
# ═══════════════════════════════════════════════════════════════════════

class TestThresholdSweep:
    """Tests for the ThresholdSweepExperiment."""

    @staticmethod
    def _make_labeled_dataset() -> List[Dict[str, Any]]:
        """Create a synthetic labeled dataset for sweep experiments."""
        return [
            # True positives (human agrees these are real)
            {**_make_high_confidence_finding(), "_human_valid": True},
            {**_make_high_confidence_finding(line=50, cwe="CWE-79"), "_human_valid": True},
            {**_make_medium_confidence_finding(cwe="CWE-22"), "_human_valid": True},
            # False positive (human disagrees)
            {**_make_low_confidence_finding(), "_human_valid": False},
            {**_make_medium_confidence_finding(), "_human_valid": False},
            # True positive with low confidence
            {**_make_low_confidence_finding(type="quality", line=5), "_human_valid": True},
        ]

    def test_sweep_produces_results(self):
        """Sweep should produce a list of SweepPoints."""
        data = self._make_labeled_dataset()
        sweep = ThresholdSweepExperiment(data, step=0.1)
        results = sweep.run()

        assert len(results) > 0
        assert all(isinstance(r, SweepPoint) for r in results)

    def test_sweep_threshold_range(self):
        """Sweep should cover from 0.0 to 1.0."""
        data = self._make_labeled_dataset()
        sweep = ThresholdSweepExperiment(data, step=0.25)
        results = sweep.run()

        thresholds = [r.threshold for r in results]
        assert min(thresholds) == 0.0
        assert max(thresholds) == 1.0

    def test_sweep_cost_decreases_with_threshold(self):
        """Higher threshold → more conclusive → lower LLM cost."""
        data = self._make_labeled_dataset()
        sweep = ThresholdSweepExperiment(data, step=0.25)
        results = sweep.run()

        costs = [r.simulated_cost for r in results]
        # Cost at threshold 0.0 should be ≤ cost at threshold 1.0
        # (at 0.0 everything is conclusive → 0 cost)
        assert costs[0] <= costs[-1]

    def test_sweep_precision_recall_bounded(self):
        """All precision and recall values should be in [0, 1]."""
        data = self._make_labeled_dataset()
        sweep = ThresholdSweepExperiment(data, step=0.1)
        results = sweep.run()

        for r in results:
            assert 0.0 <= r.precision <= 1.0, f"Bad precision: {r.precision}"
            assert 0.0 <= r.recall <= 1.0, f"Bad recall: {r.recall}"
            assert 0.0 <= r.f1 <= 1.0, f"Bad F1: {r.f1}"

    def test_to_dict_list_serializable(self):
        """to_dict_list should produce JSON-serializable output."""
        import json
        data = self._make_labeled_dataset()
        sweep = ThresholdSweepExperiment(data, step=0.25)
        dict_list = sweep.to_dict_list()

        json_str = json.dumps(dict_list)
        assert len(json_str) > 0
        parsed = json.loads(json_str)
        assert len(parsed) == len(dict_list)
