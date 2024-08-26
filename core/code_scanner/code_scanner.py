"""
This module defines a class that scans/analyse code based on the input args using AI providers.
This is the brain of this application and all core logic will be referenced here.
"""

import logging
import os

from core.utils.code_summary_extractor import (
    generate_code_summary,
    read_files_and_extract_code_summary,
)
from core.utils.file_extractor import get_changed_files_in_pr, get_changed_files_in_repo
from core.utils.provider_creator import init_provider

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class CodeScanner:
    """
    This class defines the logic for scanning source code based on the context provided in **args**
    """

    def __init__(self, args) -> None:
        self.args = args
        self.provider = init_provider(
            args.provider, args.model, args.host, args.port, args.token, args.endpoint
        )

    def scan(self):
        """
        Scans the code based on the provided arguments and AI client.
        """
        if self.args.changes_only:
            # Only scan new changes. This is supported in Git repositories only(for now).
            return self._scan_changes()
        return self._scan_files()

    def _scan_changes(self):
        """
        Scans only the files that have been changed in the specified directory or PR.
        """
        try:
            if self._is_repo_valid() and self._is_pr_number_valid():
                changed_files = get_changed_files_in_pr(
                    self.args.repo, self.args.pr_number, self.args.github_token
                )
            else:
                changed_files = get_changed_files_in_repo(self.args.directory)
        except ValueError as e:
            logging.error(e)
            return str(e)

        if not changed_files:
            logging.info("No changes detected in the directory.")
            return "No changes detected in the directory."

        code_summary = generate_code_summary(self.args.directory, changed_files)

        return self.provider.scan_code(code_summary)

    def _scan_files(self):
        """
        Scans all files in the specified directory.
        """
        file_paths = []
        for root, _, files in os.walk(self.args.directory):
            for file in files:
                file_paths.append(os.path.join(root, file))

        code_summary = read_files_and_extract_code_summary(file_paths)
        return self.provider.scan_code(code_summary)

    def _is_repo_valid(self):
        return len(self.args.repo) > 0

    def _is_pr_number_valid(self):
        return self.args.pr_number > 0
