"""
This is the runner of the codescan-ai CLI tool.
"""

from IPython.display import display_markdown

from core.code_scanner.code_scanner import CodeScanner
from core.utils.argument_parser import parse_arguments


def format_as_markdown(result):
    """
    Formats the scan result as Markdown.
    """
    output = "## Code Security Analysis Results\n"
    output += result
    return output


def main():
    """
    Main entry point for the CLI. Parses arguments, calls the centralized CodeScanner
    (which performs the scanning by using the AI provider in *args),
    and displays the results.
    """
    args = parse_arguments()
    scan_result = CodeScanner(args).scan()
    display_markdown(format_as_markdown(scan_result))


if __name__ == "__main__":
    main()
