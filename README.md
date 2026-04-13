[![Release and Publish](https://github.com/codescan-ai/codescan/actions/workflows/release-publish.yml/badge.svg)](https://github.com/codescan-ai/codescan/actions/workflows/release-publish.yml)
![GitHub release (latest by date)](https://img.shields.io/github/v/release/codescan-ai/codescan)
![GitHub issues](https://img.shields.io/github/issues/codescan-ai/codescan)
![GitHub pull requests](https://img.shields.io/github/issues-pr/codescan-ai/codescan)
![GitHub](https://img.shields.io/github/license/codescan-ai/codescan)

# CodeScanAI

CodeScanAI utilizes a variety of AI models to scan your codebase for security vulnerabilities. It leverages powerful LLM models to identify risks and provide actionable remediation suggestions. The currently supported AI providers include:

- OpenAI,
- Google Gemini, and
- custom self-hosted AI servers (Ollama, etc.).

It has been designed to integrate seamlessly into CI/CD pipelines like GitHub Actions, or can be used via a simple CLI command locally.

Check out the detailed [demo and setup](https://github.com/codescan-ai/codescanai-demo) and try it out today!

## What's new in v0.1.2

- **Pydantic-AI agent scanner:** Files are now scanned one at a time by a structured AI agent, returning typed `FileScanResult` output instead of a raw markdown string.
- **Inline PR review comments:** When running a PR scan, findings are posted as inline review comments directly on the relevant line in the diff. Falls back to a regular issue comment for architectural findings with no specific line.
- **Diff-aware analysis:** When scanning a PR or local git diff, changed lines are highlighted with a `[CHANGED]` marker in the prompt. The agent prioritises those lines while retaining full file context for accurate data flow analysis.

## Features

- **Flexible Scanning Options:**
  - **Full Directory Scans:** Comprehensive security analysis across all files in a directory.
  - **Changes Only Scan:** Scan only files changed since the last commit (`--changes_only`).
  - **PR-Specific Scans:** Scan only files modified in a specific pull request, with findings posted as inline review comments.

- **Diff-Aware PR Analysis:**

  When scanning a pull request, CodeScanAI fetches the exact lines changed in the diff and annotates them for the agent. This focuses the analysis on new and modified code while preserving full file context to avoid false negatives.

- **Support for Multiple AI Models:**

  Supports OpenAI, Google Gemini, and any self-hosted OpenAI-compatible server. Support for additional providers can be added on demand.

- **CI/CD Integration:**

  Integrate into GitHub Actions for automated security scanning on every pull request. Supports targeted scans on specific branches or changes within a repository.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- API key for your chosen provider:
  - OpenAI API key, OR
  - Gemini API key, OR
  - Access to a custom AI server (host, port, and optional token)

```bash
export OPENAI_API_KEY='your_openai_api_key'

export GEMINI_API_KEY='your_gemini_api_key'
```

### Installation

#### Option 1: Install via pip

```bash
pip install codescanai
```

This will make the `codescanai` command available directly in your terminal.

#### Option 2: Clone the Repository

```bash
git clone https://github.com/codescan-ai/codescan.git
cd codescan
pip install -r requirements.txt
```

### Usage

#### Scan all files in your current directory

```bash
codescanai --provider openai
```

Or if you cloned the repository:

```bash
python3 -m core.runner_v2 --provider openai
```

#### Scan only changed files (local git diff)

```bash
codescanai --provider openai --changes_only
```

#### Scan a GitHub pull request

```bash
codescanai --provider openai \
  --repo owner/repo \
  --pr_number 42 \
  --github_token your_github_token
```

Findings will be posted as inline review comments on the PR.

#### Scan with a Custom AI Server

```bash
codescanai --provider custom --host http://localhost --port 5000 --token your_token --directory path/to/code
```

Using locally running [Ollama](https://github.com/ollama/ollama):

```bash
codescanai --provider custom --model llama3 --host http://localhost --port 11434 --endpoint /api/generate --directory path/to/code
```

### Supported arguments

| name           | description                                               | required | default        |
| -------------- | --------------------------------------------------------- | -------- | -------------- |
| `provider`     | AI provider (`openai`, `gemini`, `custom`)                | `true`   | `""`           |
| `model`        | AI model to use                                           | `false`  | `""`           |
| `directory`    | Directory to scan                                         | `false`  | `.`            |
| `changes_only` | Scan only files changed in the local git repo             | `false`  | `false`        |
| `repo`         | GitHub repository (`owner/repo`)                          | `false`  | `""`           |
| `pr_number`    | Pull request number                                       | `false`  | `""`           |
| `github_token` | GitHub API token (required for PR scans)                  | `false`  | `""`           |
| `host`         | Custom AI server host                                     | `false`  | `""`           |
| `port`         | Custom AI server port                                     | `false`  | `""`           |
| `token`        | Token for authenticating with the custom AI server        | `false`  | `""`           |
| `endpoint`     | API endpoint for the custom server                        | `false`  | `/api/v1/scan` |

### Limitations

- **Rate limits:** Depending on your AI provider's capacity, scanning a large number of files in a single run may hit rate limits. The V2 scanner processes files one at a time, which helps, but you may still need to break up very large directories manually.

## Future Work

- **Caching:** Store results of previously scanned files to reduce API calls and speed up repeat scans.

- **Expanded Git Provider Support:** Currently integrated with GitHub. Future plans include GitLab, Bitbucket, and Azure Repos.

- **Expanded Development Tools:** Plans to make CodeScanAI accessible as a VSCode extension and in other development environments.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your improvements.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.
