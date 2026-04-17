"""
Continuous Learning Loop
========================
Hooks into the feedback mechanism to automatically suggest config changes when
the AI sees consistent rejection of certain rules.
"""

import logging
from typing import Optional

from ml_models.pattern_learner import PatternLearner

logger = logging.getLogger(__name__)

class LearningLoop:
    """
    Monitors feedback patterns and auto-suggests `.intellireview.yml` updates.
    """
    def __init__(self, pattern_learner: Optional[PatternLearner] = None):
        if pattern_learner is None:
            # Instantiate default pattern learner if none provided
            self.learner = PatternLearner()
        else:
            self.learner = pattern_learner

        # The auto-suggestion thresholds
        self.min_samples = 10
        self.rejection_threshold = 0.70  # e.g., >70% rejection triggers a config suggestion

    def on_feedback(self, suggestion_id: str, issue_type: str, accepted: bool):
        """
        Record feedback and check if a configuration update should be suggested to the team.
        """
        # 1. Track in local pattern JSON
        self.learner.track_feedback(suggestion_id, issue_type, accepted, context_hash=None)
        
        # 2. Re-evaluate metrics for auto-suggestion
        stats = self.learner.patterns.get(issue_type, {})
        total = stats.get("total", 0)
        
        if total >= self.min_samples:
            acceptance_rate = self.learner.get_acceptance_rate(issue_type)
            rejection_rate = 1.0 - acceptance_rate
            
            if rejection_rate > self.rejection_threshold:
                # We should trigger a config auto-suggestion.
                # In a real app, this would dispatch an email or post a special issue/PR.
                # For now, we log the auto-suggestion.
                self._generate_config_suggestion_pr(issue_type, rejection_rate, total)

    def _generate_config_suggestion_pr(self, issue_type: str, rejection_rate: float, samples: int):
        """
        Simulates creating an automated PR to update `.intellireview.yml`
        when a rule is consistently failing or ignored by devs.
        """
        suggestion_msg = (
            f"🤖 IntelliReview Continuous Learning\n"
            f"Rule '{issue_type}' has been rejected {rejection_rate:.0%} of the time "
            f"over the last {samples} occurrences.\n\n"
            f"Suggested Action: Add the following to your `.intellireview.yml` to reduce noise:\n"
            f"```yaml\n"
            f"rules:\n"
            f"  - id: {issue_type}\n"
            f"    severity: ignored # or 'low'\n"
            f"```\n"
        )
        logger.warning(f"[LEARNING LOOP] Auto-suggestion generated:\n{suggestion_msg}")
        return suggestion_msg
