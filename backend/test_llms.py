import sys
import os
import json
import time
import traceback

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from app.services.llm_service import LLMService

def test_provider(provider_name, invoke_method):
    start = time.time()
    result_data = {
        "PROVIDER": provider_name,
        "KEY PRESENT": "YES",
        "STATUS": "FAIL"
    }
    try:
        print(f"Testing {provider_name}...")
        prompt = "Reply with 'OK'."
        text, usage = invoke_method(prompt, {})
        result_data["RESPONSE"] = text.strip()
        result_data["STATUS"] = "PASS"
        
        # Test JSON
        print(f"Testing {provider_name} JSON...")
        json_prompt = "Reply with a valid JSON object with a single key 'status' and value 'OK'."
        json_text, json_usage = invoke_method(json_prompt, {}, require_json=True)
        try:
            json.loads(json_text)
            result_data["JSON SUPPORT"] = "PASS"
        except Exception:
            result_data["JSON SUPPORT"] = "FAIL"
            
        result_data["ERROR"] = "NONE"
    except Exception as e:
        print("TRACEBACK:")
        traceback.print_exc()
        result_data["ERROR"] = str(e)
        result_data["RESPONSE"] = "N/A"
        result_data["JSON SUPPORT"] = "N/A"
    
    latency = time.time() - start
    result_data["LATENCY"] = f"{latency:.2f}s"
    print(f"Result for {provider_name}: {result_data}")
    return result_data

if __name__ == "__main__":
    results = []
    results.append(test_provider("NVIDIA", LLMService._invoke_nvidia))
    results.append(test_provider("OpenRouter", LLMService._invoke_openrouter))
    results.append(test_provider("Gemini", LLMService._invoke_gemini))
    
    print("\n\n--- FINAL RESULTS ---")
    for r in results:
        print(r)
