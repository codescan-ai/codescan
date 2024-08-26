import os
import unittest
from unittest.mock import MagicMock, mock_open, patch

from core.code_scanner.code_scanner import CodeScanner


class TestCodeScanner(unittest.TestCase):

    @patch("core.code_scanner.code_scanner.read_files_and_extract_code_summary")
    @patch("core.code_scanner.code_scanner.init_provider")
    @patch("os.walk")
    @patch("builtins.open", new_callable=mock_open, read_data="sample code")
    def test__scan__changesOnlyFalse(
        self,
        mock_open,
        mock_walk,
        mock_init_provider,
        mock_read_files_and_extract_code_summary,
    ):
        mock_read_files_and_extract_code_summary.return_value = "Code summary"
        mock_provider = MagicMock()
        mock_init_provider.return_value = mock_provider
        mock_provider.scan_code.return_value = "Scan result"
        mock_walk.return_value = [
            (os.path.join("some", "dir"), ("subdir",), ("file1.py", "file2.py")),
        ]
        mock_args = MagicMock(changes_only=False, directory=".")
        scan_result = CodeScanner(args=mock_args).scan()

        self.assertIn("Scan result", scan_result)
        mock_provider.scan_code.assert_called_once()

    @patch("core.code_scanner.code_scanner.get_changed_files_in_repo")
    @patch("core.code_scanner.code_scanner.generate_code_summary")
    @patch("core.code_scanner.code_scanner.init_provider")
    @patch("builtins.open", new_callable=mock_open, read_data="sample code")
    def test__scan__changesOnlyTrue_forGitDirectory(
        self,
        mock_open,
        mock_init_provider,
        mock_generate_code_summary,
        mock_get_changed_files_in_repo,
    ):
        mock_get_changed_files_in_repo.return_value = ["file_one.py"]
        mock_generate_code_summary.return_value = "Code summary"
        mock_provider = MagicMock()
        mock_init_provider.return_value = mock_provider
        mock_provider.scan_code.return_value = "Scan result"
        mock_args = MagicMock(changes_only=True, directory=".", repo="", pr_number=0)
        scan_result = CodeScanner(args=mock_args).scan()

        self.assertIn("Scan result", scan_result)
        mock_provider.scan_code.assert_called_once()

    @patch("core.code_scanner.code_scanner.get_changed_files_in_pr")
    @patch("core.code_scanner.code_scanner.generate_code_summary")
    @patch("core.code_scanner.code_scanner.init_provider")
    @patch("builtins.open", new_callable=mock_open, read_data="sample code")
    def test__scan__changesOnlyTrue_forPr(
        self,
        mock_open,
        mock_init_provider,
        mock_generate_code_summary,
        mock_get_changed_files_in_pr,
    ):
        mock_get_changed_files_in_pr.return_value = ["file_one.py"]
        mock_generate_code_summary.return_value = "Code summary"
        mock_provider = MagicMock()
        mock_init_provider.return_value = mock_provider
        mock_provider.scan_code.return_value = "Scan result"
        mock_args = MagicMock(
            changes_only=True,
            directory=".",
            repo="owner/repo",
            pr_number=112233,
            github_token="token",
        )
        scan_result = CodeScanner(args=mock_args).scan()

        self.assertIn("Scan result", scan_result)
        mock_provider.scan_code.assert_called_once()
