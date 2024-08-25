"""
This module defines the GoogleGemini AI Provider.
This is one of the supported AI Providers, and implement the BaseAIProvider abstract class.
"""

import os

import google.generativeai as genai

from core.providers.base_ai_provider import BaseAIProvider


class GoogleGeminiAIProvider(BaseAIProvider):
    """Client for interacting with the Google Generative AI API."""

    def __init__(self, model):
        """Initializes the GoogleGemini AI Provider with the given model."""

        self.api_key = os.getenv("GEMINI_API_KEY")
        if not self.api_key:
            raise ValueError("Gemini API key is not set in the environment.")
        genai.configure(api_key=self.api_key)
        self.model = genai.GenerativeModel(model)

    def scan_code(self, code_summary):
        try:
            response = self.model.generate_content(
                """You are a specialist in application security, known for your ability to 
                analyze complex codebases and uncover hidden vulnerabilities. You will be 
                presented with the full code of an application. Your mission is to conduct 
                a thorough security review, identifying potential weaknesses and offering 
                actionable recommendations for improvement. Prioritize the most significant 
                security risks that could compromise the integrity of the application. 
                Here is the code:"""
                + code_summary,
            )
            return response.text
        except Exception as e:  # pylint: disable=W0718
            return f"Error occurred: {e}"
