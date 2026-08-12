import pytest
from app.services.llm_service import LLMService
from app.core.config import settings

def test_gemini():
    passed = False
    error_msg = ""
    try:
        res, usage = LLMService._invoke_gemini("Say hello in one short sentence.", {})
        if res:
            passed = True
        else:
            error_msg = "Empty response"
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"

    if passed:
        print("\nGEMINI: PASS")
    else:
        print(f"\nGEMINI: FAIL ({error_msg})")
    assert passed, error_msg

def test_nvidia():
    passed = False
    error_msg = ""
    try:
        res, usage = LLMService._invoke_nvidia("Say hello in one short sentence.", {})
        if res:
            passed = True
        else:
            error_msg = "Empty response"
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"

    if passed:
        print("\nNVIDIA: PASS")
    else:
        print(f"\nNVIDIA: FAIL ({error_msg})")
    assert passed, error_msg

def test_openrouter():
    passed = False
    error_msg = ""
    try:
        res, usage = LLMService._invoke_openrouter("Say hello in one short sentence.", {})
        if res:
            passed = True
        else:
            error_msg = "Empty response"
    except Exception as e:
        error_msg = f"{type(e).__name__}: {e}"

    if passed:
        print("\nOPENROUTER: PASS")
    else:
        print(f"\nOPENROUTER: FAIL ({error_msg})")
    assert passed, error_msg
