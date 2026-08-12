import unittest
from unittest.mock import patch, MagicMock

from app.services.llm_service import LLMService, LLMProviderException
from app.core.config import settings


class TestLLMFallback(unittest.TestCase):

    def setUp(self):
        # Ensure environment variables are set for client initialization
        settings.OPENROUTER_API_KEY = "dummy-key"
        settings.GEMINI_API_KEY = "dummy-key"
        settings.NVIDIA_API_KEY = "dummy-key"
        settings.GEMINI_MODEL = "gemini-2.5-flash"
        settings.NVIDIA_MODEL = "openai/gpt-oss-20b"
        settings.OPENROUTER_MODEL = "openrouter/anthropic/claude-3.5-sonnet"

    @patch("app.services.llm_service.ChatGoogleGenerativeAI")
    @patch("app.services.llm_service.LLMService.get_openrouter_client")
    @patch("app.services.llm_service.LLMService.get_nvidia_client")
    def test_nvidia_success(self, mock_get_nv, mock_get_or, mock_gemini_cls):
        # TEST A: NVIDIA succeeds. Expected: NVIDIA called. OpenRouter NOT called. Gemini NOT called.
        mock_nv_client = MagicMock()
        mock_nv_response = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "NVIDIA response"
        mock_nv_response.choices = [MagicMock(message=mock_msg)]
        mock_nv_client.chat.completions.create.return_value = mock_nv_response
        mock_get_nv.return_value = mock_nv_client

        response, _ = LLMService.invoke(prompt="test", inputs={})
        self.assertEqual(response, "NVIDIA response")
        mock_nv_client.chat.completions.create.assert_called_once()
        mock_get_or.assert_not_called()
        mock_gemini_cls.assert_not_called()

    @patch("app.services.llm_service.ChatGoogleGenerativeAI")
    @patch("app.services.llm_service.LLMService.get_openrouter_client")
    @patch("app.services.llm_service.LLMService.get_nvidia_client")
    def test_nvidia_fails_openrouter_succeeds(self, mock_get_nv, mock_get_or, mock_gemini_cls):
        # TEST B: NVIDIA fails. OpenRouter succeeds. Expected: NVIDIA -> OpenRouter. Gemini NOT called.
        mock_nv_client = MagicMock()
        mock_nv_client.chat.completions.create.side_effect = Exception("429 rate limit")
        mock_get_nv.return_value = mock_nv_client

        mock_or_client = MagicMock()
        mock_or_response = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "OpenRouter response"
        mock_or_response.choices = [MagicMock(message=mock_msg)]
        mock_or_client.chat.completions.create.return_value = mock_or_response
        mock_get_or.return_value = mock_or_client

        response, _ = LLMService.invoke(prompt="test", inputs={})
        self.assertEqual(response, "OpenRouter response")
        mock_nv_client.chat.completions.create.assert_called_once()
        mock_or_client.chat.completions.create.assert_called_once()
        mock_gemini_cls.assert_not_called()

    @patch("app.services.llm_service.ChatGoogleGenerativeAI")
    @patch("app.services.llm_service.LLMService.get_openrouter_client")
    @patch("app.services.llm_service.LLMService.get_nvidia_client")
    def test_nvidia_and_openrouter_fail_gemini_succeeds(self, mock_get_nv, mock_get_or, mock_gemini_cls):
        # TEST C: NVIDIA fails. OpenRouter fails. Gemini succeeds. Expected: NVIDIA -> OpenRouter -> Gemini
        mock_nv_client = MagicMock()
        mock_nv_client.chat.completions.create.side_effect = Exception("429 rate limit")
        mock_get_nv.return_value = mock_nv_client

        mock_or_client = MagicMock()
        mock_or_client.chat.completions.create.side_effect = Exception("timeout")
        mock_get_or.return_value = mock_or_client

        mock_gemini = MagicMock()
        mock_gemini.invoke.return_value = MagicMock(content="Gemini response")
        mock_gemini_cls.return_value = mock_gemini

        response, _ = LLMService.invoke(prompt="test", inputs={})
        self.assertEqual(response, "Gemini response")
        mock_nv_client.chat.completions.create.assert_called_once()
        self.assertEqual(mock_or_client.chat.completions.create.call_count, 2)
        mock_gemini.invoke.assert_called_once()

    @patch("app.services.llm_service.ChatGoogleGenerativeAI")
    @patch("app.services.llm_service.LLMService.get_openrouter_client")
    @patch("app.services.llm_service.LLMService.get_nvidia_client")
    def test_all_three_fail(self, mock_get_nv, mock_get_or, mock_gemini_cls):
        # TEST D: All providers fail. Expected: LLMProviderException
        mock_nv_client = MagicMock()
        mock_nv_client.chat.completions.create.side_effect = Exception("429 rate limit")
        mock_get_nv.return_value = mock_nv_client

        mock_or_client = MagicMock()
        mock_or_client.chat.completions.create.side_effect = Exception("timeout")
        mock_get_or.return_value = mock_or_client

        mock_gemini = MagicMock()
        mock_gemini.invoke.side_effect = Exception("Gemini quota error")
        mock_gemini_cls.return_value = mock_gemini

        with self.assertRaises(LLMProviderException):
            LLMService.invoke(prompt="test", inputs={})

        mock_nv_client.chat.completions.create.assert_called_once()
        self.assertEqual(mock_or_client.chat.completions.create.call_count, 2)
        mock_gemini.invoke.assert_called_once()

    @patch("app.services.llm_service.LLMService.get_nvidia_client")
    def test_nvidia_reasoning_ignored(self, mock_get_nv):
        # TEST E: NVIDIA returns content = "NVIDIA PRIMARY SUCCESS", reasoning_content = "...". Expected: returned result = "NVIDIA PRIMARY SUCCESS"
        mock_nv_client = MagicMock()
        mock_nv_response = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "NVIDIA PRIMARY SUCCESS"
        mock_msg.reasoning_content = "some thinking chain"
        mock_nv_response.choices = [MagicMock(message=mock_msg)]
        mock_nv_client.chat.completions.create.return_value = mock_nv_response
        mock_get_nv.return_value = mock_nv_client

        response, _ = LLMService.invoke(prompt="test", inputs={})
        self.assertEqual(response, "NVIDIA PRIMARY SUCCESS")


if __name__ == "__main__":
    unittest.main()
