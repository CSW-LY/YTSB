import requests
import json

# 测试"查找一个螺栓"的意图识别
url = "http://localhost:8000/api/v1/intent/recognize"
headers = {
    "Content-Type": "application/json"
}

data = {
    "app_key": "plm_assistant",
    "text": "查找一个螺栓"
}

print("测试意图识别: 查找一个螺栓")
print("=" * 50)

try:
    response = requests.post(url, headers=headers, json=data, timeout=30)
    response.raise_for_status()
    result = response.json()
    
    print(f"状态码: {response.status_code}")
    print(f"识别结果: {json.dumps(result, ensure_ascii=False, indent=2)}")
    
    # 检查是否识别到SEARCH_PART
    if result.get("success"):
        intent = result.get("intent")
        print(f"\n识别的意图: {intent}")
        if intent == "SEARCH_PART":
            print("✓ 成功识别为SEARCH_PART分类!")
        else:
            print(f"✗ 识别错误，期望SEARCH_PART，实际得到{intent}")
    else:
        print("✗ 识别失败")
        print(f"失败原因: {result.get('error_message')}")
        
except Exception as e:
    print(f"✗ 请求失败: {e}")

print("=" * 50)