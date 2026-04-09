import requests
import sys

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

def test_ai_suggestion(headers):
    print("\n--- Testing AI Suggestion Generation ---")
    code = """
x = input("Enter a number: ")
if x == 10:
    print("Ten")
"""
    print("Sending analysis request...")
    resp = requests.post(f"{API_URL}/analysis/analyze", json={
        "code": code,
        "language": "python",
        "file_path": "buggy.py"
    }, headers=headers)
    
    if resp.status_code != 200:
        print(f"Analysis FAILED: {resp.status_code} {resp.text}")
        return

    data = resp.json()
    print(f"Status: {resp.status_code}")
    print(f"Issues Found: {len(data.get('issues', []))}")
    
    found_ai_suggestion = False
    for issue in data.get('issues', []):
        print(f"  [{issue['severity']}] Line {issue['line']}: {issue['message']}")
        if issue.get('suggestion') and "Error generating suggestion" not in issue['suggestion']:
            print(f"    💡 AI Suggestion found: {issue['suggestion'][:100]}...")
            found_ai_suggestion = True
        elif issue.get('suggestion') and "Error generating suggestion" in issue['suggestion']:
            print(f"    ❌ AI Suggestion Error: {issue['suggestion']}")

    if found_ai_suggestion:
        print("\n✅ SUCCESS: AI suggestion generated correctly!")
    else:
        print("\n❌ FAILED: No valid AI suggestion generated.")

if __name__ == "__main__":
    h = login()
    test_ai_suggestion(h)
