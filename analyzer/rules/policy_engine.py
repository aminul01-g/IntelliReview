"""
Organization-Level Policy Engine
================================
Enforces organization-wide rules across all repositories.
Handles policy inheritance: org_policies.yml -> .intellireview.yml
Org-level severities cannot be weakened by repo-level configurations.
"""

import os
import yaml
import logging
from typing import Dict, Any, List, Optional
from pathlib import Path

from api.schemas.feedback_schemas import SeverityLevel

logger = logging.getLogger(__name__)

class PolicyEngine:
    """
    Manages organization policies and merges them with repository configurations.
    """
    def __init__(self, org_policy_path: str = "/tmp/org_policies.yml"):
        self.org_policy_path = Path(org_policy_path)
        self.global_policies = self._load_global_policies()

    def _load_global_policies(self) -> Dict[str, Any]:
        """Load the global organization policy file."""
        if not self.org_policy_path.exists():
            return {"rules": []}
        try:
            with open(self.org_policy_path, "r") as f:
                return yaml.safe_load(f) or {"rules": []}
        except Exception as e:
            logger.error(f"Failed to load global org policies: {e}")
            return {"rules": []}

    def set_global_policies(self, rules: List[Dict[str, Any]]):
        """Update global org policies. Expected to be used by Admin API."""
        try:
            self.org_policy_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.org_policy_path, "w") as f:
                yaml.dump({"rules": rules}, f)
            self.global_policies = {"rules": rules}
        except Exception as e:
            logger.error(f"Failed to save global org policies: {e}")
            raise e

    def get_effective_severity(self, rule_id: str, repo_severity: Optional[str] = None) -> Optional[str]:
        """
        Merge rules. If a globally enforced rule exists, it takes precedence if it is stricter
        than the repo_severity.
        """
        global_rule = self._get_global_rule(rule_id)
        
        if not global_rule and not repo_severity:
            return None
            
        if not global_rule:
            return repo_severity
            
        global_severity = global_rule.get("severity", "").lower()
        if not global_severity:
            return repo_severity
            
        if not repo_severity:
            return global_severity
            
        # Hierarchy: critical/important > high > medium/nit > low > info/preexisting
        # We parse them to numeric ranks
        return self._stricter_severity(global_severity, repo_severity)

    def _get_global_rule(self, rule_id: str) -> Optional[Dict[str, Any]]:
        rules = self.global_policies.get("rules", [])
        for r in rules:
            if r.get("id") == rule_id:
                return r
        return None

    def _stricter_severity(self, sev1: str, sev2: str) -> str:
        """Return the stricter of the two severities."""
        ranks = {
            "critical": 50,
            "important": 50,
            "high": 40,
            "medium": 30,
            "nit": 30,
            "low": 20,
            "info": 10,
            "preexisting": 10
        }
        r1 = ranks.get(sev1.lower(), 0)
        r2 = ranks.get(sev2.lower(), 0)
        
        return sev1 if r1 >= r2 else sev2

engine = PolicyEngine()
