"""
This module provides util methods for extracting code summaries from a list of files.
"""

import logging
import os

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


def read_files_and_extract_code_summary(file_paths):
    """
    Reads the content of the given files and generates a code summary.
    Skips files that cannot be decoded as text.

    Parameters:
        file_path (list[string]): The list of filenames to extract code from.

    Returns:
        string: summary of code extracted from the input files.
    """
    code_summary = ""
    for file_path in file_paths:
        if os.path.isfile(file_path):
            try:
                with open(file_path, "r", encoding="utf-8") as file:
                    logging.info("Reading: %s", file_path)
                    code_summary += f"\n\nFile: {os.path.basename(file_path)}\n"
                    code_summary += file.read()
            except (UnicodeDecodeError, IOError) as e:
                logging.warning("Skipping file %s: %s", file_path, e)
        else:
            logging.warning("Skipped %s: Not a valid file.", file_path)
    return code_summary


def generate_code_summary(directory, changed_files):
    """
    Generates a summary of the code from the changed files.

    Parameters:
        directory (string) : The path to the directory.
        changed_files (list[string]): The list of filenames to extract code from.

    Returns:
        string: summary of code extracted from the input files.
    """
    file_paths = [os.path.join(directory, file) for file in changed_files]
    return read_files_and_extract_code_summary(file_paths)
