import requests
import sys

API_URL = "http://localhost:8000/api/v1"

def login():
    resp = requests.post(f"{API_URL}/auth/login", data={"username": "demo", "password": "demo123"})
    if resp.status_code != 200:
        print(f"Login FAILED: {resp.status_code} {resp.text}")
        sys.exit(1)
    return {"Authorization": f"Bearer {resp.json()['access_token']}"}

def test_history():
    h = login()
    print("Fetching history...")
    resp = requests.get(f"{API_URL}/analysis/history", headers=h)
    if resp.status_code == 200:
        data = resp.json()
        print(f"History count: {len(data)}")
        if data:
            item = data[0]
            print(f"First item keys: {list(item.keys())}")
            print(f"analysis_id: {item.get('analysis_id')}")
            print(f"suggestions_count: {item.get('suggestions_count')}")
            print(f"analyzed_at: {item.get('analyzed_at')}")
            print(f"processing_time: {item.get('processing_time')}")
            
            # Check if all expected fields for UI are present
            required = ['analysis_id', 'status', 'language', 'file_path', 'issues', 'metrics', 'suggestions_count', 'analyzed_at']
            missing = [f for f in required if f not in item]
            if missing:
                print(f"❌ MISSING FIELDS: {missing}")
            else:
                print("✅ All required fields present.")
    else:
        print(f"History FAILED: {resp.status_code} {resp.text}")

if __name__ == "__main__":
    test_history()
