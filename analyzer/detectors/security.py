from typing import List, Dict
import re
import bandit
from bandit.core import manager as bandit_manager

class SecurityScanner:
    """Scan code for security vulnerabilities."""
    
    def scan(self, code: str, filename: str = "temp.py", language: str = "python") -> List[Dict]:
        """Scan code for security issues."""
        issues = []
        
        if language == "python":
            issues.extend(self._scan_python(code, filename))
        elif language == "javascript":
            issues.extend(self._scan_javascript(code))
        
        # Common security checks for all languages
        issues.extend(self._scan_common(code))
        
        return issues
    
    def _scan_python(self, code: str, filename: str) -> List[Dict]:
        """Scan Python code with Bandit."""
        issues = []
        
        try:
            # Use Bandit for Python security analysis
            b_mgr = bandit_manager.BanditManager(bandit.config.BanditConfig(), 'file')
            b_mgr.discover_files([filename], recursive=False)
            b_mgr.run_tests()
            
            for issue in b_mgr.get_issue_list():
                issues.append({
                    "type": "security_vulnerability",
                    "severity": issue.severity.lower(),
                    "line": issue.lineno,
                    "message": issue.text,
                    "suggestion": "Review and fix the security issue",
                    "cwe": issue.cwe.get('id') if hasattr(issue, 'cwe') else None
                })
        
        except Exception as e:
            # Fallback to regex-based detection
            pass
        
        return issues
    
    def _scan_javascript(self, code: str) -> List[Dict]:
        """Scan JavaScript for common security issues."""
        issues = []
        lines = code.split('\n')
        
        # Check for eval() usage
        for i, line in enumerate(lines, 1):
            if 'eval(' in line:
                issues.append({
                    "type": "security_vulnerability",
                    "severity": "high",
                    "line": i,
                    "message": "Use of eval() detected",
                    "suggestion": "Avoid eval() as it can execute arbitrary code"
                })
        
        # Check for innerHTML usage (XSS risk)
        for i, line in enumerate(lines, 1):
            if '.innerHTML' in line and '=' in line:
                issues.append({
                    "type": "security_vulnerability",
                    "severity": "medium",
                    "line": i,
                    "message": "Direct innerHTML assignment (XSS risk)",
                    "suggestion": "Use textContent or sanitize input"
                })
        
        return issues
    
    def _scan_common(self, code: str) -> List[Dict]:
        """Common security checks for all languages."""
        issues = []
        lines = code.split('\n')
        
        # Hardcoded secrets
        secret_patterns = [
            (r'password\s*=\s*["\'](.+?)["\']', "hardcoded password"),
            (r'api[_-]?key\s*=\s*["\'](.+?)["\']', "hardcoded API key"),
            (r'secret\s*=\s*["\'](.+?)["\']', "hardcoded secret"),
            (r'token\s*=\s*["\'](.+?)["\']', "hardcoded token"),
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern, desc in secret_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({
                        "type": "security_vulnerability",
                        "severity": "critical",
                        "line": i,
                        "message": f"Possible {desc} detected",
                        "suggestion": "Use environment variables or secure credential storage"
                    })
        
        # SQL Injection patterns
        sql_patterns = [
            r'execute\s*\(\s*["\'].*%s.*["\']',
            r'query\s*\(\s*["\'].*\+.*["\']',
        ]
        
        for i, line in enumerate(lines, 1):
            for pattern in sql_patterns:
                if re.search(pattern, line, re.IGNORECASE):
                    issues.append({
                        "type": "security_vulnerability",
                        "severity": "critical",
                        "line": i,
                        "message": "Possible SQL injection vulnerability",
                        "suggestion": "Use parameterized queries or ORM"
                    })
        
        return issues