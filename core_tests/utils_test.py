import os
import subprocess
import unittest
from unittest.mock import MagicMock, mock_open, patch

from core.utils.code_summary_extractor import (
    generate_code_summary,
    read_files_and_extract_code_summary,
)
from core.utils.file_extractor import (
    get_changed_files_in_pr,
    get_changed_files_in_repo,
    is_git_repo,
)
from core.utils.provider_creator import init_provider


class TestUtils(unittest.TestCase):
    """
    File Extractor Tests
    """

    @patch("subprocess.check_output")
    def test__isGitRepo__valid(self, mock_check_output):
        mock_check_output.return_value = b"true\n"
        self.assertTrue(is_git_repo(os.path.join("test", "valid", "repo")))

    @patch(
        "subprocess.check_output", side_effect=subprocess.CalledProcessError(1, "git")
    )
    def test__isGitRepo__invalid(self, mock_check_output):
        self.assertFalse(is_git_repo(os.path.join("test", "invalid", "repo")))

    @patch("core.utils.file_extractor.Github")
    def test__getChangedFilesInPr(self, mock_github):
        mock_pr = MagicMock()
        mock_pr.get_files.return_value = [
            MagicMock(filename="file_one.py"),
            MagicMock(filename="file_two.py"),
        ]
        mock_repo = MagicMock()
        mock_repo.get_pull.return_value = mock_pr
        mock_github.return_value.get_repo.return_value = mock_repo

        files = get_changed_files_in_pr("some/repo", 1, "fake_token")
        self.assertEqual(files, ["file_one.py", "file_two.py"])

    @patch("subprocess.check_output")
    @patch("os.chdir")
    @patch("core.utils.file_extractor.is_git_repo", return_value=True)
    def test__getChangedFilesInRepo(
        self, mock_is_git_repo, mock_chdir, mock_check_output
    ):
        mock_check_output.return_value = "file_one.py\nfile_two.py\n"
        files = get_changed_files_in_repo(os.path.join("some", "repo"))
        self.assertEqual(files, ["file_one.py", "file_two.py"])
        mock_chdir.assert_called_once_with(os.path.join("some", "repo"))

    @patch("core.utils.file_extractor.is_git_repo", return_value=False)
    def test__getChangedFilesInRepo_inValid(self, mock_is_git_repo):
        with self.assertRaises(ValueError):
            get_changed_files_in_repo(os.path.join("invalid", "repo"))

    """
    Code Summary Extractor Tests
    """

    @patch("builtins.open", new_callable=mock_open, read_data="sample code")
    @patch("os.path.isfile", return_value=True)
    def test__readFilesAndExtractCodeSummary__isValidFile(self, mock_isfile, mock_open):
        file_paths = [
            os.path.join("some", "repo", "file_one.py"),
            os.path.join("some", "repo", "file_two.py"),
        ]

        code_summary = read_files_and_extract_code_summary(file_paths)

        self.assertIn("File: file_one.py", code_summary)
        self.assertIn("sample code", code_summary)
        self.assertIn("File: file_two.py", code_summary)

        mock_open.assert_any_call(
            os.path.join("some", "repo", "file_one.py"), "r", encoding="utf-8"
        )
        mock_open.assert_any_call(
            os.path.join("some", "repo", "file_two.py"), "r", encoding="utf-8"
        )

    @patch("builtins.open", new_callable=mock_open, read_data="sample code")
    @patch("os.path.isfile", return_value=False)
    def test__readFilesAndExtractCodeSummary__isInvalidFile(
        self, mock_isfile, mock_open
    ):
        file_paths = [os.path.join("some", "repo", "invalid_file.py")]

        code_summary = read_files_and_extract_code_summary(file_paths)

        self.assertEqual(code_summary, "")
        mock_open.assert_not_called()

    @patch("builtins.open", new_callable=mock_open)
    @patch("os.path.isfile", return_value=True)
    def test__readFilesAndExtractCodeSummary__decodingError(
        self, mock_isfile, mock_open
    ):
        mock_open.side_effect = UnicodeDecodeError("utf-8", b"", 0, 1, "decoding error")
        file_paths = [os.path.join("some", "repo", "file_one.py")]

        code_summary = read_files_and_extract_code_summary(file_paths)

        self.assertEqual(code_summary, "")
        mock_open.assert_called_once_with(
            os.path.join("some", "repo", "file_one.py"), "r", encoding="utf-8"
        )

    @patch("builtins.open", new_callable=mock_open, read_data="sample code")
    @patch("os.path.isfile", return_value=True)
    def test__generateCodeSummary__isValid(self, mock_isfile, mock_open):
        changed_files = ["file_one.py", "file_two.py"]

        code_summary = generate_code_summary(
            os.path.join("some", "repo"), changed_files
        )
        self.assertIn("sample code", code_summary)

        mock_open.assert_any_call(
            os.path.join("some", "repo", "file_one.py"), "r", encoding="utf-8"
        )
        mock_open.assert_any_call(
            os.path.join("some", "repo", "file_two.py"), "r", encoding="utf-8"
        )

    """
    Provider Creator Tests
    """

    @patch("core.utils.provider_creator.OpenAIProvider")
    @patch("os.getenv")
    def test__initOpenAIProvider(self, mock_getenv, mock_openai_provider):
        mock_getenv.return_value = "test_openai_api_key"
        init_provider("openai", None)
        mock_getenv.assert_called_once_with("OPENAI_API_KEY")

    @patch("core.utils.provider_creator.GoogleGeminiAIProvider")
    @patch("os.getenv")
    def test__initGoogleGeminiAIProvider(self, mock_getenv, mock_google_client):
        mock_getenv.return_value = "test_gemini_api_key"
        init_provider("gemini", None)
        mock_getenv.assert_called_once_with("GEMINI_API_KEY")

    @patch("core.utils.provider_creator.CustomAIProvider")
    def test_initialize_client_custom(self, mock_custom_client):
        init_provider(
            "custom",
            "custom-model",
            "http://localhost",
            5000,
            "custom-token",
            "/api/v1/scan",
        )


if __name__ == "__main__":
    unittest.main()
