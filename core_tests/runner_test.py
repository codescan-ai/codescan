import unittest
from unittest.mock import MagicMock, patch

from core.runner import format_as_markdown


class TestUtils(unittest.TestCase):
    def test_formatAsMarkdown(self):
        result = "This is a test result"
        expected_output = "## Code Security Analysis Results\nThis is a test result"
        self.assertEqual(format_as_markdown(result), expected_output)
