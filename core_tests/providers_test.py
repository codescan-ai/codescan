import unittest
from unittest.mock import MagicMock, patch

from core.providers.base_ai_provider import BaseAIProvider
from core.providers.google_gemini_ai_provider import GoogleGeminiAIProvider
from core.providers.open_ai_provider import OpenAIProvider

"""
Unit tests for the AIProviders module.
"""


class TestAIProviders(unittest.TestCase):
    # BaseAIProvider
    def test__baseProvider__init(self):
        with self.assertRaises(NotImplementedError):
            BaseAIProvider()

    def test__newProvider__scanCodeNotImplemented(self):
        class NewProvider(BaseAIProvider):
            pass

        with self.assertRaises(NotImplementedError):
            NewProvider().scan_code()

    # GoogleGeminiAIProvider
    @patch("core.providers.google_gemini_ai_provider.genai.GenerativeModel")
    @patch("core.providers.google_gemini_ai_provider.genai.configure")
    @patch("os.getenv", return_value="test_gemini_api_key")
    def test__googleGeminiAIProvider__scanCode(
        self, mock_getenv, mock_configure, mock_generative_model
    ):
        mock_model = MagicMock()
        mock_generative_model.return_value = mock_model
        mock_model.generate_content.return_value.text = "Test Google Gemini response"

        client = GoogleGeminiAIProvider(model="test_model")
        result = client.scan_code("sample code")

        self.assertEqual(result, "Test Google Gemini response")
        mock_model.generate_content.assert_called_once()

    # OpenAIProvider
    @patch("core.providers.open_ai_provider.openai.OpenAI")
    @patch("os.getenv", return_value="test_openai_api_key")
    def test__openAIProvider__scanCode(self, mock_getenv, mock_openai):
        mock_client = MagicMock()
        mock_openai.return_value = mock_client
        mock_client.chat.completions.create.return_value.choices = [
            MagicMock(message=MagicMock(content="Test OpenAI response"))
        ]

        client = OpenAIProvider(model="test_model")
        result = client.scan_code("sample code")

        self.assertEqual(result, "Test OpenAI response")
        mock_client.chat.completions.create.assert_called_once()
