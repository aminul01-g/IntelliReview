#!/usr/bin/env python3
"""
Comprehensive End-to-End Test Suite for IntelliReview
Tests all critical user flows and edge cases
"""

import requests
import time
import sys
from typing import Dict, List

API_URL = "http://localhost:8000/api/v1"

class E2ETestSuite:
    def __init__(self):
        self.passed = 0
        self.failed = 0
        self.token = None
        
    def log_test(self, name: str, passed: bool, details: str = ""):
        if passed:
            self.passed += 1
            print(f"✅ PASS: {name}")
        else:
            self.failed += 1
            print(f"❌ FAIL: {name}")
        if details:
            print(f"   {details}")
    
    def test_registration(self):
        """Test 1: User Registration"""
        print("\n--- Test 1: User Registration ---")
        username = f"testuser_{int(time.time())}"
        resp = requests.post(f"{API_URL}/auth/register", json={
            "username": username,
            "email": f"{username}@test.com",
            "password": "testpass123"
        })
        # 200 or 201 are both acceptable for successful registration
        success = resp.status_code in [200, 201]
        self.log_test("User Registration", success, f"Status: {resp.status_code}")
        return username
    
    def test_login(self, username: str = "demo", password: str = "demo123"):
        """Test 2: User Login"""
        print("\n--- Test 2: User Login ---")
        resp = requests.post(f"{API_URL}/auth/login", data={
            "username": username,
            "password": password
        })
        success = resp.status_code == 200
        if success:
            self.token = resp.json().get('access_token')
        self.log_test("User Login", success, f"Token received: {bool(self.token)}")
        return self.token
    
    def test_invalid_login(self):
        """Test 3: Invalid Login Handling"""
        print("\n--- Test 3: Invalid Login ---")
        resp = requests.post(f"{API_URL}/auth/login", data={
            "username": "invalid_user_xxx",
            "password": "wrong_password"
        })
        self.log_test("Invalid Login Rejection", resp.status_code == 401, f"Status: {resp.status_code}")
    
    def test_multi_language_analysis(self):
        """Test 4-8: Multi-Language Analysis"""
        test_cases = {
            "Python": ("python", "f = open('test.txt')\nprint(f.read())"),
            "Java": ("java", "public class Test {\n    public static void main(String[] args) {\n        while(true) {\n            System.out.println(\"loop\");\n        }\n    }\n}"),
            "JavaScript": ("javascript", "function test(a, b) {\n  if (a == b) { return true; }\n}"),
            "C++": ("cpp", "class Base {\npublic:\n    int* p = new int[10];\n};"),
            "C": ("c", "#include <stdio.h>\nint main() {\n    char buf[10];\n    gets(buf);\n    return 0;\n}")
        }
        
        for lang_name, (lang_key, code) in test_cases.items():
            print(f"\n--- Test: {lang_name} Analysis ---")
            headers = {"Authorization": f"Bearer {self.token}"}
            resp = requests.post(f"{API_URL}/analysis/analyze", 
                json={"code": code, "language": lang_key},
                headers=headers
            )
            success = resp.status_code == 200
            if success:
                data = resp.json()
                issues_found = len(data.get('issues', []))
                has_suggestion = any(issue.get('suggestion') for issue in data.get('issues', []))
                self.log_test(f"{lang_name} Analysis", success, 
                    f"Issues: {issues_found}, Suggestions: {has_suggestion}")
            else:
                self.log_test(f"{lang_name} Analysis", False, f"Status: {resp.status_code}")
    
    def test_expert_format_verification(self):
        """Test 9: Expert SQE Format Verification"""
        print("\n--- Test 9: Expert SQE Format Verification ---")
        code = "def test():\n    x = input()\n    if x > 10:\n        print('large')"
        headers = {"Authorization": f"Bearer {self.token}"}
        resp = requests.post(f"{API_URL}/analysis/analyze",
            json={"code": code, "language": "python"},
            headers=headers
        )
        
        if resp.status_code == 200:
            data = resp.json()
            for issue in data.get('issues', []):
                suggestion = issue.get('suggestion', '')
                if suggestion and len(suggestion) > 100:
                    # Check for expert format markers
                    has_format = (
                        "### 1. Detected Programming Language" in suggestion or
                        "### 2. Total Number of Issues" in suggestion or
                        "Severity Level" in suggestion
                    )
                    self.log_test("Expert SQE Format", has_format, 
                        f"Format markers found: {has_format}")
                    return
        self.log_test("Expert SQE Format", False, "No suitable suggestions to verify")
    
    def test_file_size_limit(self):
        """Test 10: File Size Limit Enforcement"""
        print("\n--- Test 10: File Size Limit (10,000 lines) ---")
        large_code = "\n".join([f"x = {i}" for i in range(10001)])
        headers = {"Authorization": f"Bearer {self.token}"}
        resp = requests.post(f"{API_URL}/analysis/analyze",
            json={"code": large_code, "language": "python"},
            headers=headers
        )
        self.log_test("File Size Limit", resp.status_code == 400, f"Status: {resp.status_code}")
    
    def test_history_retrieval(self):
        """Test 11: Analysis History"""
        print("\n--- Test 11: History Retrieval ---")
        headers = {"Authorization": f"Bearer {self.token}"}
        resp = requests.get(f"{API_URL}/analysis/history", headers=headers)
        success = resp.status_code == 200
        if success:
            history = resp.json()
            self.log_test("History Retrieval", success, f"Records: {len(history)}")
        else:
            self.log_test("History Retrieval", False, f"Status: {resp.status_code}")
    
    def test_feedback_submission(self):
        """Test 12: Feedback Submission"""
        print("\n--- Test 12: Feedback Submission ---")
        headers = {"Authorization": f"Bearer {self.token}"}
        resp = requests.post(f"{API_URL}/feedback/submit",
            json={
                "suggestion_id": "test_id_123",
                "accepted": True,
                "issue_type": "bug"
            },
            headers=headers
        )
        self.log_test("Feedback Submission", resp.status_code == 200, f"Status: {resp.status_code}")
    
    def test_performance(self):
        """Test 13: Performance Testing"""
        print("\n--- Test 13: Performance Test ---")
        code = "def test():\n    x = 10\n    return x"
        headers = {"Authorization": f"Bearer {self.token}"}
        
        start = time.time()
        resp = requests.post(f"{API_URL}/analysis/analyze",
            json={"code": code, "language": "python"},
            headers=headers
        )
        duration = time.time() - start
        
        self.log_test("Performance (<15s)", duration < 15, f"Time: {duration:.2f}s")
    
    def run_all_tests(self):
        print("=" * 60)
        print("IntelliReview - Comprehensive E2E Test Suite")
        print("=" * 60)
        
        # Phase 1: Authentication
        self.test_invalid_login()
        username = self.test_registration()
        self.test_login()
        
        # Phase 2: Core Features
        self.test_multi_language_analysis()
        self.test_expert_format_verification()
        
        # Phase 3: Edge Cases
        self.test_file_size_limit()
        
        # Phase 4: Additional Features
        self.test_history_retrieval()
        self.test_feedback_submission()
        
        # Phase 5: Performance
        self.test_performance()
        
        # Summary
        print("\n" + "=" * 60)
        print(f"Test Summary: {self.passed} passed, {self.failed} failed")
        print("=" * 60)
        
        return self.failed == 0

if __name__ == "__main__":
    suite = E2ETestSuite()
    success = suite.run_all_tests()
    sys.exit(0 if success else 1)
