#!/usr/bin/env python3
"""
Test syntax error detection across all languages
"""

import requests
import sys

API_URL = "http://localhost:8000/api/v1"

def login():
    resp = requests.post(f"{API_URL}/auth/login", data={"username": "demo", "password": "demo123"})
    if resp.status_code != 200:
        print(f"Login FAILED: {resp.status_code}")
        sys.exit(1)
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}

def test_syntax_error(lang, code, description):
    print(f"\n--- Testing {description} ---")
    headers = login()
    resp = requests.post(f"{API_URL}/analysis/analyze",
        json={"code": code, "language": lang},
        headers=headers
    )
    
    if resp.status_code == 200:
        data = resp.json()
        issues = data.get('issues', [])
        syntax_errors = [i for i in issues if i['type'] == 'syntax_error']
        
        if syntax_errors:
            print(f"✅ PASS: Detected {len(syntax_errors)} syntax error(s)")
            for err in syntax_errors:
                print(f"   Line {err['line']}: {err['message']}")
        else:
            print(f"❌ FAIL: No syntax errors detected! Found {len(issues)} issues of other types.")
            for issue in issues:
                print(f"   [{issue['type']}] {issue['message']}")
    else:
        print(f"❌ FAIL: API error {resp.status_code}")

# User's C++ example with multiple syntax errors
cpp_broken = """#include<iostream>
using namespace std
int main(
{
cout < "hello wold" <endl;
return 0,
}"""

# Python syntax error
python_broken = """def test()
    x = 10
    if x > 5
        print("large"
"""

# JavaScript syntax error
js_broken = """function test(a, b {
  if (a == b
    console.log("equal")
}"""

# Java syntax error
java_broken = """public class Test {
    public static void main(String[] args
        System.out.println("test")
    }
}"""

if __name__ == "__main__":
    print("="*60)
    print("Syntax Error Detection Test Suite")
    print("="*60)
    
    test_syntax_error("cpp", cpp_broken, "C++ Multiple Errors")
    test_syntax_error("python", python_broken, "Python Missing Colon")
    test_syntax_error("javascript", js_broken, "JavaScript Missing Bracket")
    test_syntax_error("java", java_broken, "Java Missing Parenthesis")
    
    print("\n" + "="*60)
    print("Test Complete!")
    print("="*60)
