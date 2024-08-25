"""
This module defines the OpenAI Provider.
This is one of the supported AI Providers, and implement the BaseAIProvider abstract class.
"""

import os

import openai

from core.providers.base_ai_provider import BaseAIProvider


class OpenAIProvider(BaseAIProvider):
    """Provider that interacts with the OpenAI API."""

    def __init__(self, model):
        """Initializes the OpenAIProvider with the given model."""

        self.api_key = os.getenv("OPENAI_API_KEY")
        if not self.api_key:
            raise ValueError("OpenAI API key is not set in the environment.")
        self.client = openai.OpenAI(api_key=self.api_key)
        self.model = model

    def scan_code(self, code_summary):
        """Scans the code using OpenAI."""

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": """You are an expert in software security analysis, 
                    adept at identifying and explaining potential vulnerabilities in code. You will be 
                    given complete code snippets from various applications. Your task is to analyze 
                    the provided code, pinpoint potential security risks, and offer clear suggestions 
                    for enhancing the application's security posture. Focus on the critical issues that 
                    could impact the overall security of the application.""",
                    },
                    {"role": "user", "content": code_summary},
                ],
            )
            return response.choices[0].message.content
        except Exception as e:  # pylint: disable=W0718
            return f"Error occurred: {e}"
