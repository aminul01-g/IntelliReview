"""
Confidence Router
==================
Classifies raw findings as *conclusive* (skip LLM) or *ambiguous* (needs LLM
review), enabling the thesis experiment: "What's the optimal split between
deterministic analysis and agentic LLM review?"

The router assigns a ``confidence`` score to each finding based on objective
signals (detector source, CWE presence, dataflow evidence, pattern match
specificity).  Findings above ``conclusive_threshold`` are routed directly
to the SeverityOrchestrator without LLM cost.

Usage::

    router = ConfidenceRouter(conclusive_threshold=0.85)
    conclusive, needs_llm = router.route(static_findings)
    # Send only `needs_llm` to PRReviewOrchestrator

Thesis experiment::

    sweep = ThresholdSweepExperiment(labeled_data)
    results = sweep.run()  # produces Pareto frontier data
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any, Dict, List, Tuple

logger = logging.getLogger(__name__)


# ── Confidence score heuristics ─────────────────────────────────────────

# Detector types that produce inherently high-confidence findings
_HIGH_CONFIDENCE_TYPES = frozenset({
    "security_vulnerability",   # CWE-matched patterns
    "custom_rule",              # User-defined regex rules
    "code_duplication",         # Algorithmic duplicate detection
})

# Detector types that are inherently ambiguous and benefit from LLM review
_LOW_CONFIDENCE_TYPES = frozenset({
    "ai_over_engineering",      # Subjective judgment
    "ai_inconsistency",         # Context-dependent
    "antipattern",              # Some need architectural context
})

# CWE IDs with well-understood remediation (high confidence)
_HIGH_CONFIDENCE_CWES = frozenset({
    "CWE-89",   # SQL Injection
    "CWE-79",   # XSS
    "CWE-78",   # OS Command Injection
    "CWE-94",   # Code Injection
    "CWE-798",  # Hardcoded Credentials
    "CWE-200",  # Information Exposure
    "CWE-22",   # Path Traversal
    "CWE-502",  # Deserialization
})


def compute_finding_confidence(finding: Dict[str, Any]) -> float:
    """
    Assign a confidence score (0.0–1.0) to a single raw finding based on
    deterministic signals.

    Scoring rubric:
        +0.35  — finding has a CWE classification
        +0.25  — finding type is in high-confidence detector set
        +0.15  — finding has a ``suggested_fix_diff`` (concrete fix)
        +0.10  — finding has a specific line number (not file-wide)
        +0.10  — finding has a ``reference_url``
        +0.05  — base score for every finding
        −0.15  — finding type is in low-confidence set
    """
    score = 0.05  # Base

    raw_type = finding.get("type", "")
    cwe = finding.get("cwe", "")

    # CWE classification → high signal
    if cwe:
        score += 0.35
        if cwe in _HIGH_CONFIDENCE_CWES:
            score += 0.05  # Extra for well-known patterns

    # Detector type
    # Check if the type starts with "custom_rule:" prefix
    effective_type = raw_type.split(":")[0] if ":" in raw_type else raw_type
    if effective_type in _HIGH_CONFIDENCE_TYPES:
        score += 0.25
    elif effective_type in _LOW_CONFIDENCE_TYPES:
        score -= 0.15

    # Concrete fix available
    if finding.get("suggested_fix_diff"):
        score += 0.15
    elif finding.get("quick_fix"):
        score += 0.10

    # Specific line number (not file-wide L0 or L1)
    line = finding.get("line", 0)
    if line > 1:
        score += 0.10

    # Reference URL → well-documented issue
    if finding.get("reference_url"):
        score += 0.10

    return max(0.0, min(1.0, score))


# ── Router ──────────────────────────────────────────────────────────────

@dataclass
class RoutingResult:
    """Output of the ConfidenceRouter."""
    conclusive: List[Dict[str, Any]] = field(default_factory=list)
    needs_llm: List[Dict[str, Any]] = field(default_factory=list)
    routing_log: List[str] = field(default_factory=list)


class ConfidenceRouter:
    """
    Routes findings to either deterministic-only or LLM-assisted processing
    based on a confidence threshold.

    Args:
        conclusive_threshold: Findings with confidence ≥ this skip the LLM.
        ambiguous_threshold: Findings with confidence < this always go to LLM.
            Findings between ambiguous and conclusive thresholds are borderline
            and routed to LLM for review.
    """

    def __init__(
        self,
        conclusive_threshold: float = 0.85,
        ambiguous_threshold: float = 0.50,
    ):
        if not (0.0 <= ambiguous_threshold <= conclusive_threshold <= 1.0):
            raise ValueError(
                f"Thresholds must satisfy 0 ≤ ambiguous ({ambiguous_threshold}) "
                f"≤ conclusive ({conclusive_threshold}) ≤ 1"
            )
        self.conclusive_threshold = conclusive_threshold
        self.ambiguous_threshold = ambiguous_threshold

    def route(
        self, static_findings: List[Dict[str, Any]]
    ) -> RoutingResult:
        """
        Classify each finding and route to the appropriate bucket.

        Returns a ``RoutingResult`` with ``conclusive`` and ``needs_llm`` lists.
        Each finding in both lists gets an injected ``_routing_confidence`` key.
        """
        result = RoutingResult()

        for finding in static_findings:
            confidence = compute_finding_confidence(finding)
            finding["_routing_confidence"] = round(confidence, 3)

            if confidence >= self.conclusive_threshold:
                result.conclusive.append(finding)
                result.routing_log.append(
                    f"CONCLUSIVE ({confidence:.2f}): "
                    f"{finding.get('type', '?')} at L{finding.get('line', '?')}"
                )
            else:
                result.needs_llm.append(finding)
                result.routing_log.append(
                    f"→ LLM ({confidence:.2f}): "
                    f"{finding.get('type', '?')} at L{finding.get('line', '?')}"
                )

        logger.info(
            "ConfidenceRouter: %d conclusive, %d → LLM (threshold=%.2f)",
            len(result.conclusive),
            len(result.needs_llm),
            self.conclusive_threshold,
        )
        return result


# ── Threshold Sweep Experiment ──────────────────────────────────────────

@dataclass
class SweepPoint:
    """One data point in the threshold sweep."""
    threshold: float
    precision: float
    recall: float
    f1: float
    conclusive_count: int
    llm_count: int
    simulated_cost: float  # Proportional to llm_count


class ThresholdSweepExperiment:
    """
    Sweeps the conclusive threshold from 0.0 to 1.0 and measures
    precision, recall, and simulated cost at each point.

    This produces the Pareto frontier data for Figure 1 of the thesis.

    Args:
        labeled_data: A list of dicts, each with the raw finding fields
            plus a ``_human_valid`` bool key indicating whether a human
            would agree the finding is real.
        step: Sweep increment (default 0.05).
        llm_cost_per_finding: Simulated cost per LLM-reviewed finding.
    """

    def __init__(
        self,
        labeled_data: List[Dict[str, Any]],
        step: float = 0.05,
        llm_cost_per_finding: float = 0.02,
    ):
        self.labeled_data = labeled_data
        self.step = step
        self.llm_cost_per_finding = llm_cost_per_finding

    def run(self) -> List[SweepPoint]:
        """Execute the sweep and return results at each threshold."""
        results: List[SweepPoint] = []
        threshold = 0.0

        while threshold <= 1.0 + 1e-9:
            router = ConfidenceRouter(
                conclusive_threshold=min(threshold, 1.0),
                ambiguous_threshold=0.0,  # Everything below threshold → LLM
            )
            routing = router.route(
                # Deep-copy to avoid mutating originals
                [dict(f) for f in self.labeled_data]
            )

            # Conclusive findings are accepted as-is (no LLM correction)
            # LLM findings are assumed to be perfectly corrected by the LLM
            # So: precision = TP / (TP + FP among conclusive)
            #     recall = TP / (all actual positives)

            conclusive_tp = sum(
                1 for f in routing.conclusive if f.get("_human_valid", False)
            )
            conclusive_fp = sum(
                1 for f in routing.conclusive if not f.get("_human_valid", False)
            )
            # LLM-reviewed findings: assume the LLM corrects all FPs and keeps TPs
            llm_tp = sum(
                1 for f in routing.needs_llm if f.get("_human_valid", False)
            )

            total_real_positives = sum(
                1 for f in self.labeled_data if f.get("_human_valid", False)
            )
            total_predicted = conclusive_tp + conclusive_fp + llm_tp

            precision = (
                (conclusive_tp + llm_tp) / max(total_predicted, 1)
            )
            recall = (
                (conclusive_tp + llm_tp) / max(total_real_positives, 1)
            )
            f1 = (
                2 * precision * recall / max(precision + recall, 1e-9)
            )
            simulated_cost = len(routing.needs_llm) * self.llm_cost_per_finding

            results.append(SweepPoint(
                threshold=round(threshold, 2),
                precision=round(precision, 4),
                recall=round(recall, 4),
                f1=round(f1, 4),
                conclusive_count=len(routing.conclusive),
                llm_count=len(routing.needs_llm),
                simulated_cost=round(simulated_cost, 4),
            ))

            threshold += self.step

        return results

    def to_dict_list(self) -> List[Dict[str, Any]]:
        """Run and return as a list of dicts (for JSON serialization)."""
        from dataclasses import asdict
        return [asdict(p) for p in self.run()]
