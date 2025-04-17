"""
This module defines a CustomAI Provider, and implement the BaseAIProvider abstract class.
With this users can connect to their locally hosted AI provider.
"""

import requests

from core.providers.base_ai_provider import BaseAIProvider


class CustomAIProvider(BaseAIProvider):
    """Provider for interacting with a custom AI server."""

    def __init__(self, model, host, port, token=None, endpoint="/api/v1/scan"): # pylint: disable=R0917
        """Initializes the custom AI provider with the given parameters."""

        self.model = model
        self.host = host
        self.port = port
        self.token = token
        self.endpoint = endpoint
        self.base_url = f"{host}:{port}{endpoint}"

    def scan_code(self, code_summary):
        """Scans the code using the custom AI server."""

        headers = {"Authorization": f"Bearer {self.token}" if self.token else ""}
        payload = {
            "model": self.model,
            "messages": [
                {
                    "role": "user",
                    "content": """You are an experienced application security specialist, entrusted with the task of 
                    carefully reviewing the following code for potential security vulnerabilities. Your objective 
                    is to conduct a comprehensive analysis, identifying any weak points that could be exploited 
                    by malicious actors. Once identified, provide clear and actionable recommendations to 
                    mitigate these risks and strengthen the overall security posture of the application. 
                    Focus on issues that could compromise the integrity, confidentiality, or availability 
                    of the system, and ensure that your suggestions are practical and implementable. 
                    Here is the code you need to review:
                    """
                    + code_summary,
                },
            ],
        }
        try:
            response = requests.post(
                self.base_url, json=payload, headers=headers, timeout=120
            )
            response.raise_for_status()
            return (
                response.json()
                .get("message", {})
                .get("content", "No response content.")
            )
        except requests.exceptions.RequestException as e:
            return f"Error occurred while connecting to the server: {e}"
