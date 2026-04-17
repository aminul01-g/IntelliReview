"""
FeedbackGenerator Pydantic Schemas
===================================
Strict, validated models for the entire feedback pipeline — from raw AI findings
through severity calibration to the final structured PR review comment.

These schemas serve as the single source of truth for the JSON output contract
of the IntelliReview analysis agents.
"""

from __future__ import annotations

from datetime import datetime, timezone
from enum import Enum
from typing import Any, Dict, List, Literal, Optional, Union

from pydantic import BaseModel, Field, model_validator


# ─── Enums ────────────────────────────────────────────────────────────

class SeverityLevel(str, Enum):
    """Calibrated severity level after SeverityOrchestrator processing."""
    important = "important"    # 🔴 Block merge
    nit = "nit"                # 🟡 Style / polish
    preexisting = "preexisting"  # 🟣 Legacy debt


SEVERITY_MARKERS: Dict[SeverityLevel, str] = {
    SeverityLevel.important: "🔴",
    SeverityLevel.nit: "🟡",
    SeverityLevel.preexisting: "🟣",
}

SEVERITY_LABELS: Dict[SeverityLevel, str] = {
    SeverityLevel.important: "Important: Block merge",
    SeverityLevel.nit: "Nit: Style/Polish",
    SeverityLevel.preexisting: "Pre-existing: Legacy debt",
}


class FindingCategory(str, Enum):
    """Category of a code review finding."""
    security = "Security"
    performance = "Performance"
    architecture = "Architecture"
    correctness = "Correctness"
    style = "Style"
    maintainability = "Maintainability"
    dataflow = "Dataflow"
    ai_pattern = "AI Pattern"


# ─── Evidence Models ──────────────────────────────────────────────────

class TestCase(BaseModel):
    """A test case that demonstrates the failure mode of a finding."""
    title: str = Field(..., description="Descriptive name for the test case")
    setup: Optional[str] = Field(None, description="Test setup / preconditions")
    input_payload: str = Field(..., description="The specific input that triggers the failure")
    expected_behavior: str = Field(..., description="What *should* happen")
    actual_behavior: str = Field(..., description="What *actually* happens (the bug)")
    language: str = Field(default="python", description="Language for the test snippet")
    code_snippet: Optional[str] = Field(None, description="Optional runnable test code")


class ReproductionStep(BaseModel):
    """A step-by-step reproduction of a failure mode."""
    title: str = Field(..., description="A short name for the reproduction scenario")
    payload: str = Field(..., description="The exact HTTP payload, CLI command, or input")
    expected: str = Field(..., description="Expected system behavior")
    actual: str = Field(..., description="Actual observed behavior (the defect)")
    curl_command: Optional[str] = Field(None, description="Optional cURL command for HTTP-based repros")


# Union type for evidence — at least one is required for Important findings
EvidencePayload = Union[TestCase, ReproductionStep]


# ─── Autofix Model ───────────────────────────────────────────────────

class AutofixDiff(BaseModel):
    """A structured diff block that can be applied with a single click."""
    before: str = Field(..., description="The original code lines being replaced")
    after: str = Field(..., description="The replacement code lines")
    unified_diff: str = Field(..., description="Full unified diff string (--- a/ +++ b/ format)")
    start_line: int = Field(..., ge=1, description="Starting line number in the original file")
    end_line: int = Field(..., ge=1, description="Ending line number in the original file")


# ─── Dataflow Trace ──────────────────────────────────────────────────

class DataflowNode(BaseModel):
    """A single node in a dataflow trace."""
    expression: str = Field(..., description="The code expression at this point")
    file_path: str = Field(..., description="File where this node occurs")
    line: int = Field(..., ge=0, description="Line number")
    node_type: Literal["source", "transform", "sink"] = Field(
        ..., description="Whether this is a source (untrusted input), transform, or sink (sensitive op)"
    )
    is_tainted: bool = Field(default=True, description="Whether the value carries taint at this node")


class DataflowTrace(BaseModel):
    """A full source-to-sink dataflow trace with taint markers."""
    source: DataflowNode = Field(..., description="Where untrusted data enters")
    transforms: List[DataflowNode] = Field(default_factory=list, description="Intermediate transforms")
    sink: DataflowNode = Field(..., description="Where the data reaches a sensitive operation")
    is_sanitized: bool = Field(default=False, description="Whether a sanitizer was detected in the path")
    summary: str = Field(..., description="Human-readable one-line summary of the trace")


# ─── Core Finding Model ──────────────────────────────────────────────

class ReviewFinding(BaseModel):
    """
    A single, fully-enriched review finding ready for PR comment rendering.

    The 'Why' is the `narrative` field — it focuses on the system's behavior
    and potential impact, not the author's intent.
    """
    id: str = Field(..., description="Deterministic finding ID (hash-based)")
    severity: SeverityLevel = Field(..., description="Calibrated severity level")
    category: FindingCategory = Field(..., description="Finding category")
    title: str = Field(..., description="Short finding title for the header")

    # The 'Why' — focus on system behavior and impact
    narrative: str = Field(
        ...,
        description=(
            "A narrative description focusing on the system's behavior and "
            "potential impact rather than the author's intent"
        ),
    )

    file_path: str = Field(..., description="File where the finding occurs")
    line: int = Field(default=0, ge=0, description="Primary line number (0 = file-wide)")
    end_line: Optional[int] = Field(None, description="End line for multi-line findings")

    # Actionable Fix
    autofix: Optional[AutofixDiff] = Field(None, description="Structured diff block for one-click apply")

    # Evidence Mandate — required for 'important' findings
    evidence: Optional[EvidencePayload] = Field(
        None,
        description="Test case or reproduction step (REQUIRED for Important findings)",
    )

    # Dataflow context
    dataflow_trace: Optional[DataflowTrace] = Field(
        None, description="Dataflow trace if untrusted input reaches a sensitive sink"
    )

    # References
    cwe: Optional[str] = Field(None, description="CWE identifier (e.g., CWE-89)")
    owasp: Optional[str] = Field(None, description="OWASP reference (e.g., A03:2021)")
    reference_url: Optional[str] = Field(None, description="Link to official documentation")
    design_constraint: Optional[str] = Field(
        None, description="Architectural constraint from DESIGN.md that this finding violates"
    )

    # Metadata
    confidence: float = Field(default=0.8, ge=0.0, le=1.0, description="Confidence score 0–1")
    raw_severity: Optional[str] = Field(
        None, description="Original severity before calibration (e.g., 'critical', 'high', 'medium')"
    )
    calibration_reason: Optional[str] = Field(
        None, description="Why the severity was changed during calibration"
    )

    @model_validator(mode="after")
    def validate_evidence_mandate(self) -> "ReviewFinding":
        """Enforce the Evidence Mandate: Important findings MUST have evidence."""
        if self.severity == SeverityLevel.important and self.evidence is None:
            # Instead of hard-failing, we generate a placeholder reproduction step
            # so the pipeline never blocks. The verification walkthrough will flag this.
            self.evidence = ReproductionStep(
                title="[Auto-generated] Verification pending",
                payload="Manual verification required",
                expected="No vulnerability present",
                actual="Potential vulnerability detected by static analysis",
            )
            self.calibration_reason = (
                (self.calibration_reason or "")
                + " [Evidence auto-generated — manual verification recommended]"
            ).strip()
        return self


# ─── Nit Summary ─────────────────────────────────────────────────────

class NitSummaryItem(BaseModel):
    """A single collapsed nit entry in the summary table."""
    title: str
    file_path: str
    line: int
    category: FindingCategory


class NitSummary(BaseModel):
    """
    When >5 nits are found, they collapse into this summary to avoid
    notification fatigue.
    """
    total_nit_count: int = Field(..., ge=0)
    shown_nits: List[ReviewFinding] = Field(
        default_factory=list,
        description="The first 5 nits shown in full detail",
    )
    collapsed_nits: List[NitSummaryItem] = Field(
        default_factory=list,
        description="Remaining nits collapsed into a summary table",
    )
    collapse_reason: str = Field(
        default="Collapsed to reduce notification fatigue (>5 nits detected)",
    )


# ─── Verification Walkthrough ────────────────────────────────────────

class VerificationEntry(BaseModel):
    """How a single finding was verified by the agent."""
    finding_id: str
    finding_title: str
    verification_method: Literal[
        "test_case", "reproduction_step", "dataflow_trace",
        "ast_analysis", "pattern_match", "knowledge_base", "unverified"
    ]
    verification_summary: str = Field(..., description="Brief explanation of how this was verified")
    passed: bool = Field(default=True, description="Whether the verification confirmed the finding")


class VerificationWalkthrough(BaseModel):
    """
    Artifact summarizing how the agent verified its own findings before posting.
    Generated after every review.
    """
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_findings: int
    important_count: int
    nit_count: int
    preexisting_count: int
    entries: List[VerificationEntry] = Field(default_factory=list)
    dataflow_traces_checked: int = Field(default=0)
    knowledge_base_rules_applied: List[str] = Field(default_factory=list)
    nits_collapsed: int = Field(default=0)
    collapse_reason: Optional[str] = None


# ─── Top-Level PR Review Comment ─────────────────────────────────────

class PRReviewComment(BaseModel):
    """
    The complete, structured output of the FeedbackGenerator for a single PR.

    This is the top-level object serialized to JSON and/or rendered to Markdown
    for posting as a GitHub PR comment.
    """
    review_id: str = Field(..., description="Unique review identifier")
    repository: str = Field(..., description="Repository full name (owner/repo)")
    pr_number: int = Field(..., ge=1, description="Pull request number")
    generated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))

    # Findings
    important_findings: List[ReviewFinding] = Field(default_factory=list)
    nit_findings: Optional[NitSummary] = Field(None)
    preexisting_findings: List[ReviewFinding] = Field(default_factory=list)

    # Summary stats
    total_findings: int = Field(default=0)
    files_reviewed: int = Field(default=0)
    verdict: Literal["pass", "warn", "fail"] = Field(default="pass")

    # Verification
    verification_walkthrough: Optional[VerificationWalkthrough] = Field(None)

    @model_validator(mode="after")
    def compute_totals(self) -> "PRReviewComment":
        """Auto-compute total_findings from the sub-lists."""
        important = len(self.important_findings)
        nit = (
            self.nit_findings.total_nit_count
            if self.nit_findings
            else 0
        )
        preexisting = len(self.preexisting_findings)
        self.total_findings = important + nit + preexisting
        return self


# ─── Interactive Feedback (Human Reviewer → Knowledge Base) ──────────

class ReviewerFeedbackRequest(BaseModel):
    """
    Schema for human reviewers to interact with the agent's findings.

    Actions:
    - 'request_better_fix': Ask the agent for an improved autofix
    - 'ignore_pattern': Mark a finding pattern for future suppression
    """
    finding_id: str = Field(..., description="ID of the finding being responded to")
    action: Literal["request_better_fix", "ignore_pattern"] = Field(
        ..., description="The feedback action"
    )
    comment: Optional[str] = Field(
        None, description="Free-text comment from the reviewer"
    )
    repository: str = Field(..., description="Repository full name")
    pr_number: int = Field(..., ge=1)


class ReviewerFeedbackResponse(BaseModel):
    """Response after processing reviewer feedback."""
    status: str = Field(default="accepted")
    finding_id: str
    action_taken: str
    knowledge_base_updated: bool = Field(default=False)
    updated_fix: Optional[AutofixDiff] = Field(
        None, description="Improved autofix if 'request_better_fix' was the action"
    )
    message: str = Field(default="Feedback recorded successfully")
