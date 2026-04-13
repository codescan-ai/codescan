"""
This module contains utilities for checking
if a directory is a Git repository, retrieving changed files from local repositories
or GitHub pull requests.
"""

import logging
import os
import re
import subprocess

from github import Github

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def is_git_repo(directory):
    """
    Checks if the directory is a valid Git repository.

    Parameters:
        directory (string): The path to the directory.

    Returns:
        bool: Representing if the directory is a Git repository.
    """
    try:
        subprocess.check_output(
            ["git", "-C", directory, "rev-parse", "--is-inside-work-tree"],
            stderr=subprocess.STDOUT,
        )
        return True
    except subprocess.CalledProcessError:
        logging.error("Directory is not a valid Git repository: %s", directory)
        return False


def _parse_changed_lines(patch: str) -> set:
    """
    Parse a unified diff patch string and return the set of new-file line numbers
    that correspond to added or modified lines (i.e. lines prefixed with '+').
    """
    changed = set()
    new_line = 0
    for line in patch.split("\n"):
        hunk = re.match(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,\d+)? @@", line)
        if hunk:
            new_line = int(hunk.group(1))
        elif line.startswith("+"):
            changed.add(new_line)
            new_line += 1
        elif line.startswith("-"):
            pass  # removed line — does not advance the new-file counter
        else:
            new_line += 1  # context line
    return changed


def get_pr_changed_line_numbers(repo_name, pr_number, github_token):
    """
    Returns a mapping of filename -> set of new-file line numbers that were
    added or modified in the pull request.

    Parameters:
        repo_name (string): The name of the repository (e.g. 'owner/repo').
        pr_number (int): The pull request number.
        github_token (string): A GitHub personal access token.

    Returns:
        dict[str, set[int]]: Filename to changed line numbers.
    """
    if not github_token:
        raise ValueError("GitHub token is required for scanning PR changes.")

    files = Github(github_token).get_repo(repo_name).get_pull(pr_number).get_files()
    result = {}
    for f in files:
        if f.patch:
            result[f.filename] = _parse_changed_lines(f.patch)
        else:
            result[f.filename] = set()
    return result


def get_local_changed_line_numbers(directory, filename):
    """
    Returns the set of new-file line numbers that are modified (unstaged) for a
    given file in a local git repository.

    Parameters:
        directory (string): The path to the git repository root.
        filename (string): The file path relative to the repository root.

    Returns:
        set[int]: Changed line numbers, or an empty set on any error.
    """
    try:
        patch = subprocess.check_output(
            ["git", "-C", directory, "diff", "--", filename], text=True
        )
        return _parse_changed_lines(patch)
    except subprocess.CalledProcessError as e:
        logging.warning("Could not get diff for %s: %s", filename, e)
        return set()


def get_changed_files_in_pr(repo_name, pr_number, github_token):
    """
    Returns a list of files that have been changed in the specified pull request.

    Parameters:
        repo_name (string): The name of the repository.
        pr_number (int): The number representing the specified pull request.
        github_token(string): Your github token.

    Returns:
        list[string]: A list of all changed filenames in the pull request.
    """

    if not github_token:
        logging.error("GitHub token is required for scanning PR changes.")
        raise ValueError("GitHub token is required for scanning PR changes.")

    files = Github(github_token).get_repo(repo_name).get_pull(pr_number).get_files()

    changed_files = [file.filename for file in files]
    logging.info(
        "Fetched %d changed files from PR #%d in %s repository.",
        len(changed_files),
        pr_number,
        repo_name,
    )
    return changed_files


def get_changed_files_in_repo(directory):
    """
    Returns a list of files that have been changed locally.

    Parameters:
        directory (string): The path to the directory.

    Returns:
        list[string]: A list of all changed filenames in the directory.
    """
    if not is_git_repo(directory):
        logging.error("Directory is not a valid Git repository: %s", directory)
        raise ValueError("Directory is not a valid Git repository.")

    changed_files = []
    try:
        os.chdir(directory)
        result = subprocess.check_output(["git", "diff", "--name-only"], text=True)
        if result.strip():
            changed_files = result.strip().split("\n")
            logging.info(
                "Found %d changed files in local repository", len(changed_files)
            )
    except subprocess.CalledProcessError as e:
        logging.error("Error getting changed files: %s", e)
    return changed_files
