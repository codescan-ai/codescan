# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

### Install dependencies
```bash
pip install -r requirements.txt
pip install -r requirements_ci.txt  # dev/linting tools
```

### Run tests
```bash
# All tests
python -m unittest discover -s core_tests -p "*.py"

# Single test file
python -m unittest core_tests.runner_test
```

### Lint and format
```bash
pylint core/
isort --profile=black --check-only core/ core_tests/
isort --profile=black core/ core_tests/  # to fix imports
```

### Build
```bash
python -m build
```

### Run evals

Evals verify that the V2 agent scanner still catches expected vulnerabilities across 5 fixture files (`evals/fixtures/`). Run them after any change to `core/agent.py`, `core/code_scanner/agent_scanner.py`, or the system prompt.

```bash
# Standard model (gpt-4o-mini) — all fixtures should pass
set -a && source .env && set +a
python3 evals/run_evals.py --provider openai --model gpt-4o-mini

# Advanced model (gpt-4o) — stricter; also requires YAML deserialization,
# race condition, JWT algorithm confusion, and timing attack findings
python3 evals/run_evals.py --provider openai --model gpt-4o

# Single fixture only
python3 evals/run_evals.py --provider openai --model gpt-4o-mini --fixture auth_service.py
```

Findings are split into two tiers in `evals/expected_findings.json`:
- **standard** — required from any model (SQL injection, XSS, path traversal, pickle, hardcoded secrets, etc.)
- **advanced** — only required when running gpt-4o (YAML code execution, race conditions, JWT algorithm confusion, timing attacks)

Exit code 0 = all fixtures at or above the 80% threshold. Exit code 1 = one or more failed.
### Run the CLI locally
```bash
# V1 runner (sends all files to AI at once)
python3 -m core.runner --provider openai

# V2 runner (file-by-file via Pydantic-AI agent)
python3 -m core.runner_v2 --provider openai
```

## Architecture

CodeScanAI is a CLI tool that scans codebases for security vulnerabilities using AI models.

### Two parallel codepaths

There are two scanner implementations that share the same CLI argument surface (`core/utils/argument_parser.py`):

1. **V1 (`core/runner.py` → `core/code_scanner/code_scanner.py`)**: Aggregates all file content into a single code summary, sends it to the AI provider in one call, returns a markdown string. Uses the provider abstraction layer.

2. **V2 (`core/runner_v2.py` → `core/code_scanner/agent_scanner.py`)**: Iterates file-by-file, runs a Pydantic-AI `Agent` synchronously on each, and streams structured `FileScanResult` output to stdout. Also supports posting inline PR review comments via `GithubIntegration`. This is the more feature-rich path.

The active entrypoint is `core.runner_v2:main` (V2), set in `pyproject.toml` under `[project.scripts]`.

### Provider abstraction (V1 only)

`core/providers/base_ai_provider.py` defines the `BaseAIProvider` interface with a single `scan_code(code_summary)` method. Concrete implementations:
- `OpenAIProvider` — uses `openai` SDK
- `GoogleGeminiAIProvider` — uses `google-generativeai`
- `CustomAIProvider` — HTTP requests to a self-hosted server (Ollama, etc.)

`core/utils/provider_creator.py` maps CLI `--provider` values to provider classes.

### Pydantic-AI agent (V2 only)

`core/agent.py` defines structured output types (`Vulnerability`, `FileScanResult`) and factory functions. It also holds pre-configured system prompts for different scan modes: `SECURITY_AGENT_PROMPT`, `PERFORMANCE_AGENT_PROMPT`, `CLEAN_CODE_AGENT_PROMPT`. Custom providers route through the OpenAI-compatible interface via `OPENAI_BASE_URL`.

### GitHub integration

`core/utils/github_integration.py` (`GithubIntegration`) is used only in V2. It posts inline PR review comments using PyGithub. Falls back to a regular issue comment if the line isn't in the PR diff.

`core/utils/file_extractor.py` handles both local git-diff file discovery and PR file listing via the GitHub API, shared by both V1 and V2.

### Scan modes

Both runners support three modes driven by CLI args:
- **Full scan** (default): walks `--directory` and scans all files
- **Changes only** (`--changes_only`): scans files changed in local git repo
- **PR scan** (`--repo` + `--pr_number` + `--github_token`): fetches changed files from a GitHub PR
