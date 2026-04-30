"""
SeverityOrchestrator
====================
Calibrates raw finding severity using project-specific context.

Decision ladder:
1. Load project config from .intellireview.yml (severity overrides, custom rules)
2. Query PatternLearner acceptance rates — high-rejection findings demote to nit
3. Check dataflow traces — confirmed taint paths promote to important
4. Check DESIGN.md constraints — architectural violations promote to important
5. Apply nit volume cap — collapse >5 nits into a single summary
"""

from __future__ import annotations

import hashlib
import logging
import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

import yaml

from api.schemas.feedback_schemas import (
    AutofixDiff,
    DataflowTrace,
    FindingCategory,
    NitSummary,
    NitSummaryItem,
    ReproductionStep,
    ReviewFinding,
    SeverityLevel,
    TestCase,
)

logger = logging.getLogger(__name__)

# ─── Defaults ─────────────────────────────────────────────────────────

NIT_VOLUME_CAP = 5
REJECTION_RATE_DEMOTION_THRESHOLD = 0.60  # >60% rejection → demote to nit
MIN_SAMPLES_FOR_DEMOTION = 5  # Need at least 5 telemetry samples before demoting


# ─── Mapping raw severity strings → calibrated SeverityLevel ──────────

_RAW_TO_CALIBRATED: Dict[str, SeverityLevel] = {
    "critical": SeverityLevel.important,
    "high": SeverityLevel.important,
    "medium": SeverityLevel.nit,
    "low": SeverityLevel.nit,
    "info": SeverityLevel.preexisting,
    # Orchestrator emoji mappings (from existing Finding model)
    "🔴": SeverityLevel.important,
    "🟡": SeverityLevel.nit,
    "🟣": SeverityLevel.preexisting,
}

_RAW_TYPE_TO_CATEGORY: Dict[str, FindingCategory] = {
    "security_vulnerability": FindingCategory.security,
    "antipattern": FindingCategory.architecture,
    "code_duplication": FindingCategory.maintainability,
    "performance": FindingCategory.performance,
    "quality": FindingCategory.style,
    "ai_pattern": FindingCategory.ai_pattern,
    "correctness": FindingCategory.correctness,
}

# Sensitive sinks for dataflow severity boost
SENSITIVE_SINKS = frozenset({
    "execute", "raw", "query", "eval", "exec", "system", "popen",
    "subprocess", "os.system", "cursor.execute", "db.execute",
    "authenticate", "verify_password", "check_password",
    "open", "write", "unlink", "remove", "rmdir",
    "innerHTML", "document.write", "dangerouslySetInnerHTML",
})


@dataclass
class CalibrationEvent:
    """Records a single demotion/promotion decision for telemetry."""
    finding_id: str
    issue_type: str
    original_severity: str
    calibrated_severity: str
    reason: str
    step: str  # which calibration step triggered this


@dataclass
class CalibratedResult:
    """Output of the SeverityOrchestrator calibration pass."""
    important_findings: List[ReviewFinding] = field(default_factory=list)
    nit_summary: Optional[NitSummary] = None
    preexisting_findings: List[ReviewFinding] = field(default_factory=list)
    calibration_log: List[str] = field(default_factory=list)
    calibration_events: List[CalibrationEvent] = field(default_factory=list)


class SeverityOrchestrator:
    """
    Rules engine that calibrates raw finding severity using project context.

    Usage:
        orchestrator = SeverityOrchestrator(project_root="/path/to/repo")
        result = orchestrator.calibrate(raw_findings, knowledge_base=pattern_learner)
    """

    # All calibration step names (used by enabled_steps for ablation)
    ALL_STEPS = frozenset({
        "config_override",
        "kb_demotion",
        "dataflow_boost",
        "design_constraint",
        "reachability",
    })

    def __init__(
        self,
        project_root: Optional[str] = None,
        nit_cap: int = NIT_VOLUME_CAP,
        enabled_steps: Optional[set] = None,
    ):
        self.project_root = Path(project_root) if project_root else None
        self.nit_cap = nit_cap
        self.enabled_steps = enabled_steps if enabled_steps is not None else set(self.ALL_STEPS)
        self._project_config = self._load_project_config()
        self._design_constraints = self._load_design_constraints()

        from analyzer.feedback.reachability import SemanticReachabilityAnalyzer
        self.reachability_analyzer = SemanticReachabilityAnalyzer(str(self.project_root) if self.project_root else None)

    # ─── Public API ───────────────────────────────────────────────────

    def calibrate(
        self,
        raw_findings: List[Dict[str, Any]],
        knowledge_base: Optional[Any] = None,
        dataflow_traces: Optional[Dict[str, DataflowTrace]] = None,
    ) -> CalibratedResult:
        """
        Run the full calibration pipeline on a list of raw findings.

        Args:
            raw_findings: List of raw issue dicts from the analysis pipeline.
            knowledge_base: A PatternLearner instance for telemetry-based demotion.
            dataflow_traces: Pre-computed dataflow traces keyed by finding ID.

        Returns:
            CalibratedResult with findings sorted into important/nit/preexisting.
        """
        calibrated: List[ReviewFinding] = []
        log: List[str] = []
        events: List[CalibrationEvent] = []

        for raw in raw_findings:
            finding, reason, finding_events = self._calibrate_single(
                raw, knowledge_base, dataflow_traces or {}
            )
            calibrated.append(finding)
            events.extend(finding_events)
            if reason:
                log.append(reason)

        # Sort into buckets
        important = [f for f in calibrated if f.severity == SeverityLevel.important]
        nits_all = [f for f in calibrated if f.severity == SeverityLevel.nit]
        preexisting = [f for f in calibrated if f.severity == SeverityLevel.preexisting]

        # Apply nit volume cap
        nit_summary = self._apply_nit_cap(nits_all)
        if nit_summary and nit_summary.collapsed_nits:
            log.append(
                f"Nit volume cap applied: {len(nit_summary.collapsed_nits)} nits "
                f"collapsed (showing first {len(nit_summary.shown_nits)})"
            )

        return CalibratedResult(
            important_findings=important,
            nit_summary=nit_summary,
            preexisting_findings=preexisting,
            calibration_log=log,
            calibration_events=events,
        )

    # ─── Single Finding Calibration ───────────────────────────────────

    def _calibrate_single(
        self,
        raw: Dict[str, Any],
        knowledge_base: Optional[Any],
        dataflow_traces: Dict[str, DataflowTrace],
    ) -> Tuple[ReviewFinding, Optional[str]]:
        """Calibrate a single raw finding. Returns (ReviewFinding, calibration_reason, events)."""
        finding_id = raw.get("id") or self._generate_finding_id(raw)
        raw_severity = raw.get("severity", "medium")
        raw_type = raw.get("type", "unknown")
        events: List[CalibrationEvent] = []

        # Step 1: Base severity from raw mapping
        severity = _RAW_TO_CALIBRATED.get(raw_severity, SeverityLevel.nit)
        category = _RAW_TYPE_TO_CATEGORY.get(raw_type, FindingCategory.style)
        reason_parts: List[str] = []
        original_severity = severity.value

        # Step 2: Project config severity overrides
        if "config_override" in self.enabled_steps:
            config_severity = self._get_config_severity_override(raw_type)
            if config_severity is not None:
                old_sev = severity
                severity = config_severity
                if old_sev != severity:
                    reason_parts.append(
                        f"Config override: {old_sev.value} → {severity.value}"
                    )
                    events.append(CalibrationEvent(
                        finding_id=finding_id,
                        issue_type=raw_type,
                        original_severity=old_sev.value,
                        calibrated_severity=severity.value,
                        reason=f"Config override: {old_sev.value} → {severity.value}",
                        step="config_override",
                    ))

        # Step 3: Knowledge Base demotion (high rejection rate → demote to nit)
        if "kb_demotion" in self.enabled_steps and knowledge_base and severity == SeverityLevel.important:
            acceptance_rate = knowledge_base.get_acceptance_rate(raw_type)
            stats = knowledge_base.patterns.get(raw_type, {})
            total_samples = stats.get("total", 0)

            if (
                total_samples >= MIN_SAMPLES_FOR_DEMOTION
                and (1 - acceptance_rate) > REJECTION_RATE_DEMOTION_THRESHOLD
            ):
                old_sev = severity
                severity = SeverityLevel.nit
                reason_parts.append(
                    f"KB demotion: {raw_type} has {1 - acceptance_rate:.0%} rejection "
                    f"rate over {total_samples} samples"
                )
                events.append(CalibrationEvent(
                    finding_id=finding_id,
                    issue_type=raw_type,
                    original_severity=old_sev.value,
                    calibrated_severity=severity.value,
                    reason=f"KB demotion: {1 - acceptance_rate:.0%} rejection over {total_samples} samples",
                    step="kb_demotion",
                ))

        # Step 4: Dataflow severity boost
        trace = dataflow_traces.get(finding_id)
        if "dataflow_boost" in self.enabled_steps and trace and not trace.is_sanitized:
            if severity != SeverityLevel.important:
                old_sev = severity
                severity = SeverityLevel.important
                reason_parts.append(
                    f"Dataflow boost: untrusted input reaches sink "
                    f"({trace.source.expression} → {trace.sink.expression})"
                )
                events.append(CalibrationEvent(
                    finding_id=finding_id,
                    issue_type=raw_type,
                    original_severity=old_sev.value,
                    calibrated_severity=severity.value,
                    reason=f"Dataflow boost: {trace.source.expression} → {trace.sink.expression}",
                    step="dataflow_boost",
                ))

        # Step 5: DESIGN.md constraint violation boost
        design_violation = None
        if "design_constraint" in self.enabled_steps:
            design_violation = self._check_design_constraints(raw)
            if design_violation:
                if severity != SeverityLevel.important:
                    old_sev = severity
                    severity = SeverityLevel.important
                    reason_parts.append(
                        f"Architecture violation: {design_violation}"
                    )
                    events.append(CalibrationEvent(
                        finding_id=finding_id,
                        issue_type=raw_type,
                        original_severity=old_sev.value,
                        calibrated_severity=severity.value,
                        reason=f"Architecture violation: {design_violation}",
                        step="design_constraint",
                    ))

        # Step 6: Semantic Reachability analysis (demotion for unreachable findings)
        if "reachability" in self.enabled_steps and severity == SeverityLevel.important:
            temp_finding = ReviewFinding(
                id=finding_id,
                severity=severity,
                category=category,
                title=self._build_title(raw, category),
                narrative="temp",
                file_path=raw.get("file_path", raw.get("filename", "unknown")),
                dataflow_trace=trace,
                evidence=None # we bypass here temporarily to avoid evidence generation error
            )
            is_reachable = self.reachability_analyzer.evaluate_reachability(temp_finding)
            if not is_reachable:
                old_sev = severity
                severity = SeverityLevel.preexisting
                reason_parts.append("Reachability check: 🟢 UNREACHABLE from external entry point. Demoted to Preexisting.")
                events.append(CalibrationEvent(
                    finding_id=finding_id,
                    issue_type=raw_type,
                    original_severity=old_sev.value,
                    calibrated_severity=severity.value,
                    reason="Unreachable from entry points",
                    step="reachability",
                ))

        # Build the calibrated finding
        calibration_reason = "; ".join(reason_parts) if reason_parts else None

        finding = ReviewFinding(
            id=finding_id,
            severity=severity,
            category=category,
            title=self._build_title(raw, category),
            narrative=self._build_narrative(raw),
            file_path=raw.get("file_path", raw.get("filename", "unknown")),
            line=raw.get("line", 0),
            autofix=self._build_autofix(raw),
            evidence=self._build_evidence(raw, severity),
            dataflow_trace=trace,
            cwe=raw.get("cwe"),
            owasp=raw.get("owasp"),
            reference_url=raw.get("reference_url"),
            design_constraint=design_violation,
            confidence=raw.get("confidence", 0.8),
            raw_severity=raw_severity,
            calibration_reason=calibration_reason,
        )

        return finding, calibration_reason, events

    # ─── Nit Volume Cap ───────────────────────────────────────────────

    def _apply_nit_cap(self, nits: List[ReviewFinding]) -> Optional[NitSummary]:
        """If more than `nit_cap` nits, collapse extras into a summary."""
        if not nits:
            return None

        if len(nits) <= self.nit_cap:
            return NitSummary(
                total_nit_count=len(nits),
                shown_nits=nits,
                collapsed_nits=[],
                collapse_reason="All nits shown (within cap)",
            )

        shown = nits[: self.nit_cap]
        collapsed = [
            NitSummaryItem(
                title=n.title,
                file_path=n.file_path,
                line=n.line,
                category=n.category,
            )
            for n in nits[self.nit_cap :]
        ]

        return NitSummary(
            total_nit_count=len(nits),
            shown_nits=shown,
            collapsed_nits=collapsed,
            collapse_reason=(
                f"Collapsed to reduce notification fatigue "
                f"(>{self.nit_cap} nits detected, showing first {self.nit_cap})"
            ),
        )

    # ─── Config Loaders ──────────────────────────────────────────────

    def _load_project_config(self) -> Dict[str, Any]:
        """Load .intellireview.yml from the project root."""
        if not self.project_root:
            return {}

        config_path = self.project_root / ".intellireview.yml"
        if not config_path.exists():
            return {}

        try:
            with open(config_path, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception as e:
            logger.warning(f"Failed to load .intellireview.yml: {e}")
            return {}

    def _load_design_constraints(self) -> List[str]:
        """Load architectural constraints from DESIGN.md."""
        if not self.project_root:
            return []

        design_path = self.project_root / "DESIGN.md"
        if not design_path.exists():
            return []

        try:
            content = design_path.read_text(encoding="utf-8", errors="replace")
            # Extract constraint lines (lines starting with "- CONSTRAINT:" or similar)
            constraints = []
            in_constraints_section = False
            for line in content.split("\n"):
                lower = line.lower().strip()
                if "constraint" in lower and lower.startswith("#"):
                    in_constraints_section = True
                    continue
                if in_constraints_section:
                    if line.startswith("#"):
                        in_constraints_section = False
                        continue
                    stripped = line.strip()
                    if stripped.startswith("- ") or stripped.startswith("* "):
                        constraints.append(stripped[2:].strip())
            return constraints
        except Exception as e:
            logger.warning(f"Failed to load DESIGN.md constraints: {e}")
            return []

    def _get_config_severity_override(self, issue_type: str) -> Optional[SeverityLevel]:
        """Check if .intellireview.yml has a severity override for this issue type."""
        rules = self._project_config.get("rules", [])
        if not isinstance(rules, list):
            return None

        for rule in rules:
            if not isinstance(rule, dict):
                continue
            rule_id = rule.get("id", "")
            if rule_id == issue_type:
                raw_sev = rule.get("severity", "").lower()
                return _RAW_TO_CALIBRATED.get(raw_sev)

        return None

    def _check_design_constraints(self, raw: Dict[str, Any]) -> Optional[str]:
        """Check if a finding violates a known DESIGN.md constraint."""
        if not self._design_constraints:
            return None

        message = (raw.get("message", "") + " " + raw.get("suggestion", "")).lower()

        for constraint in self._design_constraints:
            # Simple keyword match — checks if the constraint topic appears in the finding
            keywords = [w for w in constraint.lower().split() if len(w) > 3]
            matches = sum(1 for kw in keywords if kw in message)
            if matches >= 2:  # At least 2 keyword overlaps
                return constraint

        return None

    # ─── Builders ─────────────────────────────────────────────────────

    @staticmethod
    def _generate_finding_id(raw: Dict[str, Any]) -> str:
        """Generate a deterministic ID for a finding."""
        key = f"{raw.get('type', '')}:{raw.get('line', 0)}:{raw.get('message', '')}"
        return hashlib.sha256(key.encode()).hexdigest()[:12]

    @staticmethod
    def _build_title(raw: Dict[str, Any], category: FindingCategory) -> str:
        """Build a human-readable title for the finding."""
        msg = raw.get("message", "Issue detected")
        # Truncate to first sentence or 80 chars
        first_sentence = msg.split(".")[0].strip()
        if len(first_sentence) > 80:
            first_sentence = first_sentence[:77] + "..."
        return f"{category.value}: {first_sentence}"

    @staticmethod
    def _build_narrative(raw: Dict[str, Any]) -> str:
        """
        Build the 'Why' narrative focusing on system behavior and impact,
        not author intent.
        """
        message = raw.get("message", "")
        suggestion = raw.get("suggestion", "")
        cwe = raw.get("cwe", "")

        narrative_parts = []

        if message:
            # Reframe from "you did X" to "the system does X"
            narrative_parts.append(message)

        if suggestion:
            narrative_parts.append(f"**Impact:** {suggestion}")

        if cwe:
            narrative_parts.append(f"**Classification:** {cwe}")

        return "\n\n".join(narrative_parts) if narrative_parts else "Issue detected."

    @staticmethod
    def _build_autofix(raw: Dict[str, Any]) -> Optional[AutofixDiff]:
        """Build an AutofixDiff from raw finding data if available."""
        suggestion = raw.get("suggestion", "")
        quick_fix = raw.get("quick_fix", "")
        diff_str = raw.get("suggested_fix_diff", "")

        if diff_str:
            line = raw.get("line", 1)
            return AutofixDiff(
                before="(see original code)",
                after="(see diff)",
                unified_diff=diff_str,
                start_line=line,
                end_line=line,
            )

        if quick_fix:
            line = raw.get("line", 1)
            return AutofixDiff(
                before="(see original code)",
                after=quick_fix,
                unified_diff=f"- (original)\n+ {quick_fix}",
                start_line=line,
                end_line=line,
            )

        return None

    @staticmethod
    def _build_evidence(
        raw: Dict[str, Any], severity: SeverityLevel
    ) -> Optional[ReproductionStep]:
        """Build evidence for important findings. Returns None for nits."""
        if severity != SeverityLevel.important:
            return None

        cwe = raw.get("cwe", "")
        message = raw.get("message", "")
        issue_type = raw.get("type", "")

        # Generate context-aware reproduction step based on finding type
        if "sql" in message.lower() or "injection" in message.lower() or cwe == "CWE-89":
            return ReproductionStep(
                title="SQL Injection Verification",
                payload="Input: `' OR 1=1 --` in the affected parameter",
                expected="HTTP 400 or parameterized query prevents injection",
                actual="Query executes with injected SQL, potentially dumping table data",
            )
        elif "xss" in message.lower() or cwe == "CWE-79":
            return ReproductionStep(
                title="XSS Payload Verification",
                payload='Input: `<script>alert("xss")</script>` in the affected field',
                expected="Input is sanitized or escaped before rendering",
                actual="Script tag is rendered in the DOM, executing arbitrary JavaScript",
            )
        elif "eval" in message.lower() or cwe == "CWE-94":
            return ReproductionStep(
                title="Code Injection Verification",
                payload="Input: `__import__('os').system('id')` or equivalent",
                expected="Input is rejected or safely parsed without execution",
                actual="Arbitrary code execution via eval()/exec()",
            )
        elif "secret" in message.lower() or "password" in message.lower() or cwe == "CWE-798":
            return ReproductionStep(
                title="Hardcoded Secret Verification",
                payload="Run: `grep -rn 'password\\|api_key\\|secret' <file>`",
                expected="Secrets loaded from environment variables or vault",
                actual="Credentials are committed in plaintext to version control",
            )
        else:
            return ReproductionStep(
                title=f"Verification for {issue_type}",
                payload=f"Trigger the code path at line {raw.get('line', '?')}",
                expected="No vulnerability or defect present",
                actual=message,
            )
