import sys
import os
import json
import time
import requests

API_URL = "http://localhost:8000/api/v1"

def login():
    print("Logging in...")
    resp = requests.post(f"{API_URL}/auth/login", data={"username": "demo", "password": "demo123"})
    if resp.status_code != 200:
        print(f"Login FAILED: {resp.status_code} {resp.text}")
        sys.exit(1)
    token = resp.json()["access_token"]
    print("Login successful.")
    return {"Authorization": f"Bearer {token}"}

def test_python_analysis(headers):
    print("\n--- Testing Python Analysis ---")
    code = """
def untyped_function(x):
    print(x)
    return x

def main():
    untyped_function(10)
    uncalled_function
    """
    resp = requests.post(f"{API_URL}/analysis/analyze", json={
        "code": code,
        "language": "python",
        "file_path": "test.py"
    }, headers=headers)
    data = resp.json()
    print(f"Status: {resp.status_code}")
    print(f"Processing Time: {data.get('processing_time')}s")
    print(f"Issues Found: {len(data.get('issues', []))}")
    for issue in data.get('issues', []):
        print(f"  [{issue['severity']}] Line {issue['line']}: {issue['message']}")

def test_javascript_analysis(headers):
    print("\n--- Testing JavaScript Analysis ---")
    code = """
function test(x) {
    if (x == 10) {
        console.log("Ten");
    }
}
    """
    resp = requests.post(f"{API_URL}/analysis/analyze", json={
        "code": code,
        "language": "javascript",
        "file_path": "test.js"
    }, headers=headers)
    data = resp.json()
    print(f"Status: {resp.status_code}")
    print(f"Issues Found: {len(data.get('issues', []))}")
    for issue in data.get('issues', []):
        print(f"  [{issue['severity']}] Line {issue['line']}: {issue['message']}")

def test_java_analysis(headers):
    print("\n--- Testing Java Analysis ---")
    code = """
public class Test {
    public void run() {
        System.out.println("Running");
        if (true) { if (true) { if (true) { if (true) { System.out.println("Deep"); } } } }
    }
}
    """
    resp = requests.post(f"{API_URL}/analysis/analyze", json={
        "code": code,
        "language": "java",
        "file_path": "Test.java"
    }, headers=headers)
    # Note: Java might still be in progress/partial in some parsers if not fully wired
    print(f"Status: {resp.status_code}")
    if resp.status_code == 200:
        data = resp.json()
        print(f"Issues Found: {len(data.get('issues', []))}")

def test_constraints(headers):
    print("\n--- Testing 10,000 Line Constraint ---")
    large_code = "print('hello')\n" * 10001
    resp = requests.post(f"{API_URL}/analysis/analyze", json={
        "code": large_code,
        "language": "python"
    }, headers=headers)
    print(f"Large File Status: {resp.status_code} (Expected 400)")
    print(f"Response: {resp.text}")

def test_duplication_vector(headers):
    print("\n--- Testing Vector-based Duplication ---")
    code = """
def block_alpha():
    x = 10
    y = 20
    z = x + y
    print(f"Result is {z}")
    return z

def another_unrelated():
    pass

def block_beta_modified():
    # Slightly modified but similar structure
    a = 10
    b = 20
    c = a + b
    print(f"Total is {c}")
    return c
    """
    resp = requests.post(f"{API_URL}/analysis/analyze", json={
        "code": code,
        "language": "python"
    }, headers=headers)
    data = resp.json()
    dups = [i for i in data.get('issues', []) if i['type'] == 'code_duplication']
    print(f"Status: {resp.status_code}")
    print(f"Duplications Found: {len(dups)}")
    for d in dups:
        print(f"  Similarity Block Found at line {d['line']}: {d['message']}")

if __name__ == "__main__":
    h = login()
    test_python_analysis(h)
    test_javascript_analysis(h)
    test_java_analysis(h)
    test_constraints(h)
    test_duplication_vector(h)
