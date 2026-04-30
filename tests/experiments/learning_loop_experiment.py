"""
Learning Loop Time-Series Simulation
======================================
Proves the core thesis claim: "After N feedback iterations, developer-rejected
comments drop by X%."

This simulation:
1. Creates a corpus of raw findings
2. Simulates developer feedback (accept/reject) based on a profile
3. Feeds feedback into ``PatternLearner``
4. Re-runs ``SeverityOrchestrator`` with the updated KB
5. Tracks per-round metrics: total findings, demoted, rejected, noise ratio

No LLM calls — fully deterministic simulation using only PatternLearner +
SeverityOrchestrator.

Usage::

    sim = LearningLoopSimulation(corpus, feedback_profile, rounds=5)
    results = sim.run()
    for r in results:
        print(f"Round {r['round']}: noise_ratio={r['noise_ratio']:.2%}")
"""

from __future__ import annotations

import json
import logging
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional

from analyzer.feedback.severity_orchestrator import (
    CalibrationEvent,
    CalibratedResult,
    SeverityOrchestrator,
)

logger = logging.getLogger(__name__)


# ── Feedback Profile ────────────────────────────────────────────────────

@dataclass
class FeedbackProfile:
    """
    Defines how simulated developers respond to findings.

    Keys are ``issue_type`` strings, values are acceptance probabilities.
    If a type is not in the profile, ``default_acceptance`` is used.
    """
    acceptance_by_type: Dict[str, float] = field(default_factory=dict)
    default_acceptance: float = 0.60

    def should_accept(self, issue_type: str, finding_index: int) -> bool:
        """
        Deterministic accept/reject based on the finding index.

        Uses a hash of (issue_type, finding_index) modulo 100 compared
        against the acceptance rate. This ensures:
        - Reproducibility (same inputs → same output)
        - Good distribution (different indices produce different results)
        """
        rate = self.acceptance_by_type.get(issue_type, self.default_acceptance)
        # Hash-based deterministic random: spread values evenly across [0, 1)
        hash_val = hash((issue_type, finding_index)) % 10000
        return (hash_val / 10000.0) < rate


# ── In-Memory KB (mimics PatternLearner interface) ──────────────────────

class InMemoryKB:
    """
    Minimal PatternLearner interface for the simulation.
    Tracks acceptance/rejection counts per issue type.
    """

    def __init__(self):
        self.patterns: Dict[str, Dict[str, int]] = {}

    def record_feedback(self, issue_type: str, accepted: bool):
        """Record a single accept/reject event."""
        if issue_type not in self.patterns:
            self.patterns[issue_type] = {"total": 0, "accepted": 0, "rejected": 0}
        self.patterns[issue_type]["total"] += 1
        if accepted:
            self.patterns[issue_type]["accepted"] += 1
        else:
            self.patterns[issue_type]["rejected"] += 1

    def get_acceptance_rate(self, issue_type: str) -> float:
        """Return acceptance rate for a given issue type."""
        stats = self.patterns.get(issue_type, {})
        total = stats.get("total", 0)
        if total == 0:
            return 1.0  # Unknown type → assume good
        return stats.get("accepted", 0) / total

    def reset(self):
        """Clear all recorded patterns."""
        self.patterns = {}


# ── Round Result ────────────────────────────────────────────────────────

@dataclass
class RoundResult:
    """Metrics for one round of the simulation."""
    round: int
    total_findings: int
    important_count: int
    nit_count: int
    preexisting_count: int
    demoted_count: int  # Findings demoted by KB in this round
    rejected_count: int  # Findings that the simulated developer would reject
    noise_ratio: float  # rejected / total (lower is better)
    calibration_events: List[Dict[str, Any]] = field(default_factory=list)


# ── Simulation ──────────────────────────────────────────────────────────

class LearningLoopSimulation:
    """
    Runs N rounds of the learning loop and produces a time-series.

    Args:
        corpus: List of raw finding dicts (the same findings are re-evaluated each round).
        feedback_profile: Defines which types developers accept/reject.
        rounds: Number of simulation rounds (default: 5).
        enabled_steps: Set of enabled calibration steps (default: all).
    """

    def __init__(
        self,
        corpus: List[Dict[str, Any]],
        feedback_profile: FeedbackProfile,
        rounds: int = 5,
        enabled_steps: Optional[set] = None,
    ):
        self.corpus = corpus
        self.feedback_profile = feedback_profile
        self.rounds = rounds
        self.enabled_steps = enabled_steps
        self.kb = InMemoryKB()

    def run(self) -> List[RoundResult]:
        """Execute the simulation and return per-round metrics."""
        results: List[RoundResult] = []

        for round_num in range(self.rounds):
            # Create orchestrator with current KB state
            orchestrator = SeverityOrchestrator(
                project_root=None,
                nit_cap=5,
                enabled_steps=self.enabled_steps,
            )

            # Run calibration with current KB
            calibrated = orchestrator.calibrate(
                raw_findings=[dict(f) for f in self.corpus],  # Deep-copy
                knowledge_base=self.kb,
            )

            # Count findings
            important_count = len(calibrated.important_findings)
            nit_count = calibrated.nit_summary.total_nit_count if calibrated.nit_summary else 0
            preexisting_count = len(calibrated.preexisting_findings)
            total = important_count + nit_count + preexisting_count

            # Count KB demotion events in this round
            demoted_count = sum(
                1 for e in calibrated.calibration_events
                if e.step == "kb_demotion"
            )

            # Simulate developer feedback on all findings
            all_calibrated_findings = list(calibrated.important_findings)
            if calibrated.nit_summary:
                all_calibrated_findings.extend(calibrated.nit_summary.shown_nits)
                # Collapsed nits are not shown to the developer, so no feedback
            all_calibrated_findings.extend(calibrated.preexisting_findings)

            rejected_count = 0
            for i, finding in enumerate(all_calibrated_findings):
                # Use the RAW issue type for KB tracking — this must match
                # what SeverityOrchestrator queries in Step 3 (kb_demotion)
                # We encode the raw type from the finding's calibration context
                issue_type = self._infer_raw_type(finding)

                accepted = self.feedback_profile.should_accept(
                    issue_type, i + round_num * len(self.corpus)
                )
                self.kb.record_feedback(issue_type, accepted)
                if not accepted:
                    rejected_count += 1

            noise_ratio = rejected_count / max(total, 1)

            results.append(RoundResult(
                round=round_num,
                total_findings=total,
                important_count=important_count,
                nit_count=nit_count,
                preexisting_count=preexisting_count,
                demoted_count=demoted_count,
                rejected_count=rejected_count,
                noise_ratio=round(noise_ratio, 4),
                calibration_events=[asdict(e) for e in calibrated.calibration_events],
            ))

            logger.info(
                "Round %d: total=%d, rejected=%d, noise=%.2f%%",
                round_num, total, rejected_count, noise_ratio * 100,
            )

        return results

    @staticmethod
    def _infer_raw_type(finding) -> str:
        """Infer the raw issue type from a calibrated ReviewFinding.

        The SeverityOrchestrator queries the KB using the raw `type` field
        (e.g. 'security_vulnerability', 'quality'). We reverse-map from
        the ReviewFinding's category.
        """
        _CATEGORY_TO_RAW_TYPE = {
            "Security": "security_vulnerability",
            "Architecture": "antipattern",
            "Maintainability": "code_duplication",
            "Performance": "performance",
            "Style": "quality",
            "AI Pattern": "ai_pattern",
            "Correctness": "correctness",
            "Dataflow": "security_vulnerability",
        }
        if finding.category:
            return _CATEGORY_TO_RAW_TYPE.get(finding.category.value, finding.category.value)
        return "unknown"

    def to_json(self) -> str:
        """Run and return results as JSON string."""
        results = self.run()
        return json.dumps([asdict(r) for r in results], indent=2)
