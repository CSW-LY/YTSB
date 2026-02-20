import requests
import json

# 测试 /api/ui/test 端点
url = "http://localhost:8000/api/ui/test"
headers = {"Content-Type": "application/json"}

# 测试数据
test_data = {
    "appKey": "plm_assistant",
    "text": "查找图号为6030201的零部件"
}

print("Testing /api/ui/test endpoint...")
print(f"URL: {url}")
print(f"Data: {json.dumps(test_data, ensure_ascii=False)}")

response = requests.post(url, headers=headers, json=test_data)
print(f"Status code: {response.status_code}")
print(f"Response: {response.text}")

# 测试 /api/v1/intent/recognize 端点
print("\nTesting /api/v1/intent/recognize endpoint...")
url2 = "http://localhost:8000/api/v1/intent/recognize"
headers2 = {"Content-Type": "application/json"}

test_data2 = {
    "app_key": "plm_assistant",
    "text": "查找图号为6030201的零部件"
}

response2 = requests.post(url2, headers=headers2, json=test_data2)
print(f"Status code: {response2.status_code}")
print(f"Response: {response2.text}")