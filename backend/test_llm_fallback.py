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
    def test_gemini_success(self, mock_get_nv, mock_get_or, mock_gemini_cls):
        # TEST A: Gemini succeeds. Expected: Gemini called. OpenRouter NOT called. NVIDIA NOT called.
        mock_gemini = MagicMock()
        mock_gemini.invoke.return_value = MagicMock(content="Gemini response")
        mock_gemini_cls.return_value = mock_gemini

        response, _ = LLMService.invoke(prompt="test", inputs={})
        self.assertEqual(response, "Gemini response")
        mock_gemini.invoke.assert_called_once()
        mock_get_or.assert_not_called()
        mock_get_nv.assert_not_called()

    @patch("app.services.llm_service.ChatGoogleGenerativeAI")
    @patch("app.services.llm_service.LLMService.get_openrouter_client")
    @patch("app.services.llm_service.LLMService.get_nvidia_client")
    def test_gemini_fails_openrouter_succeeds(self, mock_get_nv, mock_get_or, mock_gemini_cls):
        # TEST B: Gemini fails. OpenRouter succeeds. Expected: Gemini -> OpenRouter. NVIDIA NOT called.
        mock_gemini = MagicMock()
        mock_gemini.invoke.side_effect = Exception("timeout")
        mock_gemini_cls.return_value = mock_gemini

        mock_or_client = MagicMock()
        mock_or_response = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "OpenRouter response"
        mock_or_response.choices = [MagicMock(message=mock_msg)]
        mock_or_client.chat.completions.create.return_value = mock_or_response
        mock_get_or.return_value = mock_or_client

        response, _ = LLMService.invoke(prompt="test", inputs={})
        self.assertEqual(response, "OpenRouter response")
        self.assertEqual(mock_gemini.invoke.call_count, 2)
        mock_or_client.chat.completions.create.assert_called_once()
        mock_get_nv.assert_not_called()

    @patch("app.services.llm_service.ChatGoogleGenerativeAI")
    @patch("app.services.llm_service.LLMService.get_openrouter_client")
    @patch("app.services.llm_service.LLMService.get_nvidia_client")
    def test_gemini_and_openrouter_fail_nvidia_succeeds(self, mock_get_nv, mock_get_or, mock_gemini_cls):
        # TEST C: Gemini fails. OpenRouter fails. NVIDIA succeeds. Expected: Gemini -> OpenRouter -> NVIDIA
        mock_gemini = MagicMock()
        mock_gemini.invoke.side_effect = Exception("timeout")
        mock_gemini_cls.return_value = mock_gemini

        mock_or_client = MagicMock()
        mock_or_client.chat.completions.create.side_effect = Exception("timeout")
        mock_get_or.return_value = mock_or_client

        mock_nv_client = MagicMock()
        mock_nv_response = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "NVIDIA response"
        mock_nv_response.choices = [MagicMock(message=mock_msg)]
        mock_nv_client.chat.completions.create.return_value = mock_nv_response
        mock_get_nv.return_value = mock_nv_client

        response, _ = LLMService.invoke(prompt="test", inputs={})
        self.assertEqual(response, "NVIDIA response")
        self.assertEqual(mock_gemini.invoke.call_count, 2)
        self.assertEqual(mock_or_client.chat.completions.create.call_count, 2)
        mock_nv_client.chat.completions.create.assert_called_once()

    @patch("app.services.llm_service.ChatGoogleGenerativeAI")
    @patch("app.services.llm_service.LLMService.get_openrouter_client")
    @patch("app.services.llm_service.LLMService.get_nvidia_client")
    def test_all_three_fail(self, mock_get_nv, mock_get_or, mock_gemini_cls):
        # TEST D: All providers fail. Expected: LLMProviderException
        mock_gemini = MagicMock()
        mock_gemini.invoke.side_effect = Exception("Gemini quota error")
        mock_gemini_cls.return_value = mock_gemini

        mock_or_client = MagicMock()
        mock_or_client.chat.completions.create.side_effect = Exception("timeout")
        mock_get_or.return_value = mock_or_client

        mock_nv_client = MagicMock()
        mock_nv_client.chat.completions.create.side_effect = Exception("429 rate limit")
        mock_get_nv.return_value = mock_nv_client

        with self.assertRaises(LLMProviderException):
            LLMService.invoke(prompt="test", inputs={})

        mock_gemini.invoke.assert_called_once()
        self.assertEqual(mock_or_client.chat.completions.create.call_count, 2)
        mock_nv_client.chat.completions.create.assert_called_once()

    @patch("app.services.llm_service.ChatGoogleGenerativeAI")
    def test_gemini_reasoning_ignored(self, mock_gemini_cls):
        # TEST E: Gemini returns content = "GEMINI PRIMARY SUCCESS", reasoning_content = "...". Expected: returned result = "GEMINI PRIMARY SUCCESS"
        mock_gemini = MagicMock()
        mock_msg = MagicMock()
        mock_msg.content = "GEMINI PRIMARY SUCCESS"
        mock_msg.reasoning_content = "some thinking chain"
        mock_gemini.invoke.return_value = mock_msg
        mock_gemini_cls.return_value = mock_gemini

        response, _ = LLMService.invoke(prompt="test", inputs={})
        self.assertEqual(response, "GEMINI PRIMARY SUCCESS")


if __name__ == "__main__":
    unittest.main()
