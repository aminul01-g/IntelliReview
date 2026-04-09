import pytest
from analyzer.detectors.antipatterns import AntiPatternDetector
from analyzer.detectors.security import SecurityScanner
from analyzer.parsers.python_parser import PythonParser


class TestAntiPatternDetector:
    """Test anti-pattern detector."""
    
    def test_detect_long_method(self):
        """Test detecting long methods."""
        detector = AntiPatternDetector()
        parser = PythonParser()
        
        # Create a long function
        code = "def long_func():\n" + "    x = 1\n" * 60
        ast = parser.parse(code)
        
        issues = detector.detect(code, ast, "python")
        
        long_method_issues = [i for i in issues if i["type"] == "long_method"]
        assert len(long_method_issues) > 0
    
    def test_detect_magic_numbers(self):
        """Test detecting magic numbers."""
        detector = AntiPatternDetector()
        parser = PythonParser()
        
        code = "def calculate(): return 42 * 365"
        ast = parser.parse(code)
        
        issues = detector.detect(code, ast, "python")
        
        magic_number_issues = [i for i in issues if i["type"] == "magic_number"]
        assert len(magic_number_issues) > 0


class TestSecurityScanner:
    """Test security scanner."""
    
    def test_detect_hardcoded_password(self):
        """Test detecting hardcoded passwords."""
        scanner = SecurityScanner()
        
        code = 'password = "secret123"'
        
        issues = scanner.scan(code, "test.py", "python")
        
        password_issues = [
            i for i in issues 
            if "password" in i["message"].lower()
        ]
        assert len(password_issues) > 0
    
    def test_detect_sql_injection(self):
        """Test detecting SQL injection vulnerabilities."""
        scanner = SecurityScanner()
        
        code = 'query = "SELECT * FROM users WHERE id = " + user_id'
        
        issues = scanner.scan(code, "test.py", "python")
        
        sql_issues = [
            i for i in issues 
            if "sql" in i["message"].lower()
        ]
        assert len(sql_issues) > 0
    
    def test_no_security_issues(self):
        """Test code with no security issues."""
        scanner = SecurityScanner()
        
        code = "def hello(): return 'world'"
        
        issues = scanner.scan(code, "test.py", "python")
        
        assert len(issues) == 0

