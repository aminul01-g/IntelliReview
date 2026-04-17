import re
import math
from typing import List

class SecretRedactor:
    """
    Redacts sensitive secrets and API keys from code and diffs before sending to AI endpoints.
    """
    
    # Common patterns for API keys, tokens, and secrets
    PATTERNS = [
        # AWS Access Key
        re.compile(r'(A3T[A-Z0-9]|AKIA|AGPA|AIDA|AROA|AIPA|ANPA|ANVA|ASIA)[A-Z0-9]{16}'),
        # GitHub Token
        re.compile(r'(gh[pousr]_[A-Za-z0-9_]{36,})'),
        # Generic API Key/Token/Secret assignments (heuristics)
        re.compile(r'(?i)(?:api[_-]?key|secret|token|password|pwd|auth)(?:[ "\']*\s*[:=]\s*[ "\']*)([A-Za-z0-9_\\\-]{16,})([ "\']*)'),
        # Generic Bearer token
        re.compile(r'(?i)bearer\s+([A-Za-z0-9_\-\.]{16,})'),
        # Google Cloud/API Keys
        re.compile(r'AIza[0-9A-Za-z\-_]{35}'),
        # Slack Tokens
        re.compile(r'xox[baprs]-[0-9]{12}-[0-9]{12}-[a-zA-Z0-9]{24}'),
        # JWT Token baseline heuristic
        re.compile(r'eyJ[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}\.[A-Za-z0-9_-]{10,}')
    ]
    
    @classmethod
    def calculate_entropy(cls, string: str) -> float:
        """Calculate Shannon entropy of a string."""
        prob = [float(string.count(c)) / len(string) for c in dict.fromkeys(list(string))]
        entropy = - sum([p * math.log(p) / math.log(2.0) for p in prob])
        return entropy

    @classmethod
    def redact_code(cls, code: str) -> str:
        """
        Scans code and masks potential secrets with [REDACTED_SECRET].
        """
        redacted = code
        
        # Apply specific matching explicitly
        for pattern in cls.PATTERNS:
            # Special handling for capture groups in generic regex
            if pattern.groups == 2:
                # This pattern matches something like apiKey = "SECRET"
                def replace_heuristic(match):
                    secret_val = match.group(1)
                    # Check entropy to reduce false positives on generic assignments
                    if cls.calculate_entropy(secret_val) > 3.0:
                        return match.group(0).replace(secret_val, "[REDACTED_SECRET]")
                    return match.group(0)
                redacted = pattern.sub(replace_heuristic, redacted)
            elif pattern.groups == 1:
                # This pattern matches exactly 1 group (like Bearer SECRET)
                def replace_single_group(match):
                    secret_val = match.group(1)
                    if cls.calculate_entropy(secret_val) > 3.0:
                        return match.group(0).replace(secret_val, "[REDACTED_SECRET]")
                    return match.group(0)
                redacted = pattern.sub(replace_single_group, redacted)
            else:
                # Direct match, usually standard keys like AWS or Google
                redacted = pattern.sub("[REDACTED_SECRET]", redacted)
                
        return redacted
