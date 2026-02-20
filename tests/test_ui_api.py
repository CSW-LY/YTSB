import requests
import json

url = "http://127.0.0.1:8001/api/ui/test"
headers = {"Content-Type": "application/json"}

# Test cases
test_cases = [
    {"appKey": "plm_assistant", "text": "search parts"},
    {"appKey": "plm_assistant", "text": "搜索零件"},
    {"appKey": "plm_assistant", "text": "查找零件"},
    {"appKey": "plm_assistant", "text": "查询BOM"},
    {"appKey": "plm_assistant", "text": "创建零件"},
]

for test_case in test_cases:
    print(f"\nTesting: {test_case['text']}")
    response = requests.post(url, headers=headers, json=test_case)
    print(f"Status: {response.status_code}")
    print(f"Response: {response.text}")
