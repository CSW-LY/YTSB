import requests
import json

# API endpoint
url = "http://localhost:8000/api/v1/intent/recognize"

# Test data
payload = {
    "app_key": "plm_assistant",
    "text": "找一个螺栓"
}

# Headers
headers = {
    "Content-Type": "application/json"
}

print("Testing '找一个螺栓' recognition...")
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
        print("❌ LLM returned 'LLM无法匹配'")
    else:
        print(f"Intent: {response_data.get('intent')}")
        print(f"Confidence: {response_data.get('confidence')}")
        
    # Check if it matched part.search
    if response_data.get("intent") == "part.search":
        print("✅ Success! Matched to part.search category")
    else:
        print("❌ Failed to match to part.search category")
        
except Exception as e:
    print(f"Error: {e}")
    import traceback
    traceback.print_exc()