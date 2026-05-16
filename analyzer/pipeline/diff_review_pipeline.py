from typing import List, Dict, Any, Optional
import logging
from analyzer.detectors.base import Detector
from analyzer.context.ast_diff_mapper import map_diff_to_ast_context
from analyzer.scoring.delta_score import DeltaScoreEngine

logger = logging.getLogger(__name__)

class DiffReviewPipeline:
    """
    Orchestrates the diff-aware review process:
    Diff -> AST Mapping -> Static Detection -> Surgical Filtering -> Delta Scoring.
    """

    def __init__(self, detectors: List[Detector]):
        self.detectors = detectors
        self.score_engine = DeltaScoreEngine(detectors)

    def run(self, diff_hunks: List[Dict], full_code: str, filename: str, language: str, pre_code: Optional[str] = None, hunk_base_line: int = 1) -> Dict[str, Any]:
        """
        Executes the full diff-aware analysis pipeline.

        Args:
            diff_hunks: List of diff hunk dicts with 'context', 'added_lines', 'removed_lines'.
            full_code: The full post-change file content.
            filename: Name of the file being analyzed.
            language: Programming language.
            pre_code: Optional pre-change code for delta scoring.
            hunk_base_line: The line number in the actual file where the first hunk starts.
                           This is used to map relative hunk line numbers to absolute file line numbers.
        """
        # 1. Map diff hunks to logical AST scopes
        modified_scopes = map_diff_to_ast_context(diff_hunks, language, base_line=hunk_base_line)

        # 2. Run all static detectors on the full post-change code
        all_issues = []
        for detector in self.detectors:
            try:
                # Ensure we call the standardized 'detect' method
                issues = detector.detect(full_code, filename=filename, language=language)
                all_issues.extend(issues)
            except Exception as e:
                logger.error(f"Detector {detector.__class__.__name__} failed: {e}")

        # 3. Surgical Filtering
        # An issue is kept if it's within a modified scope or a modified hunk
        filtered_issues = self._filter_issues(all_issues, diff_hunks, modified_scopes)

        # 4. Delta Scoring
        delta_score = 0
        delta_details = {}
        if pre_code:
            # For a a coarse project-level delta, we compare the whole files.
            # In a more refined version, we'd only compare the affected scopes.
            result = self.score_engine.calculate_delta(pre_code, full_code, filename, language)
            delta_score = result["delta_score"]
            delta_details = result

        return {
            "issues": filtered_issues,
            "delta_score": delta_score,
            "delta_details": delta_details,
            "modified_scopes": modified_scopes,
            "summary": {
                "total_issues_found": len(all_issues),
                "diff_relevant_issues": len(filtered_issues)
            }
        }

    def _filter_issues(self, issues: List[Dict], hunks: List[Dict], scopes: List[Dict]) -> List[Dict]:
        """
        Filters issues to only those that are relevant to the changes.
        """
        relevant_issues = []

        for issue in issues:
            line = issue.get("line", 1)

            # Check if the issue falls within any modified AST scope
            is_relevant = False
            for scope in scopes:
                # Use the enhanced start_line and end_line from ast_diff_mapper
                start = scope.get("start_line", 0)
                end = scope.get("end_line", 999999)
                if start <= line <= end:
                    is_relevant = True
                    break

            if is_relevant:
                relevant_issues.append(issue)

        return relevant_issues
