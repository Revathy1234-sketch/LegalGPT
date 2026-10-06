import os
from dotenv import load_dotenv
import sys

# Change directory context so app imports work
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

load_dotenv(".env")

try:
    from app.services.llm_service import LLMService
    from app.core.config import settings
except ImportError as e:
    print(f"Failed to import modules: {e}")
    sys.exit(1)

print("Starting LLM Production Readiness Verification...\n")
print(f"Configured NVIDIA API Key Length: {len(settings.NVIDIA_API_KEY) if settings.NVIDIA_API_KEY else 0}")
print(f"Configured NVIDIA Model: {settings.NVIDIA_MODEL}")

if not settings.NVIDIA_API_KEY or "replace_with" in settings.NVIDIA_API_KEY:
    print("ERROR: NVIDIA_API_KEY is missing or invalid in .env")
    sys.exit(1)

print("\nAttempting to invoke LLMService using NVIDIA...")
try:
    # Use LLMService standard chat payload
    response, usage = LLMService.invoke(
        prompt="Reply with the exact word 'SUCCESS' and nothing else.",
        inputs={},
        require_json=False
    )
    print(f"LLM Response: {response}")
    print(f"Token Usage: {usage}")
    if response and "SUCCESS" in str(response):
        print("LLM Connection: PASS")
    else:
        print("LLM Connection: FAIL (Unexpected response)")
except Exception as e:
    print(f"LLM Connection: FAIL ({type(e).__name__}: {str(e)})")
    sys.exit(1)
