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

# ── Supported LLM providers and their task mappings ──────────────────────────
# Groq only supports 'conversational' (chat completions), not 'text-generation'.
# We default to chat_completion which works across all major providers.
_PROVIDER_DEFAULTS = {
    "huggingface": {"task": "chat_completion", "model": "Qwen/Qwen3-32B"},
    "groq": {"task": "chat_completion", "model": "llama-3.3-70b-versatile"},
    "google": {"task": "chat_completion", "model": "gemini-pro"},
}


class PatternLearner:
    """Learn from user feedback to improve suggestions using LLMs."""
    
    def __init__(self, storage_path: str = "./learned_patterns.json", model_name: str = "Qwen/Qwen3-32B", api_key: Optional[str] = None):
        """Initialize pattern learner."""
        self.storage_path = storage_path
        self.patterns = self._load_patterns()
        
        self.provider = os.getenv("LLM_PROVIDER", "huggingface").lower()
        provider_cfg = _PROVIDER_DEFAULTS.get(self.provider, _PROVIDER_DEFAULTS["huggingface"])

        self.model_name = os.getenv('HUGGINGFACE_PATTERN_MODEL', model_name or provider_cfg["model"])
        self.api_key = api_key or os.getenv('HUGGINGFACE_API_KEY')
        
        if not InferenceClient:
            logger.warning("huggingface_hub not installed. Advanced pattern learning will fail.")
            self.client = None
        else:
            try:
                # Only pass provider when it's a known non-default provider
                provider_arg = self.provider if self.provider != "huggingface" else None
                self.client = InferenceClient(
                    token=self.api_key,
                    provider=provider_arg,  # type: ignore[arg-type]
                )
            except Exception as exc:
                logger.error("Failed to initialise InferenceClient: %s", exc)
                self.client = None
    
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
        
    def analyze_patterns(self) -> str:
        """Use the configured LLM to analyze feedback and deduce coding rules.
        
        Falls back to deterministic rule-based analysis when the LLM is
        unavailable or the provider returns an error.
        """
        stats = self.get_statistics()
        if not stats:
            return "Not enough telemetry data to deduce patterns."

        # ── Try LLM-based analysis first ─────────────────────────────────
        if self.client is not None:
            try:
                return self._analyze_via_llm(stats)
            except Exception as exc:
                logger.error("LLM pattern analysis failed (provider=%s): %s", self.provider, exc)
                # Fall through to rule-based analysis

        # ── Deterministic fallback ───────────────────────────────────────
        return self._analyze_via_rules(stats)

    def _analyze_via_llm(self, stats: Dict) -> str:
        """Call the LLM using chat_completion (works for all providers including Groq)."""
        system_prompt = (
            "You are an elite Staff Software Engineer analyzing team telemetry data. "
            "Output a concise Markdown list of deduced coding rules."
        )
        user_prompt = (
            f"Here is a JSON mapping of AI code review suggestions and their "
            f"acceptance/rejection rates:\n{json.dumps(stats, indent=2)}\n\n"
            f"Based on these rates, what coding patterns and project specific rules "
            f"can you deduce that we should enforce?\n"
            f"If a suggestion type has a high rejection rate, advise on how our AI "
            f"should stop suggesting it."
        )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ]

        response = self.client.chat_completion(
            messages=messages,
            model=self.model_name,
            max_tokens=400,
            temperature=0.2,
        )

        # Extract the assistant reply from the chat completion response
        if hasattr(response, "choices") and response.choices:
            return response.choices[0].message.content
        # Some providers return a dict-like object
        if isinstance(response, dict):
            choices = response.get("choices", [])
            if choices:
                return choices[0].get("message", {}).get("content", str(response))
        return str(response)

    @staticmethod
    def _analyze_via_rules(stats: Dict) -> str:
        """Deterministic fallback when the LLM is unavailable."""
        lines = ["## Deduced Rules (rule-based fallback)\n"]

        for issue_type, data in stats.items():
            rate = data["acceptance_rate"]
            total = data["total_suggestions"]

            if rate < 0.3:
                lines.append(
                    f"- **SUPPRESS** `{issue_type}` — only {rate*100:.0f}% acceptance "
                    f"across {total} suggestions. Consider removing this check."
                )
            elif rate < 0.5:
                lines.append(
                    f"- **REVIEW** `{issue_type}` — {rate*100:.0f}% acceptance. "
                    f"Refine severity threshold or wording."
                )
            else:
                lines.append(
                    f"- **KEEP** `{issue_type}` — {rate*100:.0f}% acceptance. "
                    f"Well-received by the team."
                )

        return "\n".join(lines)
    
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