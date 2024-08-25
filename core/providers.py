"""
This module defines classes represent the available AI providers currently supported for code scanning.
"""

import os

import google.generativeai as genai
import openai
import requests

class BaseAIProvider:
    """Abstract base class for defining AI providers."""

    def __init__(self):
        """Initializes the base AI provider."""
        raise NotImplementedError(
            "BaseAIProvider is an abstract class and cannot be instantiated directly."
        )

    def scan_code(self, code_summary):
        """Scans the provided code summary for potential security vulnerabilities."""
        raise NotImplementedError("Each AI provider must implement the `scan_code` method.")