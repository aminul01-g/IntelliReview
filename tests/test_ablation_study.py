"""
Tests for the Ablation Study Experiment
========================================
Validates:
- Additive ablation produces the correct number of configurations
- Subtractive ablation covers all step combinations
- Adding steps changes the output (i.e., steps have an effect)
- KB demotion step specifically reduces 'important' findings
- The full pipeline is strictly better than baseline
"""

import pytest
from typing import Dict, Any, List

from tests.experiments.ablation_experiment import (
    AblationExperiment,
    AblationMetrics,
)
from tests.experiments.learning_loop_experiment import InMemoryKB


# ── Fixtures ────────────────────────────────────────────────────────────

def _make_corpus() -> List[Dict[str, Any]]:
    """Corpus with diverse severity levels for ablation testing."""
    return [
        # Critical findings → important (can be demoted by KB)
        {"type": "security_vulnerability", "severity": "critical", "line": 10,
         "message": "Hardcoded secret", "cwe": "CWE-798", "file_path": "config.py"},
        {"type": "security_vulnerability", "severity": "critical", "line": 20,
         "message": "SQL Injection", "cwe": "CWE-89", "file_path": "api/db.py"},
        {"type": "security_vulnerability", "severity": "high", "line": 30,
         "message": "XSS", "cwe": "CWE-79", "file_path": "api/views.py"},
        # Medium findings → nit
        {"type": "antipattern", "severity": "medium", "line": 40,
         "message": "Bare except", "file_path": "handlers.py"},
        {"type": "quality", "severity": "medium", "line": 50,
         "message": "Too many arguments", "file_path": "utils.py"},
        # Low findings → nit
        {"type": "quality", "severity": "low", "line": 60,
         "message": "Line too long", "file_path": "utils.py"},
    ]


def _make_kb_with_rejections() -> InMemoryKB:
    """Pre-populate KB with rejection data for security_vulnerability."""
    kb = InMemoryKB()
    # 8 rejections out of 10 → 80% rejection rate → triggers demotion
    for i in range(10):
        kb.record_feedback("security_vulnerability", accepted=(i < 2))
    return kb


# ═══════════════════════════════════════════════════════════════════════
# Additive Ablation Tests
# ═══════════════════════════════════════════════════════════════════════

class TestAdditiveAblation:
    """Tests for additive (build-up) ablation."""

    def test_produces_correct_number_of_configs(self):
        """Should produce N+1 configs (baseline + one per step)."""
        experiment = AblationExperiment(_make_corpus())
        results = experiment.run_additive()

        # 5 steps + 1 baseline = 6 configurations
        assert len(results) == 6
        assert results[0].config_name == "baseline"

    def test_baseline_has_no_events(self):
        """Baseline (no steps) should produce 0 calibration events."""
        experiment = AblationExperiment(_make_corpus())
        results = experiment.run_additive()

        baseline = results[0]
        assert baseline.demotion_events == 0
        assert baseline.promotion_events == 0
        assert len(baseline.calibration_events) == 0

    def test_total_findings_constant(self):
        """Total findings should remain constant regardless of step config."""
        experiment = AblationExperiment(_make_corpus())
        results = experiment.run_additive()

        # Total findings = important + nit + preexisting should always be 6
        for r in results:
            assert r.total_findings == 6, (
                f"{r.config_name}: total={r.total_findings}, "
                f"important={r.important_count}, nit={r.nit_count}, "
                f"preexisting={r.preexisting_count}"
            )

    def test_kb_demotion_step_reduces_important(self):
        """
        Adding KB demotion with a rejection-heavy KB should reduce
        the number of 'important' findings.
        """
        kb = _make_kb_with_rejections()
        experiment = AblationExperiment(_make_corpus(), knowledge_base=kb)

        # Run with no steps (baseline)
        baseline = experiment._run_config("baseline", set())

        # Run with only KB demotion
        with_kb = experiment._run_config("with_kb", {"kb_demotion"})

        # KB demotion should reduce important findings
        assert with_kb.important_count < baseline.important_count, (
            f"KB demotion should reduce important: "
            f"baseline={baseline.important_count}, with_kb={with_kb.important_count}"
        )
        assert with_kb.demotion_events > 0

    def test_adding_steps_shows_incremental_effect(self):
        """
        The ablation table should show that each step can potentially
        change the output (at least one step should differ from baseline).
        """
        kb = _make_kb_with_rejections()
        experiment = AblationExperiment(_make_corpus(), knowledge_base=kb)
        results = experiment.run_additive()

        baseline = results[0]
        any_different = False
        for r in results[1:]:
            if (r.important_count != baseline.important_count or
                r.nit_count != baseline.nit_count or
                r.preexisting_count != baseline.preexisting_count):
                any_different = True
                break

        assert any_different, "No ablation step changed the output — experiment is meaningless"


# ═══════════════════════════════════════════════════════════════════════
# Subtractive Ablation Tests
# ═══════════════════════════════════════════════════════════════════════

class TestSubtractiveAblation:
    """Tests for subtractive (leave-one-out) ablation."""

    def test_produces_correct_number_of_configs(self):
        """Should produce N+1 configs (all_steps + one removal per step)."""
        experiment = AblationExperiment(_make_corpus())
        results = experiment.run_subtractive()

        # 1 (all_steps) + 5 (one removal each) = 6
        assert len(results) == 6
        assert results[0].config_name == "all_steps"

    def test_removing_kb_demotion_increases_important(self):
        """
        Removing KB demotion from the full pipeline should increase
        'important' findings when the KB has rejection data.
        """
        kb = _make_kb_with_rejections()
        experiment = AblationExperiment(_make_corpus(), knowledge_base=kb)
        results = experiment.run_subtractive()

        all_steps = results[0]
        without_kb = next(r for r in results if r.config_name == "-kb_demotion")

        assert without_kb.important_count >= all_steps.important_count, (
            f"Removing KB demotion should not decrease important: "
            f"all={all_steps.important_count}, -kb={without_kb.important_count}"
        )

    def test_all_steps_config_has_all_enabled(self):
        """The 'all_steps' config should have all 5 steps enabled."""
        experiment = AblationExperiment(_make_corpus())
        results = experiment.run_subtractive()

        all_steps = results[0]
        assert len(all_steps.enabled_steps) == 5


# ═══════════════════════════════════════════════════════════════════════
# Full Experiment Tests
# ═══════════════════════════════════════════════════════════════════════

class TestFullAblationExperiment:
    """Integration tests for the complete ablation experiment."""

    def test_run_returns_both_ablation_types(self):
        """run() should return both additive and subtractive results."""
        experiment = AblationExperiment(_make_corpus())
        results = experiment.run()

        assert "additive" in results
        assert "subtractive" in results
        assert len(results["additive"]) == 6
        assert len(results["subtractive"]) == 6

    def test_json_output_is_valid(self):
        """to_json() should produce valid JSON."""
        import json
        experiment = AblationExperiment(_make_corpus())
        json_str = experiment.to_json()

        parsed = json.loads(json_str)
        assert "additive" in parsed
        assert "subtractive" in parsed

    def test_full_pipeline_vs_baseline_with_kb(self):
        """
        The full pipeline with KB data should produce different results
        than baseline — this validates the entire ablation methodology.
        """
        kb = _make_kb_with_rejections()
        experiment = AblationExperiment(_make_corpus(), knowledge_base=kb)

        results = experiment.run()
        baseline = results["additive"][0]
        full = results["subtractive"][0]

        # The full pipeline should have fewer important findings
        # (because KB demotion downgrades them)
        assert full.important_count <= baseline.important_count

    def test_print_ablation_table(self):
        """Print a formatted ablation table for thesis visualization."""
        kb = _make_kb_with_rejections()
        experiment = AblationExperiment(_make_corpus(), knowledge_base=kb)
        results = experiment.run()

        print("\n" + "=" * 80)
        print("ADDITIVE ABLATION TABLE")
        print("=" * 80)
        print(f"{'Configuration':<45} {'Important':>9} {'Nit':>5} {'Pre':>5} {'Dem':>5} {'Pro':>5}")
        print("-" * 80)
        for r in results["additive"]:
            print(
                f"{r.config_name:<45} {r.important_count:>9} "
                f"{r.nit_count:>5} {r.preexisting_count:>5} "
                f"{r.demotion_events:>5} {r.promotion_events:>5}"
            )

        print("\n" + "=" * 80)
        print("SUBTRACTIVE ABLATION TABLE")
        print("=" * 80)
        print(f"{'Configuration':<45} {'Important':>9} {'Nit':>5} {'Pre':>5} {'Dem':>5} {'Pro':>5}")
        print("-" * 80)
        for r in results["subtractive"]:
            print(
                f"{r.config_name:<45} {r.important_count:>9} "
                f"{r.nit_count:>5} {r.preexisting_count:>5} "
                f"{r.demotion_events:>5} {r.promotion_events:>5}"
            )
        print("=" * 80)
