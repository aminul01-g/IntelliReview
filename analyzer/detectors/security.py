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
    
    # Python-specific dangerous patterns for in-memory regex scanning.
    # Bandit only works on files on disk; these patterns catch critical CWEs
    # when code is analysed via the API (in-memory strings).
    _PYTHON_PATTERNS = [
        (r'\beval\s*\(',
         "Use of eval() detected — allows arbitrary code execution.",
         "Avoid eval(). Use ast.literal_eval() for safe data parsing, or restructure logic entirely.",
         "CWE-95", "high",
         "https://cwe.mitre.org/data/definitions/95.html"),
        (r'\bexec\s*\(',
         "Use of exec() detected — allows arbitrary code execution.",
         "Remove exec() and replace with explicit logic or a safe sandbox.",
         "CWE-95", "high",
         "https://cwe.mitre.org/data/definitions/95.html"),
        (r'\bos\.system\s*\(',
         "os.system() call detected — vulnerable to command injection.",
         "Use subprocess.run() with a list of arguments (no shell=True).",
         "CWE-78", "critical",
         "https://cwe.mitre.org/data/definitions/78.html"),
        (r'\bsubprocess\.\w+\s*\(.*shell\s*=\s*True',
         "subprocess with shell=True enables shell injection attacks.",
         "Pass arguments as a list and remove shell=True.",
         "CWE-78", "high",
         "https://cwe.mitre.org/data/definitions/78.html"),
        (r'\bpickle\.loads?\s*\(',
         "Deserialization of untrusted data via pickle — remote code execution risk.",
         "Use JSON or a safe serialisation format. Never unpickle untrusted data.",
         "CWE-502", "critical",
         "https://cwe.mitre.org/data/definitions/502.html"),
        (r'__import__\s*\(',
         "Dynamic import via __import__() — code injection vector.",
         "Use explicit imports. If dynamic loading is required, validate against an allow-list.",
         "CWE-94", "medium",
         "https://cwe.mitre.org/data/definitions/94.html"),
        (r'yaml\.load\s*\([^)]*\)\s*(?!.*Loader)',
         "yaml.load() without explicit Loader is unsafe — allows code execution.",
         "Use yaml.safe_load() instead of yaml.load().",
         "CWE-502", "high",
         "https://cwe.mitre.org/data/definitions/502.html"),
        (r'\.format\s*\(.*\)\s*$',
         "String .format() used in potential SQL/command context — injection risk.",
         "Use parameterised queries or template engines with auto-escaping.",
         "CWE-89", "medium",
         "https://owasp.org/www-community/attacks/SQL_Injection"),
    ]

    def _scan_python(self, code: str, filename: str) -> List[Dict]:
        """Scan Python code with Bandit + regex fallback."""
        issues = []
        bandit_found = set()  # Track lines Bandit already flagged
        
        try:
            # Use Bandit for Python security analysis
            b_mgr = bandit_manager.BanditManager(bandit.config.BanditConfig(), 'file')
            b_mgr.discover_files([filename], recursive=False)
            b_mgr.run_tests()
            
            for issue in b_mgr.get_issue_list():
                # Bandit's CWE is an object with an id property, not a dict.
                cwe_id = None
                if hasattr(issue, 'cwe') and issue.cwe:
                    cwe_id = getattr(issue.cwe, 'id', None)
                    
                ref_url = f"https://cwe.mitre.org/data/definitions/{cwe_id}.html" if cwe_id else None
                
                issues.append({
                    "type": "security_vulnerability",
                    "severity": issue.severity.lower() if hasattr(issue, 'severity') and issue.severity else "medium",
                    "line": issue.lineno,
                    "message": issue.text,
                    "suggestion": "Review Bandit documentation for mitigation.",
                    "cwe": f"CWE-{cwe_id}" if cwe_id else None,
                    "reference_url": ref_url
                })
                bandit_found.add(issue.lineno)
        
        except Exception as e:
            # Bandit failed (e.g. file not on disk) — regex fallback handles it
            pass
        
        # Always run regex patterns to catch issues Bandit missed (in-memory analysis)
        issues.extend(self._scan_python_regex(code, bandit_found))
        
        return issues
    
    def _scan_python_regex(self, code: str, skip_lines: set = None) -> List[Dict]:
        """Regex-based Python security scanner for in-memory code analysis.
        
        Supplements Bandit by catching dangerous patterns when code is not on disk.
        Skips lines already flagged by Bandit to avoid duplicates.
        """
        issues = []
        skip_lines = skip_lines or set()
        lines = code.split('\n')
        
        for i, line in enumerate(lines, 1):
            if i in skip_lines:
                continue
            stripped = line.strip()
            if stripped.startswith('#'):
                continue  # Skip comments
            
            for pattern, message, suggestion, cwe, severity, ref_url in self._PYTHON_PATTERNS:
                if re.search(pattern, line):
                    issues.append({
                        "type": "security_vulnerability",
                        "severity": severity,
                        "line": i,
                        "message": message,
                        "suggestion": suggestion,
                        "cwe": cwe,
                        "reference_url": ref_url
                    })
        
        # Python-specific SQL injection: string concatenation in queries
        for i, line in enumerate(lines, 1):
            if i in skip_lines:
                continue
            # Catches: "SELECT ... " + variable, f"SELECT ... {var}"
            if re.search(r'["\']SELECT\s.*["\']\s*\+', line, re.IGNORECASE) or \
               re.search(r'f["\']SELECT\s.*\{', line, re.IGNORECASE) or \
               re.search(r'["\']INSERT\s.*["\']\s*\+', line, re.IGNORECASE) or \
               re.search(r'["\']DELETE\s.*["\']\s*\+', line, re.IGNORECASE) or \
               re.search(r'["\']UPDATE\s.*["\']\s*\+', line, re.IGNORECASE):
                issues.append({
                    "type": "security_vulnerability",
                    "severity": "critical",
                    "line": i,
                    "message": "SQL query built via string concatenation — SQL Injection risk.",
                    "suggestion": "Use parameterized queries (e.g., cursor.execute('SELECT ... WHERE id = %s', (id,))).",
                    "cwe": "CWE-89",
                    "reference_url": "https://owasp.org/www-community/attacks/SQL_Injection"
                })
        
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
                    "message": "Use of eval() detected. Allows arbitrary code execution.",
                    "suggestion": "Avoid eval() and replace with safer logic like JSON.parse().",
                    "cwe": "CWE-94",
                    "reference_url": "https://owasp.org/www-community/attacks/Code_Injection"
                })
        
        # Check for innerHTML usage (XSS risk)
        for i, line in enumerate(lines, 1):
            if '.innerHTML' in line and '=' in line:
                issues.append({
                    "type": "security_vulnerability",
                    "severity": "high",
                    "line": i,
                    "message": "Direct innerHTML assignment creates an XSS vulnerability vector.",
                    "suggestion": "Use textContent, DOMPurify, or safe template frameworks to bind external data.",
                    "cwe": "CWE-79",
                    "reference_url": "https://owasp.org/www-community/attacks/xss/"
                })
        
        return issues
    
    def _scan_common(self, code: str) -> List[Dict]:
        """Common security checks for all languages."""
        issues = []
        lines = code.split('\n')
        
        # Hardcoded secrets (CWE-798)
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
                        "message": f"Possible {desc} detected.",
                        "suggestion": "Extract secrets into environment variables (.env) or a Vault.",
                        "cwe": "CWE-798",
                        "reference_url": "https://owasp.org/Top10/A07_2021-Identification_and_Authentication_Failures/"
                    })
        
        # SQL Injection patterns (CWE-89)
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
                        "message": "String concatenation in query detects a direct SQL Injection risk.",
                        "suggestion": "Rewrite using parameterized SQL queries or a safe ORM abstraction.",
                        "cwe": "CWE-89",
                        "reference_url": "https://owasp.org/www-community/attacks/SQL_Injection"
                    })
        
        return issues