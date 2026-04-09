from typing import List, Dict
import json
from collections import defaultdict

class PatternLearner:
    """Learn from user feedback to improve suggestions."""
    
    def __init__(self, storage_path: str = "./learned_patterns.json"):
        """Initialize pattern learner."""
        self.storage_path = storage_path
        self.patterns = self._load_patterns()
    
    def record_feedback(
        self,
        suggestion_id: str,
        accepted: bool,
        issue_type: str,
        code_context: str
    ):
        """Record user feedback on a suggestion."""
        if issue_type not in self.patterns:
            self.patterns[issue_type] = {
                "total": 0,
                "accepted": 0,
                "rejected": 0,
                "examples": []
            }
        
        self.patterns[issue_type]["total"] += 1
        
        if accepted:
            self.patterns[issue_type]["accepted"] += 1
        else:
            self.patterns[issue_type]["rejected"] += 1
        
        # Store example
        self.patterns[issue_type]["examples"].append({
            "suggestion_id": suggestion_id,
            "accepted": accepted,
            "context_hash": hash(code_context) % 10000
        })
        
        # Limit examples to last 100
        if len(self.patterns[issue_type]["examples"]) > 100:
            self.patterns[issue_type]["examples"] = \
                self.patterns[issue_type]["examples"][-100:]
        
        self._save_patterns()
    
    def get_acceptance_rate(self, issue_type: str) -> float:
        """Get acceptance rate for an issue type."""
        if issue_type not in self.patterns:
            return 0.5  # Default
        
        pattern = self.patterns[issue_type]
        if pattern["total"] == 0:
            return 0.5
        
        return pattern["accepted"] / pattern["total"]
    
    def should_suggest(self, issue_type: str, threshold: float = 0.3) -> bool:
        """Determine if we should suggest for this issue type."""
        acceptance_rate = self.get_acceptance_rate(issue_type)
        return acceptance_rate >= threshold
    
    def get_statistics(self) -> Dict:
        """Get learning statistics."""
        stats = {}
        
        for issue_type, data in self.patterns.items():
            if data["total"] > 0:
                stats[issue_type] = {
                    "total_suggestions": data["total"],
                    "acceptance_rate": round(data["accepted"] / data["total"], 2),
                    "rejection_rate": round(data["rejected"] / data["total"], 2)
                }
        
        return stats
    
    def _load_patterns(self) -> Dict:
        """Load patterns from storage."""
        try:
            with open(self.storage_path, 'r') as f:
                return json.load(f)
        except FileNotFoundError:
            return {}
    
    def _save_patterns(self):
        """Save patterns to storage."""
        with open(self.storage_path, 'w') as f:
            json.dump(self.patterns, f, indent=2)