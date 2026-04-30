"""
Ablation Study Experiment
==========================
Measures the incremental contribution of each calibration step in the
SeverityOrchestrator by toggling them on/off and measuring the output.

This produces the data for the thesis ablation table:
    "Table Y — Incremental contribution of each calibration step."

Methodology:
    1. Start with NO calibration steps (baseline)
    2. Add each step one at a time (additive ablation)
    3. Also test removing each step one at a time (subtractive ablation)
    4. Measure metrics: important_count, nit_count, preexisting_count,
       demotion_events, promotion_events

Usage::

    experiment = AblationExperiment(corpus, knowledge_base, dataflow_traces)
    results = experiment.run()
    for config_name, metrics in results.items():
        print(f"{config_name}: {metrics}")
"""

from __future__ import annotations

import json
from dataclasses import dataclass, field, asdict
from typing import Any, Dict, List, Optional, Set

from analyzer.feedback.severity_orchestrator import (
    CalibrationEvent,
    CalibratedResult,
    SeverityOrchestrator,
)


@dataclass
class AblationMetrics:
    """Metrics collected for a single ablation configuration."""
    config_name: str
    enabled_steps: List[str]
    total_findings: int
    important_count: int
    nit_count: int
    preexisting_count: int
    demotion_events: int  # Severity was lowered
    promotion_events: int  # Severity was raised
    calibration_events: List[Dict[str, Any]] = field(default_factory=list)


class AblationExperiment:
    """
    Runs additive and subtractive ablation experiments on the
    SeverityOrchestrator calibration pipeline.

    Args:
        corpus: List of raw finding dicts.
        knowledge_base: A KB instance (or InMemoryKB) for KB demotion tests.
        dataflow_traces: Pre-computed dataflow traces for dataflow boost tests.
    """

    # The canonical step ordering (matches the orchestrator's pipeline order)
    STEP_ORDER = [
        "config_override",
        "kb_demotion",
        "dataflow_boost",
        "design_constraint",
        "reachability",
    ]

    def __init__(
        self,
        corpus: List[Dict[str, Any]],
        knowledge_base: Optional[Any] = None,
        dataflow_traces: Optional[Dict] = None,
    ):
        self.corpus = corpus
        self.knowledge_base = knowledge_base
        self.dataflow_traces = dataflow_traces or {}

    def _run_config(
        self,
        config_name: str,
        enabled_steps: Set[str],
    ) -> AblationMetrics:
        """Run the orchestrator with a specific set of enabled steps."""
        orchestrator = SeverityOrchestrator(
            project_root=None,
            nit_cap=100,  # High cap to avoid collapsing nits
            enabled_steps=enabled_steps,
        )

        result = orchestrator.calibrate(
            raw_findings=[dict(f) for f in self.corpus],
            knowledge_base=self.knowledge_base,
            dataflow_traces=self.dataflow_traces,
        )

        important_count = len(result.important_findings)
        nit_count = result.nit_summary.total_nit_count if result.nit_summary else 0
        preexisting_count = len(result.preexisting_findings)

        # Count demotion vs. promotion events
        demotion_events = 0
        promotion_events = 0
        severity_rank = {"important": 3, "nit": 2, "preexisting": 1}
        for event in result.calibration_events:
            orig_rank = severity_rank.get(event.original_severity, 2)
            cal_rank = severity_rank.get(event.calibrated_severity, 2)
            if cal_rank < orig_rank:
                demotion_events += 1
            elif cal_rank > orig_rank:
                promotion_events += 1

        return AblationMetrics(
            config_name=config_name,
            enabled_steps=sorted(enabled_steps),
            total_findings=important_count + nit_count + preexisting_count,
            important_count=important_count,
            nit_count=nit_count,
            preexisting_count=preexisting_count,
            demotion_events=demotion_events,
            promotion_events=promotion_events,
            calibration_events=[asdict(e) for e in result.calibration_events],
        )

    def run_additive(self) -> List[AblationMetrics]:
        """
        Additive ablation: start with NO steps, then add one at a time.

        Produces N+1 configurations:
            - "baseline" (no steps)
            - "+config_override"
            - "+config_override+kb_demotion"
            - ...
            - "all_steps"
        """
        results = []

        # Baseline: no steps enabled
        results.append(self._run_config("baseline", set()))

        # Add steps one at a time
        current_steps: Set[str] = set()
        for step in self.STEP_ORDER:
            current_steps.add(step)
            config_name = "+" + "+".join(sorted(current_steps))
            results.append(self._run_config(config_name, set(current_steps)))

        return results

    def run_subtractive(self) -> List[AblationMetrics]:
        """
        Subtractive ablation: start with ALL steps, then remove one at a time.

        Produces N+1 configurations:
            - "all_steps"
            - "-config_override"
            - "-kb_demotion"
            - ...
            - "none"
        """
        all_steps = set(self.STEP_ORDER)
        results = []

        # Full pipeline
        results.append(self._run_config("all_steps", all_steps))

        # Remove each step individually
        for step in self.STEP_ORDER:
            remaining = all_steps - {step}
            config_name = f"-{step}"
            results.append(self._run_config(config_name, remaining))

        return results

    def run(self) -> Dict[str, List[AblationMetrics]]:
        """Run both additive and subtractive ablation."""
        return {
            "additive": self.run_additive(),
            "subtractive": self.run_subtractive(),
        }

    def to_json(self) -> str:
        """Run and return as JSON."""
        results = self.run()
        return json.dumps(
            {k: [asdict(m) for m in v] for k, v in results.items()},
            indent=2,
        )
