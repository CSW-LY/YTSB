# Test LLM fallback functionality
import requests
import json

# API endpoint
url = "http://localhost:8000/api/v1/intent/recognize"

# Test data
payload = {
    "app_key": "plm_assistant",
    "text": "你是谁"
}

# Headers
headers = {
    "Content-Type": "application/json"
}

print("Testing LLM fallback functionality...")
print(f"URL: {url}")
print(f"Payload: {payload}")
print()

try:
    # Send request
    response = requests.post(url, json=payload, headers=headers)
    
    # Print response status
    print(f"Response Status Code: {response.status_code}")
    print(f"Response Headers: {dict(response.headers)}")
    print()
    
    # Parse and print response content
    response_data = response.json()
    print("Response Content:")
    print(json.dumps(response_data, indent=2, ensure_ascii=False))
    print()
    
    # Check if LLM fallback was triggered
    if "recognition_chain" in response_data:
        print("Recognition Chain:")
        for step in response_data["recognition_chain"]:
            print(f"  - Recognizer: {step.get('recognizer')}")
            print(f"    Status: {step.get('status')}")
            print(f"    Intent: {step.get('intent')}")
            print(f"    Confidence: {step.get('confidence')}")
            print(f"    Time: {step.get('time_ms')}ms")
            if step.get('error'):
                print(f"    Error: {step.get('error')}")
            print()
    
    # Check if LLM fallback was used
    if response_data.get("fallback_used"):
        print("✅ LLM fallback was used!")
        print(f"Fallback reason: {response_data.get('fallback_reason')}")
        print(f"Final recognizer: {response_data.get('final_recognizer')}")
    else:
        print("❌ LLM fallback was not used")
        
    # Check if LLM returned "LLM无法匹配"
    if response_data.get("intent") == "LLM无法匹配":
        print("✅ LLM returned 'LLM无法匹配' as expected")
    else:
        print(f"Intent: {response_data.get('intent')}")
        print(f"Confidence: {response_data.get('confidence')}")
        
    # Check if recognition chain includes LLM step
    if "recognition_chain" in response_data:
        llm_steps = [step for step in response_data["recognition_chain"] if step.get('recognizer') == "llm_fallback"]
        if llm_steps:
            print("✅ Recognition chain includes LLM fallback step!")
        else:
            print("❌ Recognition chain does not include LLM fallback step")
            
    # Check if success is False when LLM无法匹配
    if response_data.get("intent") == "LLM无法匹配" and not response_data.get("success"):
        print("✅ Success is False when LLM无法匹配")
    elif response_data.get("intent") == "LLM无法匹配" and response_data.get("success"):
        print("❌ Success should be False when LLM无法匹配")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()