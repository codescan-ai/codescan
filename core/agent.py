"""
Defines the structured output types, agent factory, and system-prompt resolution
used by the V2 Pydantic-AI scanner.

Prompts live as Markdown under `core/prompts/`, not as Python string constants.
This keeps prompt iteration diffable and lets users override them at the CLI
without touching source. See `resolve_system_prompt` for the lookup order.
"""

from importlib import resources
from pathlib import Path
from typing import Optional, Type

from pydantic import BaseModel, Field
from pydantic_ai import Agent


class Vulnerability(BaseModel):
    """Represents a single security vulnerability found in a file."""

    line_number: Optional[int] = Field(
        default=None,
        description=(
            "The exact line number where the issue is found inside the file. "
            "Omit if the issue is architectural or spans multiple lines."
        ),
    )
    description: str = Field(
        description="A detailed description of the issue and why it is a security risk."
    )
    remediation: str = Field(
        description="Actionable suggestion or code snippet on how to fix this specific vulnerability."
    )
    severity: str = Field(description="Severity measure (Low, Medium, High, Critical)")
    vulnerability_type: str = Field(
        description="The category of issue (e.g. SQL Injection, Big-O inefficiency, etc.)"
    )


class FileScanResult(BaseModel):
    """Structured result returned by the agent for a single scanned file."""

    vulnerabilities: list[Vulnerability] = Field(
        description="List of issues found in the file. Empty if zero issues are found."
    )


def get_pydantic_ai_model(provider: str, model: Optional[str]) -> str:
    """Map a CLI provider name and optional model string to a Pydantic-AI model identifier."""
    if provider == "openai":
        return f"openai:{model or 'gpt-4o-mini'}"
    if provider == "gemini":
        return f"gemini:{model or 'gemini-1.5-flash'}"
    if provider == "custom":
        # Falls back to the OpenAI-compatible interface via OPENAI_BASE_URL
        return f"openai:{model or 'custom-model'}"
    return "openai:gpt-4o-mini"


def create_agent(
    model_str: str, system_prompt: str, output_type: Type[BaseModel] = FileScanResult
) -> Agent:
    """Creates and returns a Pydantic-AI Agent configured with the given model, prompt, and output schema."""
    return Agent(
        model_str,
        output_type=output_type,
        system_prompt=system_prompt,
    )


# --- System prompt resolution ---------------------------------------------------

PROMPT_PRESETS = ("security", "performance", "clean_code")
DEFAULT_PROMPT_PRESET = "security"


def _load_preset(name: str) -> str:
    """Read a bundled preset prompt from `core/prompts/<name>.md`."""
    if name not in PROMPT_PRESETS:
        raise ValueError(
            f"Unknown prompt preset '{name}'. Valid presets: {', '.join(PROMPT_PRESETS)}."
        )
    text = resources.files("core.prompts").joinpath(f"{name}.md").read_text(encoding="utf-8")
    text = text.strip()
    if not text:
        raise ValueError(f"Bundled prompt preset '{name}' is empty.")
    return text


def resolve_system_prompt(
    prompt_file: Optional[str] = None,
    preset: str = DEFAULT_PROMPT_PRESET,
) -> str:
    """
    Return the system prompt to use.

    Order of precedence:
      1. `prompt_file` — an explicit path to a text/markdown file on disk.
      2. `preset` — one of the bundled prompts in `core/prompts/`.
    """
    if prompt_file:
        path = Path(prompt_file).expanduser()
        if not path.is_file():
            raise FileNotFoundError(f"Prompt file not found: {path}")
        text = path.read_text(encoding="utf-8").strip()
        if not text:
            raise ValueError(f"Prompt file is empty: {path}")
        return text
    return _load_preset(preset)


# Convenience module-level constants for callers that want the built-ins directly
# (e.g. evals, tests).
SECURITY_AGENT_PROMPT = _load_preset("security")
PERFORMANCE_AGENT_PROMPT = _load_preset("performance")
CLEAN_CODE_AGENT_PROMPT = _load_preset("clean_code")
