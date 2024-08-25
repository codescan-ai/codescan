import unittest
from unittest.mock import MagicMock, patch

from core.providers import BaseAIProvider

"""
Unit tests for the AIProviders module.
"""


class TestAIProviders(unittest.TestCase):
    def test__baseProvider__init(self):
        with self.assertRaises(NotImplementedError):
            BaseAIProvider()

    def test__newProvider__scanCodeNotImplemented(self):
        class NewProvider(BaseAIProvider):
            pass

        with self.assertRaises(NotImplementedError):
            NewProvider().scan_code()
