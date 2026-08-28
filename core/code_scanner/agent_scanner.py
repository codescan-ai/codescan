"""
V2 agent-based scanner. Scans source files one at a time using a Pydantic-AI Agent
and streams structured FileScanResult output to stdout.
"""

import logging
import os

from core.agent import (
    FileScanResult,
    create_agent,
    get_pydantic_ai_model,
    resolve_system_prompt,
)
from core.utils.file_extractor import (
    get_changed_files_in_pr,
    get_changed_files_in_repo,
    get_local_changed_line_numbers,
    get_pr_changed_line_numbers,
)
from core.utils.github_integration import GithubIntegration

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)


# Directories that never contain first-party source worth scanning. Skipped by
# default in full-directory scans; users can override with repeated --exclude-dir.
DEFAULT_EXCLUDE_DIRS = frozenset({
    ".git", ".hg", ".svn",
    "node_modules", "bower_components", "vendor",
    "__pycache__", ".mypy_cache", ".pytest_cache", ".ruff_cache",
    ".venv", "venv", "env", ".tox",
    "dist", "build", "target", "out",
    ".next", ".nuxt", ".cache",
    ".idea", ".vscode",
})

# File extensions we recognise as source code. Anything else is skipped in a
# full-directory scan to avoid feeding binaries, images, and minified vendor
# bundles to the LLM.
SOURCE_EXTENSIONS = frozenset({
    # Python
    ".py", ".pyi", ".pyx",
    # JS / TS / web
    ".js", ".jsx", ".ts", ".tsx", ".mjs", ".cjs",
    ".vue", ".svelte", ".astro",
    ".html", ".htm", ".css", ".scss", ".sass", ".less",
    # PHP
    ".php", ".phtml", ".inc",
    # Ruby
    ".rb", ".erb", ".rake",
    # Go
    ".go",
    # Rust
    ".rs",
    # JVM
    ".java", ".kt", ".kts", ".scala", ".groovy",
    # C family
    ".c", ".h", ".cc", ".cpp", ".hpp", ".cxx", ".hxx", ".inl",
    # C#
    ".cs", ".fs", ".fsx",
    # Shell
    ".sh", ".bash", ".zsh", ".fish",
    # Perl
    ".pl", ".pm", ".t",
    # SQL
    ".sql",
    # Templates
    ".j2", ".jinja", ".jinja2", ".tmpl", ".tpl", ".mustache", ".hbs",
    # Elixir / Erlang
    ".ex", ".exs", ".erl", ".hrl",
    # Lua
    ".lua",
    # Swift / ObjC
    ".swift", ".m", ".mm",
    # Terraform / IaC
    ".tf", ".tfvars", ".bicep",
    # Config commonly containing security-sensitive data
    ".yml", ".yaml", ".toml",
    # Dockerfile-style (matched by name below too)
    ".dockerfile",
})

# Exact filenames (no extension) worth scanning.
SOURCE_FILENAMES = frozenset({
    "Dockerfile", "Containerfile", "Makefile", "Rakefile", "Gemfile",
})


def _is_source_file(name: str) -> bool:
    if name in SOURCE_FILENAMES:
        return True
    _, ext = os.path.splitext(name)
    return ext.lower() in SOURCE_EXTENSIONS


class AgentScanner:
    """
    Scans source code via the Pydantic AI agent, file by file.
    Optionally posts inline review comments to GitHub PRs.
    """

    def __init__(self, args) -> None:
        self.args = args
        model_str = get_pydantic_ai_model(args.provider, args.model)

        # Set OPENAI_BASE_URL for custom providers so Pydantic-AI targets the correct backend.
        if args.provider == "custom" and args.host:
            host_url = f"{args.host}:{args.port}" if args.port else args.host
            if args.endpoint:
                host_url += args.endpoint
            os.environ["OPENAI_BASE_URL"] = host_url
            # The OpenAI SDK requires a non-empty API key even for local servers that
            # don't authenticate. Fall back to a dummy value when no token is supplied.
            os.environ["OPENAI_API_KEY"] = args.token if args.token else "dummy"

        prompt_file = getattr(args, "prompt_file", None)
        prompt_preset = getattr(args, "prompt_preset", None) or "security"
        system_prompt = resolve_system_prompt(prompt_file=prompt_file, preset=prompt_preset)

        self.agent = create_agent(
            model_str=model_str,
            system_prompt=system_prompt,
            output_type=FileScanResult,
        )
        self.github_integration = (
            GithubIntegration(args)
            if args.repo and args.pr_number and args.github_token
            else None
        )

        # File-filter config, with defaults for callers (tests) that don't set them.
        self.max_file_bytes = getattr(args, "max_file_bytes", 262144) or 0
        exclude_dirs = getattr(args, "exclude_dirs", None)
        self.exclude_dirs = frozenset(exclude_dirs) if exclude_dirs else DEFAULT_EXCLUDE_DIRS

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
        for filepath in self._iter_scannable_files(self.args.directory):
            self._scan_single_file(
                filepath, display_name=os.path.relpath(filepath, self.args.directory)
            )

    def _iter_scannable_files(self, root_dir: str):
        """Yield paths under root_dir that pass the directory / extension / size filters."""
        for root, dirs, files in os.walk(root_dir):
            # Prune excluded directories in-place so os.walk doesn't descend into them.
            dirs[:] = [d for d in dirs if d not in self.exclude_dirs]

            for name in files:
                if not _is_source_file(name):
                    continue
                path = os.path.join(root, name)
                if self.max_file_bytes:
                    try:
                        size = os.path.getsize(path)
                    except OSError as e:
                        logging.debug("Cannot stat %s: %s", path, e)
                        continue
                    if size > self.max_file_bytes:
                        logging.debug(
                            "Skipping %s: size %d bytes exceeds --max-file-bytes %d",
                            path, size, self.max_file_bytes,
                        )
                        continue
                yield path

    def _scan_single_file(self, file_path: str, display_name: str, changed_lines: set = None):
        """Scan a single file and print any vulnerabilities found."""
        if not os.path.isfile(file_path):
            logging.warning("Skipping %s: Not a valid file or not found locally.", file_path)
            return

        try:
            with open(file_path, "r", encoding="utf-8") as f:
                content = f.read()
        except UnicodeDecodeError:
            logging.debug("Skipping %s: not UTF-8 text.", file_path)
            return
        except OSError as e:
            logging.warning("Skipping %s: %s", file_path, e)
            return

        if not content.strip():
            return

        logging.info("Scanning file: %s ...", display_name)

        def _format_line(idx, line):
            lineno = idx + 1
            if changed_lines and lineno in changed_lines:
                return f"{lineno}: [CHANGED] {line}"
            return f"{lineno}: {line}"

        numbered_content = "\n".join([_format_line(idx, line) for idx, line in enumerate(content.splitlines())])

        try:
            result = self.agent.run_sync(f"File: {display_name}\n\n{numbered_content}")
            scan_result = result.output

            if scan_result.vulnerabilities:
                print(f"\n--- Vulnerabilities found in {display_name} ---")
                md_output = ""
                for vuln in scan_result.vulnerabilities:
                    line_info = f"Line {vuln.line_number}: " if vuln.line_number else ""
                    md_output += f"  - **{line_info}[{vuln.severity}] {vuln.vulnerability_type}**\n"
                    md_output += f"  - **Issue**: {vuln.description}\n"
                    md_output += f"  - **Fix**: {vuln.remediation}\n"
                print(md_output)

                if self.github_integration:
                    for vuln in scan_result.vulnerabilities:
                        comment_body = (
                            f"**[{vuln.severity.upper()} SEVERITY] {vuln.vulnerability_type}**"
                            f"\n\n{vuln.description}"
                            f"\n\n**Suggested Fix:**\n{vuln.remediation}"
                        )
                        self.github_integration.post_inline_comment(
                            path=display_name,
                            line=vuln.line_number,
                            body=comment_body,
                        )
            else:
                logging.info("No vulnerabilities found in %s.", display_name)

        except Exception as e:  # pylint: disable=broad-exception-caught
            logging.error("Error scanning %s: %s", display_name, e)
