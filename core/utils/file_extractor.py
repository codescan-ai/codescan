"""
This module contains utilities for checking 
if a directory is a Git repository, retrieving changed files from local repositories 
or GitHub pull requests.
"""

import logging
import os
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
