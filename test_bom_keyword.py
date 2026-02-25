import requests
import json
import time

# API endpoint
url = "http://localhost:8000/api/v1/intent/recognize"

# Test data for BOM
payload_bom = {
    "app_key": "plm_assistant",
    "text": "查看bom123"
}

# Test data for part search
payload_part = {
    "app_key": "plm_assistant",
    "text": "查找一个螺栓"
}

headers = {
    "Content-Type": "application/json"
}

print("Testing BOM keyword matching...")
print(f"URL: {url}")
print()

# Test BOM input
print("=== Testing '查看bom123' ===")
start_time = time.time()
try:
    response = requests.post(url, json=payload_bom, headers=headers, timeout=30)
    end_time = time.time()
    response_time = (end_time - start_time) * 1000
    
    print(f"Response time: {response_time:.2f}ms")
    print(f"Status code: {response.status_code}")
    print(f"Response content: {response.text}")
    print()
    
    # Parse response
    data = response.json()
    print(f"Matched intent: {data.get('intent')}")
    print(f"Confidence: {data.get('confidence')}")
    print(f"Fallback used: {data.get('fallback_used')}")
    print(f"Processing time: {data.get('processing_time_ms')}ms")
    print(f"Recognition chain: {json.dumps(data.get('recognition_chain'), indent=2, ensure_ascii=False)}")
    print()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

# Test part search input
print("=== Testing '查找一个螺栓' ===")
start_time2 = time.time()
try:
    response2 = requests.post(url, json=payload_part, headers=headers, timeout=30)
    end_time2 = time.time()
    response_time2 = (end_time2 - start_time2) * 1000
    
    print(f"Response time: {response_time2:.2f}ms")
    print(f"Status code: {response2.status_code}")
    print(f"Response content: {response2.text}")
    print()
    
    # Parse response
    data2 = response2.json()
    print(f"Matched intent: {data2.get('intent')}")
    print(f"Confidence: {data2.get('confidence')}")
    print(f"Fallback used: {data2.get('fallback_used')}")
    print(f"Processing time: {data2.get('processing_time_ms')}ms")
    print(f"Recognition chain: {json.dumps(data2.get('recognition_chain'), indent=2, ensure_ascii=False)}")
    print()
    
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()

print("=== Summary ===")
print(f"'查看bom123' response time: {response_time:.2f}ms")
print(f"'查找一个螺栓' response time: {response_time2:.2f}ms")
