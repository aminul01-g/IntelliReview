"""
Custom Rule Engine
==================
Allows teams to define project-specific code rules via YAML configuration.
Rules are evaluated against each file during analysis and produce issues
just like the built-in detectors.

Usage:
    Place a `.intellireview.yml` in your project root:

    ```yaml
    rules:
      - id: no-print
        pattern: "print\\("
        message: "Use logging module instead of print()"
        severity: medium
        languages: [python]
        suggestion: "Replace print() with logger.info()"

      - id: no-eval
        pattern: "eval\\("
        message: "Never use eval() — security risk"
        severity: critical
        languages: [python, javascript]

      - id: max-line-length
        max_line_length: 120
        message: "Line exceeds {max_line_length} characters"
        severity: low

      - id: max-file-length
        max_file_lines: 500
        message: "File exceeds {max_file_lines} lines"
        severity: medium

      - id: banned-import
        pattern: "from datetime import datetime"
        message: "Use arrow or pendulum instead of stdlib datetime"
        severity: low
        languages: [python]
        suggestion: "import arrow"

      - id: required-header
        required_pattern: "# Copyright"
        message: "Missing copyright header"
        severity: low
        languages: [python]
    ```
"""

import re
import yaml
from pathlib import Path
from typing import List, Dict, Optional


class CustomRuleEngine:
    """Evaluate user-defined YAML rules against source code."""

    def __init__(self, rules: Optional[List[Dict]] = None):
        self.rules = rules or []

    @classmethod
    def from_yaml(cls, yaml_path: str) -> "CustomRuleEngine":
        """Load rules from a YAML file."""
        path = Path(yaml_path)
        if not path.exists():
            return cls(rules=[])
        try:
            with open(path, "r") as f:
                data = yaml.safe_load(f) or {}
            return cls(rules=data.get("rules", []))
        except Exception:
            return cls(rules=[])

    @classmethod
    def from_dict(cls, data: Dict) -> "CustomRuleEngine":
        """Load rules from a dict (e.g. from API payload)."""
        return cls(rules=data.get("rules", []))

    def evaluate(self, code: str, filename: str, language: str) -> List[Dict]:
        """Evaluate all rules against the given code. Returns a list of issues."""
        issues = []
        lines = code.split("\n")

        for rule in self.rules:
            rule_id = rule.get("id", "custom-rule")
            allowed_langs = rule.get("languages")

            # Skip if rule is language-specific and doesn't match
            if allowed_langs and language not in allowed_langs:
                continue

            severity = rule.get("severity", "medium")
            suggestion = rule.get("suggestion", "")

            # ── Pattern match (banned pattern) ──
            pattern = rule.get("pattern")
            if pattern:
                try:
                    regex = re.compile(pattern)
                    for i, line in enumerate(lines, 1):
                        if regex.search(line):
                            msg = rule.get("message", f"Custom rule '{rule_id}' violated")
                            issues.append({
                                "type": f"custom_rule:{rule_id}",
                                "severity": severity,
                                "line": i,
                                "message": msg,
                                "suggestion": suggestion,
                            })
                except re.error:
                    pass

            # ── Required pattern (must be present) ──
            required = rule.get("required_pattern")
            if required:
                try:
                    if not re.search(required, code):
                        msg = rule.get("message", f"Required pattern '{required}' not found")
                        issues.append({
                            "type": f"custom_rule:{rule_id}",
                            "severity": severity,
                            "line": 1,
                            "message": msg,
                            "suggestion": suggestion,
                        })
                except re.error:
                    pass

            # ── Max line length ──
            max_line_len = rule.get("max_line_length")
            if max_line_len and isinstance(max_line_len, int):
                for i, line in enumerate(lines, 1):
                    if len(line) > max_line_len:
                        raw_msg = rule.get("message", f"Line exceeds {max_line_len} chars")
                        msg = raw_msg.replace("{max_line_length}", str(max_line_len))
                        issues.append({
                            "type": f"custom_rule:{rule_id}",
                            "severity": severity,
                            "line": i,
                            "message": f"{msg} ({len(line)} chars)",
                            "suggestion": suggestion or f"Keep lines under {max_line_len} characters",
                        })
                        # Only report first 5 occurrences
                        if len([x for x in issues if x["type"] == f"custom_rule:{rule_id}"]) >= 5:
                            break

            # ── Max file length ──
            max_file_lines = rule.get("max_file_lines")
            if max_file_lines and isinstance(max_file_lines, int):
                if len(lines) > max_file_lines:
                    raw_msg = rule.get("message", f"File exceeds {max_file_lines} lines")
                    msg = raw_msg.replace("{max_file_lines}", str(max_file_lines))
                    issues.append({
                        "type": f"custom_rule:{rule_id}",
                        "severity": severity,
                        "line": 1,
                        "message": f"{msg} ({len(lines)} lines)",
                        "suggestion": suggestion or "Split into smaller modules",
                    })

            # ── Max function length (Python) ──
            max_func_lines = rule.get("max_function_lines")
            if max_func_lines and isinstance(max_func_lines, int) and language == "python":
                issues.extend(self._check_python_func_length(lines, max_func_lines, rule_id, severity))

        return issues

    def _check_python_func_length(self, lines: List[str], max_lines: int,
                                   rule_id: str, severity: str) -> List[Dict]:
        """Check Python function lengths."""
        issues = []
        func_start = None
        func_name = None
        func_indent = 0

        for i, line in enumerate(lines):
            stripped = line.lstrip()
            indent = len(line) - len(stripped)

            if stripped.startswith("def ") or stripped.startswith("async def "):
                # If we were tracking a previous function, check its length
                if func_start is not None:
                    length = i - func_start
                    if length > max_lines:
                        issues.append({
                            "type": f"custom_rule:{rule_id}",
                            "severity": severity,
                            "line": func_start + 1,
                            "message": f"Function '{func_name}' has {length} lines (max: {max_lines})",
                            "suggestion": "Break into smaller, focused functions",
                        })
                func_start = i
                func_name = stripped.split("(")[0].replace("def ", "").replace("async ", "").strip()
                func_indent = indent

        # Check last function
        if func_start is not None:
            length = len(lines) - func_start
            if length > max_lines:
                issues.append({
                    "type": f"custom_rule:{rule_id}",
                    "severity": severity,
                    "line": func_start + 1,
                    "message": f"Function '{func_name}' has {length} lines (max: {max_lines})",
                    "suggestion": "Break into smaller, focused functions",
                })

        return issues[:5]
