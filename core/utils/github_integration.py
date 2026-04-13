import logging
from github import Github

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

class GithubIntegration:
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
        if not self.gh or not self.latest_commit:
            return
            
        try:
            logging.info(f"Attempting to post PR review comment to {path}:{line}")
            self.pr.create_review_comment(
                body=body,
                commit_id=self.latest_commit,
                path=path,
                line=line
            )
        except Exception as e:
            # Inline commenting can fail if the specific line wasn't modified in the PR diff.
            logging.warning(f"Could not post inline comment on {path}:{line} (line might not be part of pull request diff) - {e}. Falling back to normal PR comment.")
            try:
                fallback_body = f"**File: `{path}` (Line {line})**\n\n{body}"
                self.pr.create_issue_comment(fallback_body)
            except Exception as fallback_e:
                logging.error(f"Failed to post fallback PR comment: {fallback_e}")
