"""
This module provides util methods used for initializing an AIProvider based on the user args.
"""

from core.providers.custom_ai_provider import CustomAIProvider
from core.providers.google_gemini_ai_provider import GoogleGeminiAIProvider
from core.providers.open_ai_provider import OpenAIProvider

PROVIDERS = {
    "openai": OpenAIProvider,
    "gemini": GoogleGeminiAIProvider,
    "custom": CustomAIProvider,
}

DEFAULT_MODELS = {
    "openai": "gpt-4o-mini",
    "gemini": "gemini-pro",
}


def init_provider(provider, model, host=None, port=None, token=None, endpoint=None): # pylint: disable=R0917
    """
    Initializes and returns the appropriate AI client based on the provider.
    """

    if provider == "custom":
        client_params = {
            "model": model,
            "host": host,
            "port": port,
            "token": token,
            "endpoint": endpoint,
        }
    else:
        client_params = {
            "model": model if model else DEFAULT_MODELS[provider],
        }

    return PROVIDERS[provider](**client_params)
