"""
Defines the structured output types, agent factory, and pre-configured system prompts
used by the V2 Pydantic-AI scanner.
"""

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
    return Agent(
        model_str,
        output_type=output_type,
        system_prompt=system_prompt,
    )


# --- Define pre-configured Agent Prompts for laser-focused tasks ---

SECURITY_AGENT_PROMPT = (
    "You are an expert in software security analysis, adept at identifying and explaining "
    "potential vulnerabilities in code. "
    "You will be given complete code snippets from various applications. "
    "EVERY line of the source code is prefixed with its exact line number "
    "(e.g. `14: def foo():`). "
    "Your task is to analyze the provided code, pinpoint potential security risks, "
    "and offer clear suggestions for enhancing the application's security posture. "
    "Focus on the critical issues that could impact the overall security of the application. "
    "You MUST be exhaustive. Carefully audit the entire script from top to bottom "
    "and return EVERY vulnerability you find. Do not stop at the first issue. "
    "If any are found, use the explicitly provided line numbers to pinpoint the defect "
    "where possible. For architectural or multi-line issues, you may omit the line number. "
    "Also, strictly provide an actionable `remediation` that makes suggestions on how to "
    "rewrite or fix the code securely. "
    "If no vulnerabilities are found, return an empty list. "
    "When scanning a pull request or diff, some lines will be marked with `[CHANGED]` "
    "after the line number (e.g. `14: [CHANGED] def foo():`). "
    "These lines are newly added or modified in the change under review. "
    "Prioritise your analysis on `[CHANGED]` lines, but use the full file context — "
    "imports, surrounding functions, class definitions, and data flow — to assess "
    "whether those changes introduce or worsen a vulnerability."
)

PERFORMANCE_AGENT_PROMPT = (
    "You are a Senior Staff Software Engineer laser-focused on performance optimization. "
    "Analyze the following code for memory leaks, O(N^2) bottlenecks, or CPU inefficiencies. "
    "Pinpoint exact line numbers and return a list of performance issues. "
    "If none are found, return an empty list."
)

CLEAN_CODE_AGENT_PROMPT = (
    "You are an expert in code refactoring and Clean Code methodologies. "
    "Analyze the code for anti-patterns, confusing variable names, massive functions, "
    "or high cyclomatic complexity. "
    "Pinpoint exact line numbers and return a list of maintainability issues. "
    "If the code is perfectly clean, return an empty list."
)
