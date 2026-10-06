"""Central configuration and response helpers for the primary LLM providers."""

import logging
import httpx
import time
from typing import Any, Dict, Tuple
from app.core.config import settings

try:
    from langchain_google_genai import ChatGoogleGenerativeAI
except ImportError:  # pragma: no cover - fallback for minimal environments
    ChatGoogleGenerativeAI = None

try:
    from openai import OpenAI
except ImportError:  # pragma: no cover - fallback for minimal environments
    OpenAI = None

try:
    from google.api_core.exceptions import ResourceExhausted
except ImportError:  # pragma: no cover - fallback for minimal environments
    ResourceExhausted = None

logger = logging.getLogger(__name__)


class LLMProviderException(Exception):
    """Custom exception raised when LLM providers are unavailable or fail."""
    pass


# Monkeypatch langchain_google_genai retry decorator to avoid internal tenacity retries
try:
    import langchain_google_genai.chat_models as langchain_chat_models
    import tenacity

    def _create_no_retry_decorator() -> tenacity.retry:
        return tenacity.retry(
            reraise=True,
            stop=tenacity.stop_after_attempt(1),
            retry=tenacity.retry_if_exception_type(Exception),
        )

    langchain_chat_models._create_retry_decorator = _create_no_retry_decorator
    logger.info("Successfully monkeypatched langchain_google_genai to disable internal tenacity retries.")
except Exception as patch_err:
    logger.warning("Could not monkeypatch langchain_google_genai retry decorator: %s", patch_err)



class LLMService:
    @staticmethod
    def get_model(require_json: bool = False) ->  Any:
        model_kwargs = {"response_mime_type": "application/json"} if require_json else {}
        return ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0,
            max_output_tokens=1500,
            timeout=180,
            max_retries=0,
            model_kwargs=model_kwargs
        )

    @staticmethod
    def get_openrouter_client() -> Any:
        """Create an OpenRouter client.

        Validates that the OpenAI SDK is available and that the
        ``OPENROUTER_API_KEY`` setting is non‑empty. Raises a clear
        ``RuntimeError`` if the client cannot be instantiated.
        """
        if OpenAI is None:
            raise RuntimeError("OpenRouter client is unavailable (OpenAI SDK not installed)")
        if not settings.OPENROUTER_API_KEY:
            raise RuntimeError("OpenRouter API key is missing in environment configuration")
        base_url = settings.OPENROUTER_BASE_URL or "https://openrouter.ai/api/v1"
        return OpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url=base_url,
            timeout=180.0,
        )

    @staticmethod
    def get_nvidia_client() -> Any:
        """Create an NVIDIA client.

        Validates that the OpenAI SDK is available and that the
        ``NVIDIA_API_KEY`` setting is non‑empty. Raises a clear
        ``RuntimeError`` if the client cannot be instantiated.
        """
        if OpenAI is None:
            raise RuntimeError("NVIDIA client is unavailable (OpenAI SDK not installed)")
        if not settings.NVIDIA_API_KEY:
            raise RuntimeError("NVIDIA API key is missing in environment configuration")
        base_url = settings.NVIDIA_BASE_URL or "https://integrate.api.nvidia.com/v1"
        return OpenAI(
            api_key=settings.NVIDIA_API_KEY,
            base_url=base_url,
            timeout=180.0,
        )

    @staticmethod
    def unpack_response(response: Any) -> Tuple[str, Dict[str, int]]:
        """Return text and normalized token usage from a provider response."""

        def extract_text(resp: Any) -> str:
            def is_mock(obj: Any) -> bool:
                return type(obj).__name__ in ("MagicMock", "Mock", "NonCallableMagicMock", "NonCallableMock")

            if hasattr(resp, "choices") and isinstance(resp.choices, (list, tuple)) and resp.choices:
                msg = getattr(resp.choices[0], "message", None)
                if msg is not None:
                    content = getattr(msg, "content", None)
                    if content is not None and not is_mock(content) and content != "":
                        if isinstance(content, list):
                            return "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in content)
                        return str(content)
                    return ""
            if hasattr(resp, "content") and resp.content is not None and not is_mock(resp.content):
                if isinstance(resp.content, list):
                    return "".join(part.get("text", "") if isinstance(part, dict) else str(part) for part in resp.content)
                return str(resp.content)
            if hasattr(resp, "text") and resp.text is not None and not is_mock(resp.text):
                return str(resp.text)
            return str(resp) if resp is not None and not is_mock(resp) else ""

        def extract_usage(resp: Any) -> Dict[str, int]:
            # Flatten potential sources of usage info
            sources = []
            if isinstance(resp, dict):
                sources.append(resp)
                sources.append(resp.get("usage", {}))
                sources.append(resp.get("usage_metadata", {}))
            if hasattr(resp, "usage"):
                sources.append(resp.usage)
            if hasattr(resp, "usage_metadata"):
                sources.append(resp.usage_metadata)
            if hasattr(resp, "response_metadata"):
                sources.append(resp.response_metadata)

            def get_int(obj: Any, keys: list[str]) -> int:
                for key in keys:
                    val = (obj.get(key) if isinstance(obj, dict) else getattr(obj, key, None))
                    if val is not None:
                        try: return int(val)
                        except (ValueError, TypeError): continue
                return 0

            input_toks = get_int(resp, ["input_tokens", "prompt_tokens", "prompt_token_count", "input_token_count"])
            output_toks = get_int(resp, ["output_tokens", "completion_tokens", "candidates_token_count", "completion_token_count", "output_token_count"])
            total_toks = get_int(resp, ["total_tokens", "total_token_count"]) or (input_toks + output_toks)

            return {"input_tokens": input_toks, "output_tokens": output_toks, "total_tokens": total_toks}

        text = extract_text(response)
        if not text or not text.strip():
            raise RuntimeError("Empty model response received; cannot proceed.")
        return text, extract_usage(response)

    @staticmethod
    def _is_quota_error(exc: Exception) -> bool:
        if ResourceExhausted is not None and isinstance(exc, ResourceExhausted):
            return True
        exc_type = type(exc).__name__
        if exc_type == "RateLimitError":
            return True
        lowered = str(exc).lower()
        return any(
            token in lowered
            for token in ["429", "quota", "resourceexhausted", "rate limit", "per minute"]
        )

    @staticmethod
    def _is_fallback_error(exc: Exception) -> bool:
        """Determine if an exception should trigger a fallback to the next provider.
        Fallback should happen for provider/API failures, timeout, quota/rate-limit,
        service unavailable, or empty response.
        """
        if isinstance(exc, RuntimeError) and "Empty model response received" in str(exc):
            return True

        if isinstance(exc, ValueError) and "missing in environment configuration" in str(exc):
            return True

        exc_type = type(exc).__name__
        if exc_type in ("RateLimitError", "APITimeoutError", "APIConnectionError", "APIStatusError", "APIError"):
            return True

        if isinstance(exc, (httpx.HTTPStatusError, httpx.RequestError)):
            return True

        if LLMService._is_quota_error(exc) or LLMService._is_network_timeout_error(exc):
            return True

        if isinstance(exc, RuntimeError) and "client is unavailable" in str(exc):
            return True

        return False

    @staticmethod
    def _is_network_timeout_error(exc: Exception) -> bool:
        exc_type = type(exc).__name__
        if exc_type in ("APITimeoutError", "APIConnectionError"):
            return True
        lowered = str(exc).lower()
        return any(
            token in lowered
            for token in ["timeout", "timed out", "connection", "api unavailable", "service unavailable", "temporarily unavailable"]
        )

    @staticmethod
    def _is_retryable_error(exc: Exception) -> bool:
        return LLMService._is_quota_error(exc) or LLMService._is_network_timeout_error(exc)

    @staticmethod
    def _get_backoff_seconds(attempt: int) -> float:
        return 1.0 if attempt == 0 else 2.0

    @staticmethod
    def _render_prompt(prompt: Any, inputs: Dict[str, Any]) -> str:
        if hasattr(prompt, "format"):
            try:
                return prompt.format(**inputs)
            except TypeError:
                return prompt.format(inputs)
        if hasattr(prompt, "format_prompt"):
            return prompt.format_prompt(**inputs).to_string()
        return str(prompt)

    @classmethod
    def _invoke_gemini(cls, prompt: Any, inputs: Dict[str, Any], require_json: bool = False) -> Tuple[str, Dict[str, int]]:
        if ChatGoogleGenerativeAI is None:
            raise RuntimeError("Gemini client is unavailable")

        # Quota errors: 0 retries (1 attempt total)
        # Temporary network/timeout errors: 1 retry (2 attempts total)
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                logger.info("Using Gemini for LLM invocation (attempt %s)", attempt + 1)
                model = cls.get_model(require_json=require_json)
                # If the prompt is a plain string (as in unit tests), invoke the model directly.
                if isinstance(prompt, str):
                    response = model.invoke(cls._render_prompt(prompt, inputs))
                else:
                    # For LangChain PromptTemplate objects use the pipe operator.
                    response = (prompt | model).invoke(inputs)
                return cls.unpack_response(response)
            except Exception as exc:
                is_quota = cls._is_quota_error(exc)
                is_network = cls._is_network_timeout_error(exc)

                # If not retryable or a quota error, raise immediately to fall back.
                if not (is_quota or is_network) or is_quota:
                    raise

                # For network/timeout errors, check if we've exhausted all retries
                if attempt >= max_attempts - 1:
                    raise

                logger.warning(
                    "Gemini temporary network/timeout error (attempt %s failed): %s; backing off and retrying",
                    attempt + 1,
                    exc,
                )
                time.sleep(cls._get_backoff_seconds(attempt))

        raise RuntimeError("Gemini unavailable after retries")

    @classmethod
    def _invoke_nvidia(cls, prompt: Any, inputs: Dict[str, Any], require_json: bool = False) -> Tuple[str, Dict[str, int]]:
        client = cls.get_nvidia_client()
        rendered_prompt = cls._render_prompt(prompt, inputs)
        max_attempts = 2
        kwargs = {}
        if require_json:
            kwargs["response_format"] = {"type": "json_object"}

        for attempt in range(max_attempts):
            try:
                logger.info("Using NVIDIA for LLM invocation (attempt %s)", attempt + 1)
                response = client.chat.completions.create(
                    model=settings.NVIDIA_MODEL,
                    messages=[{"role": "user", "content": rendered_prompt}],
                    temperature=0,
                    max_tokens=4096,
                    timeout=180,
                    **kwargs
                )
                return cls.unpack_response(response)
            except Exception as exc:
                is_quota = cls._is_quota_error(exc)
                is_network = cls._is_network_timeout_error(exc)

                if not (is_quota or is_network) or is_quota:
                    raise

                if attempt >= max_attempts - 1:
                    raise

                logger.warning(
                    "NVIDIA temporary network/timeout error (attempt %s failed): %s; backing off and retrying",
                    attempt + 1,
                    exc,
                )
                time.sleep(cls._get_backoff_seconds(attempt))

        raise RuntimeError("NVIDIA unavailable after retries")

    @classmethod
    def _invoke_openrouter(cls, prompt: Any, inputs: Dict[str, Any], require_json: bool = False) -> Tuple[str, Dict[str, int]]:
        client = cls.get_openrouter_client()
        max_attempts = 2
        kwargs = {}
        if require_json:
            kwargs["response_format"] = {"type": "json_object"}

        for attempt in range(max_attempts):
            try:
                logger.info("Using OpenRouter for LLM invocation (attempt %s)", attempt + 1)
                response = client.chat.completions.create(
                    model=settings.OPENROUTER_MODEL,
                    messages=[{"role": "user", "content": cls._render_prompt(prompt, inputs)}],
                    temperature=0,
                    # Without an explicit cap some OpenRouter models truncate
                    # JSON responses mid-object, breaking agent parsing.
                    max_tokens=4096,
                    timeout=180,
                    **kwargs
                )
                return cls.unpack_response(response)
            except Exception as exc:
                is_quota = cls._is_quota_error(exc)
                is_network = cls._is_network_timeout_error(exc)

                if not (is_quota or is_network) or is_quota:
                    raise

                if attempt >= max_attempts - 1:
                    raise

                logger.warning(
                    "OpenRouter temporary network/timeout error (attempt %s failed): %s; backing off and retrying",
                    attempt + 1,
                    exc,
                )
                time.sleep(cls._get_backoff_seconds(attempt))

        raise RuntimeError("OpenRouter unavailable after retries")

    @classmethod
    def invoke(cls, prompt: Any, inputs: Dict[str, Any], require_json: bool = False) -> Tuple[str, Dict[str, int]]:
        """Invoke the LLM provider hierarchy: Gemini -> OpenRouter -> NVIDIA."""
        _invoke_start = time.time()
        provider_used = "gemini"
        fallback_used = False
        try:
            logger.info("[LLM] Invoking primary provider: Gemini")
            result = cls._invoke_gemini(prompt, inputs, require_json=require_json)
        except Exception as gemini_exc:
            if not cls._is_fallback_error(gemini_exc):
                raise
            logger.warning("[LLM] Gemini invocation failed: %s. Activating OpenRouter fallback...", gemini_exc)
            provider_used = "openrouter"
            fallback_used = True
            try:
                result = cls._invoke_openrouter(prompt, inputs, require_json=require_json)
            except Exception as open_exc:
                if not cls._is_fallback_error(open_exc):
                    raise
                logger.warning("[LLM] OpenRouter invocation failed: %s. Activating NVIDIA fallback...", open_exc)
                provider_used = "nvidia"
                fallback_used = True
                try:
                    result = cls._invoke_nvidia(prompt, inputs, require_json=require_json)
                except Exception as nvidia_exc:
                    elapsed_ms = int((time.time() - _invoke_start) * 1000)
                    logger.error(
                        "[LLM] NVIDIA fallback also failed | provider=%s | fallback=%s | time_ms=%d | error=%s",
                        provider_used, fallback_used, elapsed_ms, nvidia_exc,
                    )
                    raise LLMProviderException(
                        "The primary and all fallback LLM services are currently unavailable."
                    ) from nvidia_exc

        elapsed_ms = int((time.time() - _invoke_start) * 1000)
        token_usage = result[1] if isinstance(result, tuple) and len(result) > 1 else {}
        logger.info(
            "[LLM] Invoke complete | provider=%s | fallback=%s | time_ms=%d "
            "| input_tokens=%s | output_tokens=%s | total_tokens=%s",
            provider_used,
            fallback_used,
            elapsed_ms,
            token_usage.get("input_tokens", 0),
            token_usage.get("output_tokens", 0),
            token_usage.get("total_tokens", 0),
        )
        return result
