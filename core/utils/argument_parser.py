"""
This module provides util methods for understanding and parsing the arguments sent by user in the CLI.
"""

import argparse

from core.agent import DEFAULT_PROMPT_PRESET, PROMPT_PRESETS


def parse_arguments():
    """
    Parses command-line arguments for the AI-based code scanner.
    """
    parser = argparse.ArgumentParser(
        description="A CLI tool for powered by GenAI to access vulnerability of codebases and provide suggestions."
    )

    parser.add_argument(
        "--provider",
        type=str,
        required=True,
        choices=["openai", "gemini", "custom"],
        help="Select the AI provider",
    )
    parser.add_argument(
        "--directory",
        type=str,
        default=".",
        help="Directory to scan (defaults to root)",
    )
    parser.add_argument(
        "--model",
        type=str,
        help="AI model to use (optional, defaults vary by provider. See [gemini: gemini-pro, openai: gpt-4o-mini])",
    )
    parser.add_argument(
        "--changes_only",
        action="store_true",
        help="Scan only changed files in a git repository",
    )

    # Additional arguments for PR scanning
    parser.add_argument(
        "--repo", type=str, help="GitHub repository in the format 'owner/repo'"
    )
    parser.add_argument("--pr_number", type=int, help="Pull request number")
    parser.add_argument("--github_token", help="GitHub API token")

    # Additional arguments for custom provider
    parser.add_argument(
        "--host", type=str, help="Custom AI server host (e.g., http://localhost)"
    )
    parser.add_argument("--port", type=int, help="Custom AI server port (e.g., 5000)")
    parser.add_argument(
        "--token", type=str, help="Token for authenticating with the custom AI server"
    )
    parser.add_argument(
        "--endpoint",
        type=str,
        default="/api/v1/scan",
        help="API endpoint for the custom server",
    )

    # Prompt selection
    parser.add_argument(
        "--prompt-file",
        dest="prompt_file",
        type=str,
        default=None,
        help=(
            "Path to a text/markdown file containing the system prompt. "
            "Overrides --prompt-preset when supplied."
        ),
    )
    parser.add_argument(
        "--prompt-preset",
        dest="prompt_preset",
        type=str,
        default=DEFAULT_PROMPT_PRESET,
        choices=list(PROMPT_PRESETS),
        help="Which built-in prompt to use when --prompt-file is not supplied.",
    )

    # File-filtering knobs for full-directory scans
    parser.add_argument(
        "--max-file-bytes",
        dest="max_file_bytes",
        type=int,
        default=262144,
        help=(
            "Skip files larger than this many bytes when doing a full-directory "
            "scan. Default: 262144 (256 KiB). Set to 0 to disable the cap."
        ),
    )
    parser.add_argument(
        "--exclude-dir",
        dest="exclude_dirs",
        action="append",
        default=None,
        help=(
            "Directory name to skip during a full-directory scan. May be given "
            "multiple times. If omitted, a built-in list of common junk "
            "directories (.git, node_modules, __pycache__, ...) is used."
        ),
    )

    return parser.parse_args()
