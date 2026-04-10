import sys
import threading
import time
import requests
import uvicorn
from api.main import app

def run_server():
    uvicorn.run(app, host="127.0.0.1", port=8002, log_level="error")

def test():
    time.sleep(2)
    # create 105 files
    files = [('files', ('test.txt', b'hello', 'text/plain')) for _ in range(105)]
    try:
        response = requests.post("http://127.0.0.1:8002/api/v1/analysis/upload", files=files)
        print("Status", response.status_code)
        print("Response Text:", response.text)
    except Exception as e:
        print("Error:", e)
    
    import os, signal
    os.kill(os.getpid(), signal.SIGTERM)

if __name__ == "__main__":
    t = threading.Thread(target=run_server, daemon=True)
    t.start()
    test()
