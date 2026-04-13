"""Utilities for posting inline review comments to GitHub pull requests."""

import logging

from github import Github

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


class GithubIntegration:
    """Wraps PyGithub to post inline PR review comments for scanner findings."""

    def __init__(self, args):
        self.repo_name = args.repo
        self.pr_number = args.pr_number
        self.github_token = args.github_token

        if self.github_token:
            self.gh = Github(self.github_token)
            self.repo = self.gh.get_repo(self.repo_name)
            self.pr = self.repo.get_pull(self.pr_number)

            commits = list(self.pr.get_commits())
            self.latest_commit = commits[-1] if commits else None
        else:
            self.gh = None

    def post_inline_comment(self, path: str, line: int, body: str):
        """
        Post an inline review comment on a specific line of a PR diff.
        Falls back to a regular issue comment if the line is not part of the diff.
        """
        if not self.gh or not self.latest_commit:
            return

        try:
            logging.info("Attempting to post PR review comment to %s:%s", path, line)
            self.pr.create_review_comment(
                body=body,
                commit=self.latest_commit,
                path=path,
                line=line,
            )
        except Exception:  # pylint: disable=broad-exception-caught
            logging.warning(
                "Could not post inline comment on %s:%s "
                "(line might not be part of pull request diff). "
                "Falling back to normal PR comment.",
                path,
                line,
            )
            try:
                fallback_body = f"**File: `{path}` (Line {line})**\n\n{body}"
                self.pr.create_issue_comment(fallback_body)
            except Exception:  # pylint: disable=broad-exception-caught
                logging.error("Failed to post fallback PR comment for %s:%s", path, line)
