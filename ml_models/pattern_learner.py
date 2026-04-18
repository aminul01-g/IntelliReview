from typing import List, Dict, Optional
import json
import os
import logging
from collections import defaultdict

try:
    from huggingface_hub import InferenceClient
except ImportError:
    InferenceClient = None

logger = logging.getLogger(__name__)

class PatternLearner:
    """Learn from user feedback to improve suggestions using LLMs."""
    
    def __init__(self, storage_path: str = "./learned_patterns.json", model_name: str = "Qwen/Qwen3-32B", api_key: str = None):
        """Initialize pattern learner."""
        self.storage_path = storage_path
        self.patterns = self._load_patterns()
        
        self.model_name = os.getenv('HUGGINGFACE_PATTERN_MODEL', model_name)
        self.api_key = api_key or os.getenv('HUGGINGFACE_API_KEY')
        
        if not InferenceClient:
            logger.warning("huggingface_hub not installed. Advanced pattern learning will fail.")
            self.client = None
        else:
            self.client = InferenceClient(token=self.api_key)
    
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
        # a
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
        
    def analyze_patterns(self) -> str:
        """Use the Qwen LLM to analyze the JSON feedback and deduce coding rules."""
        if not self.client:
            return "LLM Inference Client not available."
            
        stats = self.get_statistics()
        if not stats:
            return "Not enough telemetry data to deduce patterns."
            
        prompt = f"""You are an elite Staff Software Engineer analyzing team telemetry data.
Here is a JSON mapping of AI code review suggestions and their acceptance/rejection rates:
{json.dumps(stats, indent=2)}

Based on these rates, what coding patterns and project specific rules can you deduce that we should enforce?
If a suggestion type has a high rejection rate, advise on how our AI should stop suggesting it.

Output a concise Markdown list of deduced rules."""
        
        try:
            return self.client.text_generation(
                prompt,
                model=self.model_name,
                max_new_tokens=400,
                temperature=0.2
            )
        except Exception as e:
            logger.error(f"Failed to infer patterns via LLM: {e}")
            return f"Error inferring patterns: {str(e)}"
    
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