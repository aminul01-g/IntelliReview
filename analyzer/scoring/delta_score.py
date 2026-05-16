from typing import List, Dict, Any
import logging

logger = logging.getLogger(__name__)

class DeltaScoreEngine:
    """
    Quantifies the impact of a change by comparing issue sets
    between pre-change and post-change versions of modified scopes.
    """

    SEVERITY_WEIGHTS = {
        "critical": 10,
        "high": 5,
        "medium": 2,
        "low": 1
    }

    def __init__(self, detectors: List[Any]):
        self.detectors = detectors

    def calculate_delta(self, pre_code: str, post_code: str, filename: str, language: str) -> Dict[str, Any]:
        """
        Compares pre and post versions of a scope to calculate a quality delta.
        """
        pre_issues = self._run_detectors(pre_code, filename, language)
        post_issues = self._run_detectors(post_code, filename, language)

        resolved_weight = 0
        introduced_weight = 0

        # Issues that were in pre but are NOT in post (Resolved)
        # Simple line-based matching for a scope-level check
        pre_issue_keys = {f"{i.get('type')}-{i.get('line')}" for i in pre_issues}
        post_issue_keys = {f"{i.get('type')}-{i.get('line')}" for i in post_issues}

        resolved = pre_issue_keys - post_issue_keys
        introduced = post_issue_keys - pre_issue_keys

        # Calculate weight for resolved issues (Positive impact)
        for key in resolved:
            issue = next((i for i in pre_issues if f"{i.get('type')}-{i.get('line')}" == key), {})
            resolved_weight += self.SEVERITY_WEIGHTS.get(issue.get("severity", "medium"), 2)

        # Calculate weight for introduced issues (Negative impact)
        for key in introduced:
            issue = next((i for i in post_issues if f"{i.get('type')}-{i.get('line')}" == key), {})
            introduced_weight += self.SEVERITY_WEIGHTS.get(issue.get("severity", "medium"), 2)

        delta = resolved_weight - introduced_weight

        return {
            "delta_score": delta,
            "resolved_count": len(resolved),
            "introduced_count": len(introduced),
            "resolved_weight": resolved_weight,
            "introduced_weight": introduced_weight
        }

    def _run_detectors(self, code: str, filename: str, language: str) -> List[Dict]:
        """Runs all static detectors on a piece of code."""
        all_issues = []
        for detector in self.detectors:
            try:
                # Use standardized detect method
                issues = detector.detect(code, filename=filename, language=language)
                all_issues.extend(issues)
            except Exception as e:
                logger.error(f"DeltaScoreEngine detector {detector.__class__.__name__} failed: {e}")
        return all_issues
