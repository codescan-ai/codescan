"""
This module defines an abstract class to represent an AI provider.
Currently supported AI providers will implement this class.
"""


class BaseAIProvider:
    """Abstract base class for defining AI providers."""

    def __init__(self):
        """Initializes the base AI provider."""
        raise NotImplementedError(
            "BaseAIProvider is an abstract class and cannot be instantiated directly."
        )

    def scan_code(self, code_summary):
        """Scans the provided code summary for potential security vulnerabilities."""
        raise NotImplementedError(
            "Each AI provider must implement the `scan_code` method."
        )
