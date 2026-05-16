from typing import List, Dict, Protocol

class Detector(Protocol):
    """
    Standard interface for all IntelliReview detectors.
    All detectors must implement a `detect` method that returns a list of
    standardized issue dictionaries.
    """
    def detect(self, code: str, filename: str = "unknown", language: str = "python", **kwargs) -> List[Dict]:
        ...

# Standard Issue Format:
# {
#     "type": str,           # e.g., "security_vulnerability", "code_quality", "ai_placeholder"
#     "severity": str,       # "critical", "high", "medium", "low"
#     "line": int,           # 1-indexed line number
#     "column": int,         # 0-indexed column (optional, default 0)
#     "message": str,        # Detailed description of the issue
#     "suggestion": str,     # How to fix the issue
#     "cwe": str = None,     # CWE ID for security issues
#     "reference_url": str = None # Link to documentation
# }
