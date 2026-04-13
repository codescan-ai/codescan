"""
run_evals.py — Eval harness for CodeScanAI's V2 agent scanner.

For each fixture file, runs the agent and checks the structured output
against the expected findings in expected_findings.json.

A required finding is matched if the scanner returns at least one
Vulnerability whose vulnerability_type (lowercased) contains any of the
expected keywords.

Exit code 0 = all files passed their threshold.
Exit code 1 = one or more files failed.

Usage:
    python evals/run_evals.py [--provider openai] [--model gpt-4o-mini]
"""

import argparse
import json
import os
import sys
from pathlib import Path
from types import SimpleNamespace
from typing import Optional

# Make sure the repo root is on the path when running from evals/
sys.path.insert(0, str(Path(__file__).parent.parent))

from core.code_scanner.agent_scanner import AgentScanner
from core.agent import FileScanResult, Vulnerability


FIXTURES_DIR = Path(__file__).parent / "fixtures"
MANIFEST_PATH = Path(__file__).parent / "expected_findings.json"

# ANSI colours
GREEN = "\033[92m"
RED = "\033[91m"
YELLOW = "\033[93m"
CYAN = "\033[96m"
BOLD = "\033[1m"
RESET = "\033[0m"


def detect_model_tier(model: Optional[str], manifest: dict) -> str:
    """
    Return 'advanced' if the model is an advanced-tier model, otherwise 'standard'.
    Standard-tier patterns are checked first so that 'gpt-4o-mini' is not
    accidentally matched by the 'gpt-4o' advanced pattern.
    """
    if not model:
        return "standard"
    model_lower = model.lower()
    tiers = manifest.get("model_tiers", {})
    # Standard wins if any standard pattern matches — prevents substring false-positives
    for pattern in tiers.get("standard", []):
        if pattern.lower() == model_lower:
            return "standard"
    for pattern in tiers.get("advanced", []):
        if pattern.lower() == model_lower:
            return "advanced"
    return "standard"


def _match_finding(vuln: Vulnerability, expected: dict) -> bool:
    """Return True if `vuln` matches an expected finding by keyword."""
    vtype = vuln.vulnerability_type.lower()
    desc = vuln.description.lower()
    combined = vtype + " " + desc
    return any(kw in combined for kw in expected["vulnerability_type_keywords"])


def eval_fixture(
    scanner: AgentScanner,
    fixture_path: Path,
    manifest: dict,
    threshold: float,
    model_tier: str = "standard",
) -> dict:
    """
    Scan a single fixture and compare against the manifest.
    Advanced-tier findings are only required when model_tier == 'advanced';
    otherwise they are treated as optional bonuses.
    Returns a result dict with pass/fail details.
    """
    filename = fixture_path.name
    fixture_manifest = manifest["fixtures"].get(filename)
    if not fixture_manifest:
        return {"file": filename, "skipped": True}

    all_required = fixture_manifest["required"]
    all_optional = fixture_manifest.get("optional", [])

    # Partition required findings by whether the current tier demands them
    if model_tier == "advanced":
        required = all_required
        optional = all_optional
        advanced_promoted = []  # nothing demoted in advanced mode
    else:
        required = [f for f in all_required if f.get("tier", "standard") == "standard"]
        # Advanced-tier required findings become optional bonuses on standard models
        advanced_promoted = [f for f in all_required if f.get("tier") == "advanced"]
        optional = all_optional + advanced_promoted

    # Capture structured results by monkey-patching _scan_single_file
    found_vulns: list[Vulnerability] = []
    original = scanner._scan_single_file

    def capturing_scan(file_path, display_name=""):
        nonlocal found_vulns
        import os as _os
        if not _os.path.isfile(file_path):
            return
        with open(file_path, "r", encoding="utf-8") as f:
            content = f.read()
        if not content.strip():
            return
        lines = content.splitlines()
        numbered = "\n".join(f"{i+1}: {l}" for i, l in enumerate(lines))
        try:
            result = scanner.agent.run_sync(f"File: {display_name}\n\n{numbered}")
            found_vulns.extend(result.data.vulnerabilities)
        except Exception as e:
            print(f"  {RED}Agent error:{RESET} {e}")

    scanner._scan_single_file = capturing_scan

    try:
        scanner._scan_single_file(str(fixture_path), display_name=filename)
    finally:
        scanner._scan_single_file = original

    # Match required findings
    matched_required = []
    missed_required = []
    for exp in required:
        if any(_match_finding(v, exp) for v in found_vulns):
            matched_required.append(exp)
        else:
            missed_required.append(exp)

    # Match optional findings
    matched_optional = [
        exp for exp in optional if any(_match_finding(v, exp) for v in found_vulns)
    ]

    total_required = len(required)
    score = len(matched_required) / total_required if total_required else 1.0
    passed = score >= threshold

    return {
        "file": filename,
        "skipped": False,
        "passed": passed,
        "score": score,
        "threshold": threshold,
        "required_total": total_required,
        "required_matched": len(matched_required),
        "matched_required": matched_required,
        "missed_required": missed_required,
        "optional_matched": matched_optional,
        "advanced_promoted": advanced_promoted,
        "total_vulnerabilities_found": len(found_vulns),
    }


def print_result(result: dict):
    if result.get("skipped"):
        print(f"  {YELLOW}SKIPPED{RESET} (not in manifest)")
        return

    status = f"{GREEN}PASS{RESET}" if result["passed"] else f"{RED}FAIL{RESET}"
    pct = f"{result['score']*100:.0f}%"
    print(
        f"  {status}  {pct} required findings detected "
        f"({result['required_matched']}/{result['required_total']})  "
        f"[threshold: {result['threshold']*100:.0f}%]"
    )

    if result["missed_required"]:
        print(f"  {RED}Missed required:{RESET}")
        for m in result["missed_required"]:
            print(f"    - [{m['severity']}] {m['note']}  (id: {m['id']})")

    if result["optional_matched"]:
        tier_note = ""
        print(f"  {GREEN}Bonus findings detected:{RESET}")
        for m in result["optional_matched"]:
            tier_label = f" {CYAN}[advanced]{RESET}" if m.get("tier") == "advanced" else ""
            print(f"    +{tier_label} {m['note']}  (id: {m['id']})")

    if result.get("advanced_promoted"):
        print(f"  {CYAN}Advanced-tier findings treated as optional (standard model):{RESET}")
        for m in result["advanced_promoted"]:
            print(f"    ~ [{m['severity']}] {m['note']}  (id: {m['id']})")

    print(f"  Total vulnerabilities returned by scanner: {result['total_vulnerabilities_found']}")


def main():
    parser = argparse.ArgumentParser(description="Run CodeScanAI evals")
    parser.add_argument("--provider", default="openai")
    parser.add_argument("--model", default=None)
    parser.add_argument("--host", default=None)
    parser.add_argument("--port", default=None, type=int)
    parser.add_argument("--token", default=None)
    parser.add_argument("--endpoint", default=None)
    parser.add_argument("--fixture", default=None, help="Run a single fixture by filename")
    cli_args = parser.parse_args()

    with open(MANIFEST_PATH) as f:
        manifest = json.load(f)

    threshold = manifest["threshold"]

    # Build a minimal args namespace that AgentScanner expects
    scanner_args = SimpleNamespace(
        provider=cli_args.provider,
        model=cli_args.model,
        host=cli_args.host,
        port=cli_args.port,
        token=cli_args.token,
        endpoint=cli_args.endpoint,
        directory=str(FIXTURES_DIR),
        changes_only=False,
        repo=None,
        pr_number=None,
        github_token=None,
    )

    model_tier = detect_model_tier(cli_args.model, manifest)
    tier_label = f"{CYAN}advanced{RESET}" if model_tier == "advanced" else f"{YELLOW}standard{RESET}"

    print(f"\n{BOLD}CodeScanAI Evals{RESET}")
    print(f"Provider: {cli_args.provider}  Model: {cli_args.model or 'default'}  Tier: {tier_label}")
    print(f"Threshold: {threshold*100:.0f}%  Fixtures: {FIXTURES_DIR}\n")

    scanner = AgentScanner(scanner_args)

    fixtures = sorted(FIXTURES_DIR.glob("*.py"))
    if cli_args.fixture:
        fixtures = [f for f in fixtures if f.name == cli_args.fixture]
        if not fixtures:
            print(f"{RED}No fixture named '{cli_args.fixture}' found.{RESET}")
            sys.exit(1)

    all_passed = True
    for fixture_path in fixtures:
        print(f"{BOLD}{fixture_path.name}{RESET}")
        result = eval_fixture(scanner, fixture_path, manifest, threshold, model_tier=model_tier)
        print_result(result)
        print()
        if not result.get("skipped") and not result["passed"]:
            all_passed = False

    if all_passed:
        print(f"{GREEN}{BOLD}All evals passed.{RESET}")
        sys.exit(0)
    else:
        print(f"{RED}{BOLD}One or more evals failed.{RESET}")
        sys.exit(1)


if __name__ == "__main__":
    main()
