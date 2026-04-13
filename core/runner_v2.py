"""
This is the V2 runner of the codescan-ai CLI tool.
It utilizes pydantic-ai orchestrations to process data file by file.
"""

from core.code_scanner.agent_scanner import AgentScanner
from core.utils.argument_parser import parse_arguments


def main():
    """
    Main entry point for the V2 CLI. Parses arguments, calls the AgentScanner
    (which performs the file-by-file scanning by using the AI agent),
    and displays the results progressively.
    """
    args = parse_arguments()
    AgentScanner(args).scan()


if __name__ == "__main__":
    main()
