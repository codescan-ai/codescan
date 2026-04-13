import logging
import os

from core.agent import (
    create_agent, 
    get_pydantic_ai_model, 
    SECURITY_AGENT_PROMPT, 
    FileScanResult
)

from core.utils.file_extractor import (
    get_changed_files_in_pr,
    get_changed_files_in_repo,
    get_pr_changed_line_numbers,
    get_local_changed_line_numbers,
)
from core.utils.github_integration import GithubIntegration

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

class AgentScanner:
    """
    This class defines the logic for scanning source code via the Pydantic AI agent.
    It streams results file-by-file and optionally posts direct inline comments to GitHub PRs.
    """

    def __init__(self, args) -> None:
        self.args = args
        model_str = get_pydantic_ai_model(args.provider, args.model)
        
        # We need to set OPENAI_BASE_URL if its a custom provider 
        # so that Pydantic-AI's OpenAI integration targets the correct backend
        if args.provider == "custom" and args.host:
            host_url = f"{args.host}:{args.port}" if args.port else args.host
            if args.endpoint:
                host_url += args.endpoint
            os.environ["OPENAI_BASE_URL"] = host_url
            if args.token:
                os.environ["OPENAI_API_KEY"] = args.token
                
        self.agent = create_agent(
            model_str=model_str,
            system_prompt=SECURITY_AGENT_PROMPT,
            result_type=FileScanResult
        )
        self.github_integration = GithubIntegration(args) if args.repo and args.pr_number and args.github_token else None

    def scan(self):
        """
        Scans the code by identifying files based on PR context or local directory
        and iterates through them using the Pydantic AI agent.
        """
        if self.args.changes_only or (self.args.repo and self.args.pr_number):
            return self._scan_changes()
        return self._scan_files()

    def _scan_changes(self):
        try:
            if self.args.repo and self.args.pr_number:
                changed_files = get_changed_files_in_pr(
                    self.args.repo, self.args.pr_number, self.args.github_token
                )
                changed_line_map = get_pr_changed_line_numbers(
                    self.args.repo, self.args.pr_number, self.args.github_token
                )
            else:
                changed_files = get_changed_files_in_repo(self.args.directory)
                changed_line_map = None
        except ValueError as e:
            logging.error(e)
            return

        if not changed_files:
            logging.info("No changes detected.")
            return

        for filename in changed_files:
            filepath = os.path.join(self.args.directory, filename)
            if changed_line_map is not None:
                changed_lines = changed_line_map.get(filename, set())
            else:
                changed_lines = get_local_changed_line_numbers(self.args.directory, filename)
            self._scan_single_file(filepath, display_name=filename, changed_lines=changed_lines)

    def _scan_files(self):
        file_paths = []
        for root, _, files in os.walk(self.args.directory):
            for file in files:
                file_paths.append(os.path.join(root, file))

        for filepath in file_paths:
            self._scan_single_file(filepath, display_name=os.path.relpath(filepath, self.args.directory))
            
    def _scan_single_file(self, file_path: str, display_name: str, changed_lines: set = None):
        if not os.path.isfile(file_path):
            logging.warning(f"Skipping {file_path}: Not a valid file or not found locally.")
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except Exception as e:
            logging.warning(f"Skipping {file_path}: {e}")
            return
            
        if not content.strip():
            return
            
        logging.info(f"Scanning file: {display_name} ...")
        
        try:
            # Prefix each line with its line number. Mark changed lines when scanning a diff.
            lines = content.splitlines()
            def _format_line(idx, line):
                lineno = idx + 1
                if changed_lines and lineno in changed_lines:
                    return f"{lineno}: [CHANGED] {line}"
                return f"{lineno}: {line}"
            numbered_content = "\n".join([_format_line(idx, line) for idx, line in enumerate(lines)])
            
            # Sync run of the Pydantic-AI Agent returning structured data
            result = self.agent.run_sync(f"File: {display_name}\n\n{numbered_content}")
            scan_result = result.data
            
            if scan_result.vulnerabilities:
                print(f"\n--- Vulnerabilities found in {display_name} ---")
                md_output = ""
                for vuln in scan_result.vulnerabilities:
                    line_info = f"Line {vuln.line_number}: " if vuln.line_number else ""
                    md_output += f"  - **{line_info}[{vuln.severity}] {vuln.vulnerability_type}**\n"
                    md_output += f"  - **Issue**: {vuln.description}\n"
                    md_output += f"  - **Fix**: {vuln.remediation}\n"
                    
                print(md_output)
                
                # Report to GitHub PR
                if self.github_integration:
                    for vuln in scan_result.vulnerabilities:
                        self.github_integration.post_inline_comment(
                            path=display_name,
                            line=vuln.line_number,
                            body=f"**[{vuln.severity.upper()} SEVERITY] {vuln.vulnerability_type}**\n\n{vuln.description}\n\n**Suggested Fix:**\n{vuln.remediation}"
                        )
            else:
                logging.info(f"No vulnerabilities found in {display_name}.")
                
        except Exception as e:
            logging.error(f"Error scanning {display_name}: {e}")
