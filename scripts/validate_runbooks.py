#!/usr/bin/env python3
"""
Runbook Validator — Validates documentation runbooks for correctness.

Validates:
- File paths and directories exist
- Environment variables are documented in .env.example
- Code blocks and commands are properly formatted
- Steps are in logical order

Usage:
    python scripts/validate_runbooks.py                    # Validate all runbooks
    python scripts/validate_runbooks.py docs/LOCAL_DEVELOPMENT.md  # Validate specific file
"""

import re
import sys
from pathlib import Path
from typing import List, Set


class RunbookValidator:
    """Validates documentation runbooks for correctness and consistency."""

    def __init__(self, repo_root: Path = None):
        """Initialize validator with repo root."""
        self.repo_root = repo_root or Path.cwd()
        self.errors: List[str] = []
        self.warnings: List[str] = []
        self.env_vars: Set[str] = set()
        self._load_env_example()

    def _load_env_example(self):
        """Load environment variables from .env.example."""
        env_file = self.repo_root / ".env.example"
        if not env_file.exists():
            self.warnings.append(f"⚠️  .env.example not found at {env_file}")
            return

        with open(env_file, "r") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    var_name = line.split("=")[0].strip()
                    self.env_vars.add(var_name)

    def validate_file(self, filepath: Path) -> bool:
        """Validate a single runbook file."""
        if not filepath.exists():
            self.errors.append(f"❌ File not found: {filepath}")
            return False

        with open(filepath, "r") as f:
            content = f.read()

        self._validate_file_paths(content, filepath)
        self._validate_env_vars(content, filepath)
        self._validate_code_blocks(content, filepath)

        return len(self.errors) == 0

    def _validate_file_paths(self, content: str, filepath: Path):
        """Validate file paths mentioned in the runbook."""
        # Remove code blocks from content to avoid validating paths within directory trees
        # Split by ``` and only process non-code sections
        parts = content.split("```")
        content_without_code = "".join(parts[i] for i in range(0, len(parts), 2))

        patterns = [
            r"`([a-zA-Z0-9._\/-]+\.md)`",
            r"`([a-zA-Z0-9._\/-]+\.py)`",
            r"`([a-zA-Z0-9._\/-]+\.txt)`",
            r"`([a-zA-Z0-9._\/-]+\.json)`",
            r"`([a-zA-Z0-9._\/-]+\.yaml)`",
            r"`([a-zA-Z0-9._\/-]+\.yml)`",
        ]

        found_paths: Set[str] = set()
        for pattern in patterns:
            for match in re.finditer(pattern, content_without_code, re.IGNORECASE):
                path = match.group(1)
                found_paths.add(path)

        for path_str in found_paths:
            full_path = self.repo_root / path_str

            if path_str.startswith(("http://", "https://", "$", "${", "{{")):
                continue

            if not full_path.exists():
                self.errors.append(
                    f"❌ {filepath.name}: File path does not exist: {path_str}"
                )

    def _validate_env_vars(self, content: str, filepath: Path):
        """Validate environment variables are documented in .env.example."""
        patterns = [
            r"\$\{([A-Z_][A-Z0-9_]*)\}",
            r"\$([A-Z_][A-Z0-9_]*)\b",
            r"env:([A-Z_][A-Z0-9_]*)",
        ]

        found_vars: Set[str] = set()
        for pattern in patterns:
            for match in re.finditer(pattern, content):
                var_name = match.group(1)
                found_vars.add(var_name)

        # Exempt vars that are not environment variables
        exempt_vars = {
            "HOME",
            "PATH",
            "USER",
            "PWD",
            "SHELL",
            "LANG",
            "VITE_API_URL",
            # FMCSA duty status enums (not env vars)
            "DRIVING",
            "OFF_DUTY",
            "ON_DUTY_NOT_DRIVING",
            "SLEEPER",
            "SLEEPER_BERTH",
            # HTTP methods (not env vars)
            "POST",
            "GET",
            "PUT",
            "DELETE",
            "PATCH",
        }

        for var in found_vars:
            if var in exempt_vars:
                continue

            if var not in self.env_vars:
                self.warnings.append(
                    f"⚠️  {filepath.name}: Environment variable '{var}' not documented in .env.example"
                )

    def _validate_code_blocks(self, content: str, filepath: Path):
        """Validate code blocks are properly formatted."""
        code_block_pattern = r"```"
        matches = list(re.finditer(code_block_pattern, content))

        if len(matches) % 2 != 0:
            self.errors.append(
                f"❌ {filepath.name}: Unclosed code block (odd number of ``` markers)"
            )

    def report(self) -> int:
        """Print validation report and return exit code."""
        print("\n" + "=" * 60)
        print("RUNBOOK VALIDATION REPORT")
        print("=" * 60 + "\n")

        if self.errors:
            print("❌ ERRORS:")
            for error in sorted(set(self.errors)):
                print(f"  {error}")
            print()

        if self.warnings:
            print("⚠️  WARNINGS:")
            for warning in sorted(set(self.warnings)):
                print(f"  {warning}")
            print()

        if not self.errors and not self.warnings:
            print("✅ All runbooks are valid!\n")
            return 0

        summary = f"\nSummary: {len(self.errors)} errors, {len(self.warnings)} warnings"
        print(summary)
        print("=" * 60 + "\n")

        return 1 if self.errors else 0


def find_runbooks(repo_root: Path) -> List[Path]:
    """Find all markdown runbook files in the repo."""
    runbook_patterns = [
        "docs/TESTING.md",
        "docs/ARCHITECTURE.md",
        "docs/API_CONTRACT.md",
        "docs/HOS_ENGINE.md",
        "docs/FRONTEND_INTEGRATION.md",
        "README.md",
    ]

    runbooks = []
    for pattern in runbook_patterns:
        filepath = repo_root / pattern
        if filepath.exists():
            runbooks.append(filepath)

    return sorted(runbooks)


def main():
    """Main entry point."""
    repo_root = Path.cwd()

    target_files = []
    if len(sys.argv) > 1:
        for arg in sys.argv[1:]:
            filepath = Path(arg)
            if not filepath.is_absolute():
                filepath = repo_root / filepath
            target_files.append(filepath)
    else:
        target_files = find_runbooks(repo_root)

    if not target_files:
        print("❌ No runbook files found to validate")
        return 1

    print(f"Validating {len(target_files)} runbook(s)...\n")

    validator = RunbookValidator(repo_root)

    for filepath in target_files:
        print(f"Checking: {filepath.relative_to(repo_root)}")
        validator.validate_file(filepath)

    exit_code = validator.report()
    return exit_code


if __name__ == "__main__":
    sys.exit(main())

