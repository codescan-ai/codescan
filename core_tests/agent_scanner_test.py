import os
import unittest
from unittest.mock import MagicMock, mock_open, patch

from core.agent import FileScanResult, Vulnerability, get_pydantic_ai_model
from core.code_scanner.agent_scanner import AgentScanner


class TestGetPydanticAiModel(unittest.TestCase):
    def test__openai__returnsDefaultModel(self):
        self.assertEqual(get_pydantic_ai_model("openai", None), "openai:gpt-4o-mini")

    def test__openai__returnsSpecifiedModel(self):
        self.assertEqual(get_pydantic_ai_model("openai", "gpt-4o"), "openai:gpt-4o")

    def test__gemini__returnsDefaultModel(self):
        self.assertEqual(get_pydantic_ai_model("gemini", None), "gemini:gemini-1.5-flash")

    def test__gemini__returnsSpecifiedModel(self):
        self.assertEqual(get_pydantic_ai_model("gemini", "gemini-pro"), "gemini:gemini-pro")

    def test__custom__returnsDefaultModel(self):
        self.assertEqual(get_pydantic_ai_model("custom", None), "openai:custom-model")

    def test__custom__returnsSpecifiedModel(self):
        self.assertEqual(get_pydantic_ai_model("custom", "my-model"), "openai:my-model")


class TestVulnerabilityModel(unittest.TestCase):
    def test__vulnerability__withAllFields(self):
        vuln = Vulnerability(
            line_number=14,
            description="SQL Injection via f-string",
            remediation="Use parameterized queries",
            severity="Critical",
            vulnerability_type="SQL Injection",
        )
        self.assertEqual(vuln.line_number, 14)
        self.assertEqual(vuln.severity, "Critical")
        self.assertEqual(vuln.vulnerability_type, "SQL Injection")

    def test__vulnerability__lineNumberIsOptional(self):
        vuln = Vulnerability(
            description="MD5 is a weak hashing algorithm",
            remediation="Use bcrypt or Argon2",
            severity="High",
            vulnerability_type="Weak Cryptography",
        )
        self.assertIsNone(vuln.line_number)

    def test__fileScanResult__emptyVulnerabilities(self):
        result = FileScanResult(vulnerabilities=[])
        self.assertEqual(result.vulnerabilities, [])

    def test__fileScanResult__withVulnerabilities(self):
        vuln = Vulnerability(
            line_number=6,
            description="Pickle deserialization",
            remediation="Use json.loads",
            severity="Critical",
            vulnerability_type="Insecure Deserialization",
        )
        result = FileScanResult(vulnerabilities=[vuln])
        self.assertEqual(len(result.vulnerabilities), 1)
        self.assertEqual(result.vulnerabilities[0].line_number, 6)


class TestAgentScanner(unittest.TestCase):

    def _make_args(self, **kwargs):
        defaults = dict(
            provider="openai",
            model=None,
            host=None,
            port=None,
            token=None,
            endpoint=None,
            directory=".",
            changes_only=False,
            repo=None,
            pr_number=None,
            github_token=None,
            prompt_file=None,
            prompt_preset="security",
            max_file_bytes=262144,
            exclude_dirs=None,
        )
        defaults.update(kwargs)
        return MagicMock(**defaults)

    @patch("core.code_scanner.agent_scanner.create_agent")
    def test__init__createsAgentWithCorrectModelString(self, mock_create_agent):
        args = self._make_args(provider="openai", model="gpt-4o")
        AgentScanner(args)
        mock_create_agent.assert_called_once()
        call_kwargs = mock_create_agent.call_args[1]
        self.assertEqual(call_kwargs["model_str"], "openai:gpt-4o")

    @patch("core.code_scanner.agent_scanner.create_agent")
    def test__init__customProvider_setsOpenAIBaseURL(self, mock_create_agent):
        args = self._make_args(provider="custom", host="http://localhost", port=11434, endpoint="/v1", token="tok")
        with patch.dict(os.environ, {}, clear=False):
            AgentScanner(args)
            self.assertEqual(os.environ.get("OPENAI_BASE_URL"), "http://localhost:11434/v1")
            self.assertEqual(os.environ.get("OPENAI_API_KEY"), "tok")

    @patch("core.code_scanner.agent_scanner.create_agent")
    def test__init__noGithubArgs_githubIntegrationIsNone(self, mock_create_agent):
        args = self._make_args(repo=None, pr_number=None, github_token=None)
        scanner = AgentScanner(args)
        self.assertIsNone(scanner.github_integration)

    @patch("core.code_scanner.agent_scanner.create_agent")
    def test__scan__routesToScanFiles_whenNoChangesFlag(self, mock_create_agent):
        args = self._make_args(changes_only=False, repo=None, pr_number=None)
        scanner = AgentScanner(args)
        scanner._scan_files = MagicMock()
        scanner.scan()
        scanner._scan_files.assert_called_once()

    @patch("core.code_scanner.agent_scanner.create_agent")
    def test__scan__routesToScanChanges_whenChangesOnlyTrue(self, mock_create_agent):
        args = self._make_args(changes_only=True, repo=None, pr_number=None)
        scanner = AgentScanner(args)
        scanner._scan_changes = MagicMock()
        scanner.scan()
        scanner._scan_changes.assert_called_once()

    @patch("core.code_scanner.agent_scanner.create_agent")
    def test__scanSingleFile__skipsNonExistentFile(self, mock_create_agent):
        args = self._make_args()
        scanner = AgentScanner(args)
        with patch("os.path.isfile", return_value=False):
            scanner._scan_single_file("/fake/path.py", "path.py")
        scanner.agent.run_sync.assert_not_called()

    @patch("core.code_scanner.agent_scanner.create_agent")
    def test__scanSingleFile__skipsEmptyFile(self, mock_create_agent):
        args = self._make_args()
        scanner = AgentScanner(args)
        with patch("os.path.isfile", return_value=True), \
             patch("builtins.open", mock_open(read_data="   ")):
            scanner._scan_single_file("/fake/path.py", "path.py")
        scanner.agent.run_sync.assert_not_called()

    @patch("core.code_scanner.agent_scanner.create_agent")
    def test__scanSingleFile__prefixesLinesWithNumbers(self, mock_create_agent):
        args = self._make_args()
        scanner = AgentScanner(args)
        mock_result = MagicMock()
        mock_result.data = FileScanResult(vulnerabilities=[])
        scanner.agent.run_sync = MagicMock(return_value=mock_result)

        file_content = "line one\nline two\nline three"
        with patch("os.path.isfile", return_value=True), \
             patch("builtins.open", mock_open(read_data=file_content)):
            scanner._scan_single_file("/fake/path.py", "path.py")

        call_arg = scanner.agent.run_sync.call_args[0][0]
        self.assertIn("1: line one", call_arg)
        self.assertIn("2: line two", call_arg)
        self.assertIn("3: line three", call_arg)

    @patch("core.code_scanner.agent_scanner.create_agent")
    def test__scanSingleFile__annotatesChangedLines(self, mock_create_agent):
        args = self._make_args()
        scanner = AgentScanner(args)
        mock_result = MagicMock()
        mock_result.data = FileScanResult(vulnerabilities=[])
        scanner.agent.run_sync = MagicMock(return_value=mock_result)

        file_content = "line one\nline two\nline three"
        with patch("os.path.isfile", return_value=True), \
             patch("builtins.open", mock_open(read_data=file_content)):
            scanner._scan_single_file("/fake/path.py", "path.py", changed_lines={2})

        call_arg = scanner.agent.run_sync.call_args[0][0]
        self.assertIn("1: line one", call_arg)
        self.assertIn("2: [CHANGED] line two", call_arg)
        self.assertIn("3: line three", call_arg)
        self.assertNotIn("1: [CHANGED]", call_arg)
        self.assertNotIn("3: [CHANGED]", call_arg)

    @patch("core.code_scanner.agent_scanner.create_agent")
    def test__scanSingleFile__noChangedLinesMarker_whenChangedLinesIsNone(self, mock_create_agent):
        args = self._make_args()
        scanner = AgentScanner(args)
        mock_result = MagicMock()
        mock_result.data = FileScanResult(vulnerabilities=[])
        scanner.agent.run_sync = MagicMock(return_value=mock_result)

        file_content = "line one\nline two"
        with patch("os.path.isfile", return_value=True), \
             patch("builtins.open", mock_open(read_data=file_content)):
            scanner._scan_single_file("/fake/path.py", "path.py", changed_lines=None)

        call_arg = scanner.agent.run_sync.call_args[0][0]
        self.assertNotIn("[CHANGED]", call_arg)

    @patch("core.code_scanner.agent_scanner.create_agent")
    def test__scanSingleFile__printsVulnerabilitiesWithLineNumber(self, mock_create_agent):
        args = self._make_args()
        scanner = AgentScanner(args)
        vuln = Vulnerability(
            line_number=14,
            description="SQL Injection",
            remediation="Use parameterized queries",
            severity="Critical",
            vulnerability_type="SQL Injection",
        )
        mock_result = MagicMock()
        mock_result.output = FileScanResult(vulnerabilities=[vuln])
        scanner.agent.run_sync = MagicMock(return_value=mock_result)

        with patch("os.path.isfile", return_value=True), \
             patch("builtins.open", mock_open(read_data="some code")), \
             patch("builtins.print") as mock_print:
            scanner._scan_single_file("/fake/path.py", "path.py")

        printed = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertIn("Line 14", printed)
        self.assertIn("Critical", printed)
        self.assertIn("SQL Injection", printed)

    @patch("core.code_scanner.agent_scanner.create_agent")
    def test__scanSingleFile__printsVulnerabilitiesWithoutLineNumber(self, mock_create_agent):
        args = self._make_args()
        scanner = AgentScanner(args)
        vuln = Vulnerability(
            line_number=None,
            description="MD5 is weak",
            remediation="Use bcrypt",
            severity="High",
            vulnerability_type="Weak Cryptography",
        )
        mock_result = MagicMock()
        mock_result.output = FileScanResult(vulnerabilities=[vuln])
        scanner.agent.run_sync = MagicMock(return_value=mock_result)

        with patch("os.path.isfile", return_value=True), \
             patch("builtins.open", mock_open(read_data="some code")), \
             patch("builtins.print") as mock_print:
            scanner._scan_single_file("/fake/path.py", "path.py")

        printed = " ".join(str(c) for c in mock_print.call_args_list)
        self.assertNotIn("Line None", printed)
        self.assertIn("High", printed)
        self.assertIn("Weak Cryptography", printed)

    @patch("core.code_scanner.agent_scanner.create_agent")
    def test__scanChanges__usesGitRepoFiles_whenNoPrArgs(self, mock_create_agent):
        args = self._make_args(changes_only=True, repo=None, pr_number=None, directory="/repo")
        scanner = AgentScanner(args)
        scanner._scan_single_file = MagicMock()

        with patch("core.code_scanner.agent_scanner.get_changed_files_in_repo", return_value=["a.py"]), \
             patch("core.code_scanner.agent_scanner.get_local_changed_line_numbers", return_value={3, 5}) as mock_local_lines:
            scanner._scan_changes()

        mock_local_lines.assert_called_once_with("/repo", "a.py")
        scanner._scan_single_file.assert_called_once_with(
            os.path.join("/repo", "a.py"), display_name="a.py", changed_lines={3, 5}
        )

    @patch("core.code_scanner.agent_scanner.GithubIntegration")
    @patch("core.code_scanner.agent_scanner.create_agent")
    def test__scanChanges__usesPrFiles_whenRepoAndPrNumberSet(self, mock_create_agent, mock_github):
        args = self._make_args(
            changes_only=True, repo="owner/repo", pr_number=42,
            github_token="tok", directory="/repo"
        )
        scanner = AgentScanner(args)
        scanner._scan_single_file = MagicMock()

        with patch("core.code_scanner.agent_scanner.get_changed_files_in_pr", return_value=["b.py"]), \
             patch("core.code_scanner.agent_scanner.get_pr_changed_line_numbers", return_value={"b.py": {10, 11}}):
            scanner._scan_changes()

        scanner._scan_single_file.assert_called_once_with(
            os.path.join("/repo", "b.py"), display_name="b.py", changed_lines={10, 11}
        )

    @patch("core.code_scanner.agent_scanner.create_agent")
    def test__scanSingleFile__handlesAgentException(self, mock_create_agent):
        args = self._make_args()
        scanner = AgentScanner(args)
        scanner.agent.run_sync = MagicMock(side_effect=Exception("API error"))

        with patch("os.path.isfile", return_value=True), \
             patch("builtins.open", mock_open(read_data="some code")):
            # Should not raise — errors are caught and logged
            scanner._scan_single_file("/fake/path.py", "path.py")


if __name__ == "__main__":
    unittest.main()
