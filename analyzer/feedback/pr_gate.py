"""
PR Quality Gate
===============
Calculates the 'Merge Readiness' verdict based on the Code Quality Health Score,
Technical Debt, and the presence of unresolved 'Important' AI findings.
"""

from typing import List, Dict, Any, Optional
from pydantic import BaseModel, Field
from api.schemas.feedback_schemas import PRReviewComment, SeverityLevel

class MergeReadinessVerdict(BaseModel):
    can_merge: bool
    verdict: str = Field(description="'pass', 'warn', or 'block'")
    health_score: float
    technical_debt_hours: float
    unresolved_important: int
    block_reasons: List[str] = Field(default_factory=list)
    recommendations: List[str] = Field(default_factory=list)


class PRGate:
    def __init__(self, target_health_score: float = 80.0, max_debt_hours: float = 4.0):
        self.target_health_score = target_health_score
        self.max_debt_hours = max_debt_hours

    def evaluate(self, pr_review: PRReviewComment, total_lines: int) -> MergeReadinessVerdict:
        """Evaluate a PR against organization quality gates."""
        
        # 1. Gather all issues to calculate tech debt and health score
        all_findings = pr_review.important_findings + pr_review.preexisting_findings
        if pr_review.nit_findings:
            all_findings.extend(pr_review.nit_findings.shown_nits)
            # Add an approximation for collapsed nits
            total_nits = pr_review.nit_findings.total_nit_count

        critical_high_count = len([
            f for f in pr_review.important_findings 
            if f.severity == SeverityLevel.important
        ])
        
        # 2. Compute Health Score
        # Formula from existing mcp_server.py: 100 - (critical_high_count / max(total_lines, 1)) * 1000
        # If total_lines is 0, default to 1 to avoid ZeroDivisionError
        safe_lines = max(total_lines, 1)
        health_score = max(0.0, min(100.0, 100.0 - (critical_high_count / safe_lines) * 1000))
        
        # 3. Compute Technical Debt
        # Assume critical/important = 60m, nit = 5m, preexisting = 15m
        tech_debt_minutes = 0
        tech_debt_minutes += critical_high_count * 60
        
        if pr_review.nit_findings:
            tech_debt_minutes += pr_review.nit_findings.total_nit_count * 5
            
        tech_debt_minutes += len(pr_review.preexisting_findings) * 15
        tech_debt_hours = round(tech_debt_minutes / 60.0, 1)

        unresolved_important = len(pr_review.important_findings)
        
        # 4. Generate Verdict
        block_reasons = []
        recommendations = []
        verdict_str = "pass"
        can_merge = True
        
        if health_score < self.target_health_score:
            block_reasons.append(f"Health Score ({health_score:.1f}%) is below the {self.target_health_score}% threshold.")
            
        if unresolved_important > 0:
            block_reasons.append(f"Found {unresolved_important} unresolved 'Important' 🔴 issue(s).")
            
        if block_reasons:
            verdict_str = "block"
            can_merge = False
        elif tech_debt_hours > self.max_debt_hours:
            verdict_str = "warn"
            recommendations.append(f"Technical debt ({tech_debt_hours}h) exceeds recommendation ({self.max_debt_hours}h).")
            
        return MergeReadinessVerdict(
            can_merge=can_merge,
            verdict=verdict_str,
            health_score=round(health_score, 1),
            technical_debt_hours=tech_debt_hours,
            unresolved_important=unresolved_important,
            block_reasons=block_reasons,
            recommendations=recommendations
        )
