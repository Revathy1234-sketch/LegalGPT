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
    def get_model() ->  Any:
        return ChatGoogleGenerativeAI(
            model=settings.GEMINI_MODEL,
            google_api_key=settings.GEMINI_API_KEY,
            temperature=0,
            max_output_tokens=1500,
            timeout=60,
            max_retries=0,
        )

    @staticmethod
    def get_openrouter_client() -> Any:
        if OpenAI is None:
            raise RuntimeError("OpenRouter client is unavailable")
        return OpenAI(
            api_key=settings.OPENROUTER_API_KEY,
            base_url="https://openrouter.ai/api/v1",
            timeout=60.0,
        )

    @staticmethod
    def unpack_response(response: Any) -> Tuple[str, Dict[str, int]]:
        """Return text and normalized token usage from a provider response."""
        content = getattr(response, "content", response)
        if isinstance(content, list):
            content = "".join(
                part.get("text", "") if isinstance(part, dict) else str(part)
                for part in content
            )
        elif hasattr(response, "choices") and response.choices:
            message = getattr(response.choices[0], "message", None)
            content = getattr(message, "content", "")
            if isinstance(content, list):
                content = "".join(
                    part.get("text", "") if isinstance(part, dict) else str(part)
                    for part in content
                )
        elif hasattr(response, "text"):
            content = response.text

        # Robust token accounting extracting usage metadata from various shapes
        sources = []
        
        # 1. From response attributes
        if hasattr(response, "usage_metadata") and response.usage_metadata:
            sources.append(response.usage_metadata)
        if hasattr(response, "response_metadata") and response.response_metadata:
            sources.append(response.response_metadata)
            if isinstance(response.response_metadata, dict):
                if "usage_metadata" in response.response_metadata:
                    sources.append(response.response_metadata["usage_metadata"])
                if "token_usage" in response.response_metadata:
                    sources.append(response.response_metadata["token_usage"])
                if "usage" in response.response_metadata:
                    sources.append(response.response_metadata["usage"])
                    
        if hasattr(response, "usage") and response.usage:
            sources.append(response.usage)
            
        # 2. From response itself if it is a dict
        if isinstance(response, dict):
            sources.append(response)
            if "usage" in response:
                sources.append(response["usage"])
            if "usage_metadata" in response:
                sources.append(response["usage_metadata"])
            if "meta" in response and isinstance(response["meta"], dict):
                sources.append(response["meta"])
                if "usage" in response["meta"]:
                    sources.append(response["meta"]["usage"])
                if "token_usage" in response["meta"]:
                    sources.append(response["meta"]["token_usage"])
            if "token_usage" in response:
                sources.append(response["token_usage"])

        input_tokens = 0
        output_tokens = 0
        total_tokens = 0

        # Helper to extract an integer value from a source object/dict
        def get_val(source: Any, keys: list[str]) -> int:
            for k in keys:
                # check dict keys
                if isinstance(source, dict):
                    if k in source and source[k] is not None:
                        try:
                            return int(source[k])
                        except (ValueError, TypeError):
                            pass
                # check attributes
                elif hasattr(source, k):
                    val = getattr(source, k, None)
                    if val is not None:
                        try:
                            return int(val)
                        except (ValueError, TypeError):
                            pass
            return 0

        # Try to extract from each source in preference order
        for src in sources:
            if not src:
                continue
            
            i_tok = get_val(src, ["input_tokens", "prompt_tokens", "prompt_token_count", "input_token_count"])
            o_tok = get_val(src, ["output_tokens", "completion_tokens", "candidates_token_count", "completion_token_count", "output_token_count"])
            t_tok = get_val(src, ["total_tokens", "total_token_count"])
            
            if i_tok > 0:
                input_tokens = i_tok
            if o_tok > 0:
                output_tokens = o_tok
            if t_tok > 0:
                total_tokens = t_tok

        if not total_tokens:
            total_tokens = input_tokens + output_tokens

        return str(content or ""), {
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": total_tokens,
        }

    @staticmethod
    def _is_quota_error(exc: Exception) -> bool:
        if ResourceExhausted is not None and isinstance(exc, ResourceExhausted):
            return True
        lowered = str(exc).lower()
        return any(
            token in lowered
            for token in ["429", "quota", "resourceexhausted", "rate limit", "per minute"]
        )

    @staticmethod
    def _is_fallback_error(exc: Exception) -> bool:
        """Determine if an exception should trigger a fallback to the secondary provider.
        Checks:
        1. Known provider‑specific exception classes (e.g., httpx.HTTPStatusError, httpx.RequestError).
        2. HTTP status codes indicating quota or server errors (429, 503, 500).
        3. Message patterns for quota or timeout issues.
        Returns True if fallback is appropriate, False otherwise.
        """
        # 1. Exception class checks
        if isinstance(exc, (httpx.HTTPStatusError, httpx.RequestError)):
            # For HTTPStatusError we can inspect the response status code
            if isinstance(exc, httpx.HTTPStatusError) and exc.response is not None:
                if exc.response.status_code in {429, 503, 500}:
                    return True
            return True
        # 2. Use existing helpers for quota or network timeout detection
        if LLMService._is_quota_error(exc) or LLMService._is_network_timeout_error(exc):
            return True
        # 3. Generic fallback for any other unexpected exception
        return False

    @staticmethod
    def _is_network_timeout_error(exc: Exception) -> bool:
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
    def _invoke_gemini(cls, prompt: Any, inputs: Dict[str, Any]) -> Tuple[str, Dict[str, int]]:
        if ChatGoogleGenerativeAI is None:
            raise RuntimeError("Gemini client is unavailable")

        # Quota errors: 0 retries (1 attempt total)
        # Temporary network/timeout errors: 1 retry (2 attempts total)
        max_attempts = 2
        for attempt in range(max_attempts):
            try:
                logger.info("Using Gemini for LLM invocation (attempt %s)", attempt + 1)
                response = (prompt | cls.get_model()).invoke(inputs)
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

                logger.warning("Gemini temporary network/timeout error (attempt %s failed): %s; backing off and retrying", attempt + 1, exc)
                time.sleep(cls._get_backoff_seconds(attempt))

        raise RuntimeError("Gemini unavailable after retries")

    @classmethod
    def _invoke_openrouter(cls, prompt: Any, inputs: Dict[str, Any]) -> Tuple[str, Dict[str, int]]:
        client = cls.get_openrouter_client()
        response = client.chat.completions.create(
            model=settings.OPENROUTER_MODEL,
            messages=[{"role": "user", "content": cls._render_prompt(prompt, inputs)}],
            timeout=60,
        )
        return cls.unpack_response(response)

    @classmethod
    def invoke(cls, prompt: Any, inputs: Dict[str, Any]) -> Tuple[str, Dict[str, int]]:
        """Invoke the primary LLM provider and fall back to OpenRouter when needed."""
        _invoke_start = time.time()
        provider_used = "gemini"
        fallback_used = False
        try:
            logger.info("[LLM] Invoking primary provider: Gemini")
            result = cls._invoke_gemini(prompt, inputs)
        except Exception as exc:
            if not cls._is_fallback_error(exc):
                # Not a fallback-eligible error; re-raise to surface the issue
                raise
            logger.warning("[LLM] Gemini invocation failed: %s. Activating OpenRouter fallback...", exc)
            provider_used = "openrouter"
            fallback_used = True
            try:
                result = cls._invoke_openrouter(prompt, inputs)
            except Exception as open_exc:
                elapsed_ms = int((time.time() - _invoke_start) * 1000)
                logger.error(
                    "[LLM] OpenRouter fallback also failed | provider=%s | fallback=%s | time_ms=%d | error=%s",
                    provider_used, fallback_used, elapsed_ms, open_exc,
                )
                raise LLMProviderException(
                    "The primary LLM service and fallback service are both currently unavailable."
                ) from exc

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
