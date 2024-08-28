# CodeScanAI

CodeScanAI utilizes a variety of AI models, including OpenAI, Gemini, and custom self-hosted AI servers, to scan your codebase for bad development practices. It is currently configure to catch potential security vulnerabilities, but will be extended to other use cases in the future.

It has been designed to enable  seamless integration into CI/CD pipelines like GitHub Actions, or can be used via a simple command. CodeScanAI enables developers to automatically detect potential security issues in their code throughout the development process. [Try it out today](#getting-started)!

## Features

- **Support for Multiple AI Models:**

  - **OpenAI Integration:**  Utilize OpenAI's advanced models, such as GPT-4, to scan your code and identify potential security vulnerabilities, OR
  - **Gemini Integration:** Tap into Gemini's expertise to analyze your code for security risks, OR
  - **Custom AI Server Integration:** Connect with self-hosted or private AI servers for security scans, offering fully customizable and self-managed AI solutions.

- **CI/CD Integration:**

  - Seamlessly integrate the CLI tool into GitHub Actions for automated security vulnerability scanning on every pull request.
  - Supports targeted scans on specific branches or changes within a repository.

- **Flexible Scanning Options:**
  - **Full Directory Scans:** Perform a comprehensive security analysis by scanning all files within a directory.
  - **Changes Only Scan:** Only scan those files that have chnaged since the last scan.
  - **PR-Specific Scans:** Target files modified in a specific pull request to optimize the scanning process and reduce overhead.

## Getting Started

### Prerequisites

- Python 3.10 or higher
- API keys for the supported AI models:
  - OpenAI API key
  - Gemini API key
  - Access to a custom AI server (host, port, and optional token)
- Set an environment variable for your API key(s).

```bash
export OPENAI_API_KEY = 'your_openai_api_key'
```
OR 

```bash
export GEMINI_API_KEY = 'your_gemini_api_key'
```

### Installation

#### Option 1: Install via pip

You can install the tool directly from the repository using pip:

```bash
pip install codescanai
```

This will allow you to use the `codescanai` command directly in your terminal.

#### Option 2: Clone the Repository

If you prefer to clone the repository and install the dependencies manually:

```bash
git clone https://github.com/codescan-ai/codescan.git
cd codescan
pip install -r requirements.txt
```

### Usage

#### Scanning files in  your current directory

```bash
codescanai --provider openai
```
OR if you're cloning the repository,
```bash
python3 -m core.runner --provider openai
```

#### Scanning with a Custom AI Server

To scan code using a custom AI server:

```bash
codescanai --provider custom --host http://localhost --port 5000 --token your_token --directory path/to/your/code
```

### Supported arguments

| name           | description                                               | required | default        |
| -------------- | --------------------------------------------------------- | -------- | -------------- |
| `provider`     | <p>AI provider</p>                                        | `true`   | `""`           |
| `model`        | <p>AI model to use</p>                                    | `false`  | `""`           |
| `directory`    | <p>Directory to scan</p>                                  | `false`  | `.`            |
| `changes_only` | <p>Scan only changed files</p>                            | `false`  | `false`        |
| `repo`         | <p>GitHub repository</p>                                  | `false`  | `""`           |
| `pr_number`    | <p>Pull request number</p>                                | `false`  | `""`           |
| `github_token` | <p>GitHub API token</p>                                   | `false`  | `""`           |
| `host`         | <p>Custom AI server host</p>                              | `false`  | `""`           |
| `port`         | <p>Custom AI server port</p>                              | `false`  | `""`           |
| `token`        | <p>Token for authenticating with the custom AI server</p> | `false`  | `""`           |
| `endpoint`     | <p>API endpoint for the custom server</p>                 | `false`  | `/api/v1/scan` |

### Supported AI Providers

- **OpenAI:** Utilizes GPT models for in-depth security analysis.
- **Gemini:** Delivers strong security insights through Gemini's advanced capabilities.
- **Custom:** Connects with self-hosted or private AI servers for fully customizable solutions.

### Limitations

- **Large number of files:** We currently do not support scalable way to scan a large number of files on a single run. Depending on the capacity of your AI Provider, you might run into a `rate_limit_exceeded` error. To do this, you can create a custom solution that breaks down the number of files for each run. 

## Future Work

- **Batch Processing:** For the limitation above, a future version will be to implement batch processing for a large number of files.

- **Caching Implementation:** A caching mechanism to store results of previously scanned files, reducing the number of API calls and optimizing performance.

- **Expanded Git Provider Support:** The tool is currently integrated with GitHub for PR-based scanning, future plans include extending support to other Git providers like GitLab, Bitbucket, and Azure Repos.

- **Expanded Development tools:** This will be a plan to expand this tool to be accessible in other development environments. For example, as a VSCode extension.

## Contributing

Contributions are welcome! Please fork the repository and submit a pull request with your improvements.

## License

This project is licensed under the MIT License. See the [LICENSE](LICENSE) file for details.