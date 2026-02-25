import requests
import json
import time

# API endpoint
url = "http://localhost:8000/api/v1/intent/recognize"

# Test data
payload = {
    "app_key": "plm_assistant",
    "text": "查找一个螺栓"
}

headers = {
    "Content-Type": "application/json"
}

print("Testing first request response time...")
print(f"URL: {url}")
print(f"Payload: {payload}")
print()

# Test first request
start_time = time.time()
try:
    response = requests.post(url, json=payload, headers=headers, timeout=60)
    end_time = time.time()
    response_time = (end_time - start_time) * 1000
    
    print(f"First request response time: {response_time:.2f}ms")
    print(f"Status code: {response.status_code}")
    print(f"Response content: {response.text}")
    print()
    
    # Test second request to compare
    print("Testing second request response time...")
    start_time2 = time.time()
    response2 = requests.post(url, json=payload, headers=headers, timeout=60)
    end_time2 = time.time()
    response_time2 = (end_time2 - start_time2) * 1000
    
    print(f"Second request response time: {response_time2:.2f}ms")
    print(f"Status code: {response2.status_code}")
    print(f"Response content: {response2.text}")
    print()
    
    print("=== Summary ===")
    print(f"First request: {response_time:.2f}ms")
    print(f"Second request: {response_time2:.2f}ms")
    print(f"Difference: {abs(response_time - response_time2):.2f}ms")
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()
