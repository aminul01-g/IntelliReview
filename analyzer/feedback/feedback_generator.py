"""
FeedbackGenerator
=================
Core service that transforms raw AI analysis into structured, world-class
PR review comments.

Pipeline:
    Raw AI Findings
    → SeverityOrchestrator (calibrate)
    → Dataflow Enrichment (MCP integration)
    → Evidence Generator
    → Markdown Renderer
    → PRReviewComment (structured output)
    → Verification Walkthrough (artifact)
"""

from __future__ import annotations

import hashlib
import logging
import re
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from api.schemas.feedback_schemas import (
    AutofixDiff,
    DataflowNode,
    DataflowTrace,
    FindingCategory,
    NitSummary,
    NitSummaryItem,
    PRReviewComment,
    ReproductionStep,
    ReviewFinding,
    ReviewerFeedbackRequest,
    ReviewerFeedbackResponse,
    SeverityLevel,
    SEVERITY_LABELS,
    SEVERITY_MARKERS,
    TestCase,
    VerificationEntry,
    VerificationWalkthrough,
)
from analyzer.feedback.severity_orchestrator import (
    SENSITIVE_SINKS,
    CalibratedResult,
    SeverityOrchestrator,
)
from analyzer.feedback.verification import VerificationWalkthroughGenerator

logger = logging.getLogger(__name__)


class FeedbackGenerator:
    """
    Transforms raw analysis into production-grade PR review comments.

    Usage:
        generator = FeedbackGenerator(project_root="/path/to/repo")
        comment = generator.generate_review(
            raw_findings=issues,
            code="...",
            language="python",
            repository="owner/repo",
            pr_number=42,
        )
        markdown = generator.render_markdown(comment)
    """

    def __init__(
        self,
        project_root: Optional[str] = None,
        nit_cap: int = 5,
    ):
        self.severity_orchestrator = SeverityOrchestrator(
            project_root=project_root,
            nit_cap=nit_cap,
        )
        self.walkthrough_generator = VerificationWalkthroughGenerator()

    # ─── Public API ───────────────────────────────────────────────────

    def generate_review(
        self,
        raw_findings: List[Dict[str, Any]],
        code: str,
        language: str,
        repository: str = "unknown/unknown",
        pr_number: int = 0,
        file_path: str = "unknown",
        knowledge_base: Optional[Any] = None,
        files_reviewed: int = 1,
    ) -> PRReviewComment:
        """
        Full pipeline: calibrate → enrich → render.

        Args:
            raw_findings: Raw issue dicts from the analysis pipeline.
            code: Source code being reviewed.
            language: Programming language.
            repository: GitHub repo full name.
            pr_number: PR number.
            file_path: File path for context.
            knowledge_base: PatternLearner instance for telemetry.
            files_reviewed: Number of files reviewed.

        Returns:
            PRReviewComment with all findings calibrated and enriched.
        """
        # Step 1: Inject file_path into raw findings if missing
        for finding in raw_findings:
            if "file_path" not in finding and "filename" not in finding:
                finding["file_path"] = file_path

        # Step 2: Dataflow enrichment
        dataflow_traces = self._compute_dataflow_traces(raw_findings, code, language)

        # Step 3: Severity calibration
        result: CalibratedResult = self.severity_orchestrator.calibrate(
            raw_findings=raw_findings,
            knowledge_base=knowledge_base,
            dataflow_traces=dataflow_traces,
        )

        # Step 4: Determine verdict
        verdict = self._compute_verdict(result)

        # Step 5: Generate verification walkthrough
        walkthrough = self.walkthrough_generator.generate(
            important_findings=result.important_findings,
            nit_summary=result.nit_summary,
            preexisting_findings=result.preexisting_findings,
            calibration_log=result.calibration_log,
        )

        # Step 6: Assemble the PR review comment
        review_id = hashlib.sha256(
            f"{repository}:{pr_number}:{datetime.now(timezone.utc).isoformat()}".encode()
        ).hexdigest()[:16]

        return PRReviewComment(
            review_id=review_id,
            repository=repository,
            pr_number=max(pr_number, 1),
            important_findings=result.important_findings,
            nit_findings=result.nit_summary,
            preexisting_findings=result.preexisting_findings,
            files_reviewed=files_reviewed,
            verdict=verdict,
            verification_walkthrough=walkthrough,
        )

    def render_markdown(self, comment: PRReviewComment) -> str:
        """
        Render a PRReviewComment into a full Markdown string suitable for
        posting as a GitHub PR comment.
        """
        sections: List[str] = []

        # Header
        marker = {"pass": "🟢", "warn": "🟡", "fail": "🔴"}.get(comment.verdict, "⚪")
        sections.append(
            f"# {marker} IntelliReview AI Audit\n\n"
            f"> **{comment.files_reviewed}** files reviewed | "
            f"**{comment.total_findings}** findings | "
            f"Verdict: **{comment.verdict.upper()}**\n"
        )

        # Important findings
        if comment.important_findings:
            sections.append("---\n\n## 🔴 Important Findings (Block Merge)\n")
            for finding in comment.important_findings:
                sections.append(self._render_finding(finding))

        # Nit findings
        if comment.nit_findings and comment.nit_findings.total_nit_count > 0:
            sections.append("---\n\n## 🟡 Nits (Style / Polish)\n")
            for nit in comment.nit_findings.shown_nits:
                sections.append(self._render_finding(nit))

            if comment.nit_findings.collapsed_nits:
                sections.append(self._render_collapsed_nits(comment.nit_findings))

        # Pre-existing findings
        if comment.preexisting_findings:
            sections.append("---\n\n## 🟣 Pre-existing (Legacy Debt)\n")
            for finding in comment.preexisting_findings:
                sections.append(self._render_finding(finding))

        # Verification walkthrough reference
        if comment.verification_walkthrough:
            sections.append(
                "---\n\n"
                "<details>\n"
                "<summary>📋 Verification Walkthrough</summary>\n\n"
                + self._render_walkthrough(comment.verification_walkthrough)
                + "\n</details>\n"
            )

        return "\n".join(sections)

    # ─── Finding Renderer ────────────────────────────────────────────

    def _render_finding(self, finding: ReviewFinding) -> str:
        """Render a single finding as structured Markdown."""
        marker = SEVERITY_MARKERS.get(finding.severity, "⚪")
        label = SEVERITY_LABELS.get(finding.severity, finding.severity.value)

        lines: List[str] = []

        # Header
        lines.append(f"### {marker} {finding.title}\n")
        lines.append(
            f"**File:** `{finding.file_path}` "
            f"**Line:** {finding.line}\n"
        )

        # Narrative — 'The Why'
        lines.append(f"{finding.narrative}\n")

        # Dataflow trace
        if finding.dataflow_trace:
            trace = finding.dataflow_trace
            lines.append(
                f"**Dataflow:** `{trace.source.expression}` → "
                f"`{trace.sink.expression}` "
                f"{'(⚠️ unsanitized)' if not trace.is_sanitized else '(✅ sanitized)'}\n"
            )

        # DESIGN.md constraint
        if finding.design_constraint:
            lines.append(
                f"> ⚠️ **Architecture Violation:** {finding.design_constraint}\n"
            )

        # Autofix
        if finding.autofix:
            lines.append(
                "<details>\n"
                "<summary>🔧 Autofix (click to expand)</summary>\n\n"
                f"```diff\n{finding.autofix.unified_diff}\n```\n\n"
                "</details>\n"
            )

        # Evidence
        if finding.evidence:
            evidence = finding.evidence
            if isinstance(evidence, ReproductionStep):
                lines.append(
                    "<details>\n"
                    f"<summary>🧪 Evidence: {evidence.title}</summary>\n\n"
                    f"**Payload:** `{evidence.payload}`\n\n"
                    f"**Expected:** {evidence.expected}\n\n"
                    f"**Actual:** {evidence.actual}\n"
                )
                if evidence.curl_command:
                    lines.append(f"\n```bash\n{evidence.curl_command}\n```\n")
                lines.append("\n</details>\n")
            elif isinstance(evidence, TestCase):
                lines.append(
                    "<details>\n"
                    f"<summary>🧪 Evidence: {evidence.title}</summary>\n\n"
                    f"**Input:** `{evidence.input_payload}`\n\n"
                    f"**Expected:** {evidence.expected_behavior}\n\n"
                    f"**Actual:** {evidence.actual_behavior}\n"
                )
                if evidence.code_snippet:
                    lines.append(
                        f"\n```{evidence.language}\n{evidence.code_snippet}\n```\n"
                    )
                lines.append("\n</details>\n")

        # References
        refs: List[str] = []
        if finding.cwe:
            cwe_id = finding.cwe.replace("CWE-", "")
            refs.append(
                f"[{finding.cwe}](https://cwe.mitre.org/data/definitions/{cwe_id}.html)"
            )
        if finding.owasp:
            refs.append(f"OWASP {finding.owasp}")
        if finding.reference_url:
            refs.append(f"[Reference]({finding.reference_url})")
        if refs:
            lines.append(f"> 📎 {' | '.join(refs)}\n")

        # Calibration note
        if finding.calibration_reason:
            lines.append(
                f"> 🔧 *Calibration: {finding.calibration_reason}*\n"
            )

        lines.append("")  # blank line separator
        return "\n".join(lines)

    # ─── Collapsed Nits ──────────────────────────────────────────────

    def _render_collapsed_nits(self, nit_summary: NitSummary) -> str:
        """Render collapsed nits as a summary table."""
        lines: List[str] = [
            f"\n<details>\n"
            f"<summary>📦 +{len(nit_summary.collapsed_nits)} more nits "
            f"(collapsed to reduce noise)</summary>\n\n"
            f"| # | File | Line | Category | Title |\n"
            f"|---|------|------|----------|-------|\n"
        ]
        for i, nit in enumerate(nit_summary.collapsed_nits, 1):
            lines.append(
                f"| {i} | `{nit.file_path}` | L{nit.line} | {nit.category.value} | {nit.title} |"
            )
        lines.append(f"\n> {nit_summary.collapse_reason}\n\n</details>\n")
        return "\n".join(lines)

    # ─── Verification Walkthrough ────────────────────────────────────

    def _render_walkthrough(self, walkthrough: VerificationWalkthrough) -> str:
        """Render the verification walkthrough as Markdown."""
        lines: List[str] = [
            f"**Generated:** {walkthrough.generated_at.strftime('%Y-%m-%d %H:%M:%S UTC')}\n",
            f"| Metric | Count |",
            f"|--------|-------|",
            f"| Total Findings | {walkthrough.total_findings} |",
            f"| 🔴 Important | {walkthrough.important_count} |",
            f"| 🟡 Nits | {walkthrough.nit_count} |",
            f"| 🟣 Pre-existing | {walkthrough.preexisting_count} |",
            f"| Dataflow Traces Checked | {walkthrough.dataflow_traces_checked} |",
            f"| Nits Collapsed | {walkthrough.nits_collapsed} |",
            "",
        ]

        if walkthrough.knowledge_base_rules_applied:
            lines.append("**KB Rules Applied:**")
            for rule in walkthrough.knowledge_base_rules_applied:
                lines.append(f"- {rule}")
            lines.append("")

        if walkthrough.entries:
            lines.append("**Finding Verification Details:**\n")
            lines.append("| Finding | Method | Summary | Result |")
            lines.append("|---------|--------|---------|--------|")
            for entry in walkthrough.entries:
                status = "✅" if entry.passed else "❌"
                lines.append(
                    f"| {entry.finding_title[:40]} | {entry.verification_method} | "
                    f"{entry.verification_summary[:50]} | {status} |"
                )
            lines.append("")

        return "\n".join(lines)

    # ─── Dataflow Tracking ───────────────────────────────────────────

    def _compute_dataflow_traces(
        self,
        raw_findings: List[Dict[str, Any]],
        code: str,
        language: str,
    ) -> Dict[str, DataflowTrace]:
        """
        Compute dataflow traces for findings that involve known taint patterns.

        This performs lightweight AST-free analysis by scanning for common
        source → sink patterns. For full AST-based tracking, the MCP
        `track_dataflow` tool should be used.
        """
        traces: Dict[str, DataflowTrace] = {}
        code_lines = code.split("\n")

        for raw in raw_findings:
            finding_id = raw.get("id") or self._generate_id(raw)
            raw_type = raw.get("type", "")
            message = raw.get("message", "").lower()

            # Only trace security-relevant findings
            if raw_type != "security_vulnerability" and "injection" not in message:
                continue

            line_num = raw.get("line", 0)
            if line_num <= 0 or line_num > len(code_lines):
                continue

            # Look for source → sink patterns in the surrounding code
            trace = self._trace_dataflow_in_context(
                code_lines, line_num, language, raw
            )
            if trace:
                traces[finding_id] = trace

        return traces

    def _trace_dataflow_in_context(
        self,
        code_lines: List[str],
        line_num: int,
        language: str,
        raw: Dict[str, Any],
    ) -> Optional[DataflowTrace]:
        """
        Lightweight dataflow tracing using pattern matching on surrounding code.

        Scans ±20 lines for source patterns (request params, user input) and
        sink patterns (execute, eval, innerHTML, etc.).
        """
        start = max(0, line_num - 20)
        end = min(len(code_lines), line_num + 20)
        context = code_lines[start:end]

        source_line = None
        sink_line = None
        source_expr = None
        sink_expr = None

        # Source patterns: things that introduce untrusted data
        source_patterns = [
            r'request\.(args|form|params|json|query|body|data)\[',
            r'request\.get\(',
            r'params\[', r'query\[',
            r'input\(', r'stdin',
            r'req\.(body|params|query)',
            r'document\.(getElementById|querySelector)',
            r'window\.location',
            r'argv\[',
        ]

        # Sink patterns: sensitive operations
        sink_patterns = [
            r'\.execute\(', r'\.query\(', r'\.raw\(',
            r'\beval\(', r'\bexec\(',
            r'os\.system\(', r'subprocess\.',
            r'\.innerHTML\s*=',
            r'document\.write\(',
            r'cursor\.execute\(',
            r'authenticate\(', r'verify_password\(',
        ]

        for i, line in enumerate(context):
            actual_line = start + i + 1
            for pattern in source_patterns:
                match = re.search(pattern, line)
                if match and source_line is None:
                    source_line = actual_line
                    source_expr = line.strip()
                    break

            for pattern in sink_patterns:
                match = re.search(pattern, line)
                if match and sink_line is None:
                    sink_line = actual_line
                    sink_expr = line.strip()
                    break

        if source_line and sink_line:
            file_path = raw.get("file_path", raw.get("filename", "unknown"))
            return DataflowTrace(
                source=DataflowNode(
                    expression=source_expr or "untrusted input",
                    file_path=file_path,
                    line=source_line,
                    node_type="source",
                ),
                sink=DataflowNode(
                    expression=sink_expr or "sensitive operation",
                    file_path=file_path,
                    line=sink_line,
                    node_type="sink",
                ),
                is_sanitized=False,
                summary=f"Untrusted input at L{source_line} flows to sensitive sink at L{sink_line}",
            )

        return None

    # ─── Verdict Computation ─────────────────────────────────────────

    @staticmethod
    def _compute_verdict(result: CalibratedResult) -> str:
        """Compute the overall verdict from calibrated results."""
        if result.important_findings:
            return "fail"
        if result.nit_summary and result.nit_summary.total_nit_count > 0:
            return "warn"
        if result.preexisting_findings:
            return "warn"
        return "pass"

    @staticmethod
    def _generate_id(raw: Dict[str, Any]) -> str:
        key = f"{raw.get('type', '')}:{raw.get('line', 0)}:{raw.get('message', '')}"
        return hashlib.sha256(key.encode()).hexdigest()[:12]
