import requests
import sys

API_URL = "http://localhost:8000/api/v1"

def login():
    resp = requests.post(f"{API_URL}/auth/login", data={"username": "demo", "password": "demo123"})
    if resp.status_code != 200:
        print(f"Login FAILED: {resp.status_code} {resp.text}")
        sys.exit(1)
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}

def test_language(lang, code):
    print(f"\n--- Testing {lang.upper()} Analysis ---")
    headers = login()
    payload = {"code": code, "language": lang, "file_path": f"test.{lang}"}
    resp = requests.post(f"{API_URL}/analysis/analyze", json=payload, headers=headers)
    if resp.status_code == 200:
        data = resp.json()
        print(f"SUCCESS: Found {len(data['issues'])} issues.")
        for issue in data['issues']:
            print(f"  [{issue['severity']}] Line {issue['line']}: {issue['message']}")
            if issue.get('suggestion') and len(issue['suggestion']) > 100:
                 print(f"    💡 SQE Expert Suggestion found (length: {len(issue['suggestion'])})")
                 if "### 1. Detected Programming Language" in issue['suggestion']:
                     print("    ✅ Expert Output Format Verified!")
    else:
        print(f"FAILED: {resp.status_code} {resp.text}")

# JS Example: console.log and ==
js_code = """
function test(a, b) {
  if (a == b) {
    console.log("Equal");
  }
}
"""

# Java Example: System.out.println and potential logic bugs
java_code = """
public class Main {
    public static void main(String[] args) {
        System.out.println("Hello World");
        int x = 10;
        if x > 5 { // Syntax error handled by expert prompt
             System.out.println("X is large");
        }
    }
}
"""

# C++ Example: missing virtual destructor
cpp_code = """
class Base {
public:
    void risky() {
        int* p = new int[10]; // Memory leak (expert DQ)
    }
};
"""

# C Example: Unsafe gets
c_code = """
#include <stdio.h>
int main() {
    char buf[10];
    gets(buf); // Dangerous function
    return 0;
}
"""

if __name__ == "__main__":
    test_language("python", "def test():\n    f = open('test.txt')\n    return 0")
    test_language("javascript", js_code)
    test_language("java", java_code)
    test_language("cpp", cpp_code)
    test_language("c", c_code)
