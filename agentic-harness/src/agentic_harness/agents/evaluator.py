"""Evaluator agent: reviews changes against the sprint contract."""

from __future__ import annotations

import json
from pathlib import Path

from ..config import HarnessConfig
from ..context import AgentRole, ContextAssembler
from ..schema import EVALUATION_CONTRACT, parse_evaluator_response
from ..tools.file_ops import LIST_DIRECTORY_TOOL, READ_FILE_TOOL
from ..tools.git_ops import GIT_DIFF_TOOL, GIT_STATUS_TOOL
from ..tools.shell import SHELL_TOOL
from .base import BaseAgent

DEFAULT_SYSTEM_PROMPT = """\
You are an Evaluator agent in a multi-agent development harness.

Your job is to review code changes produced by the Generator agent \
and grade them against the sprint contract. You are an independent \
reviewer — you did NOT write this code.

## Your responsibilities:
1. Read the specification and sprint contract
2. Review all changed files for correctness, completeness, and quality
3. Run tests and linting to verify the changes work
4. Grade each acceptance criterion as met or unmet
5. Produce a structured evaluation with a pass/fail verdict

## Rules:
- Be thorough but fair — focus on the sprint contract criteria
- Run tests to verify functionality, don't just read code
- Check for security issues (hardcoded secrets, SQL injection, etc.)
- Check for style compliance with project standards
- You CANNOT modify files — you can only read and run commands
- A "pass" verdict means ALL acceptance criteria are met
- A "fail" verdict requires specific, actionable findings

## Grading criteria:
- **Correctness**: Does the code do what the spec says?
- **Completeness**: Are all acceptance criteria met?
- **Style compliance**: Does it follow project conventions?
- **Test coverage**: Are tests written per the contract?
- **Security**: No secrets, no injection vulnerabilities?

## Output format:
Return a single JSON object matching this contract:
"""

# Evaluator can only run test/lint commands
EVALUATOR_SHELL_PREFIXES = [
    "poetry run pytest",
    "poetry run pre-commit",
    "pytest",
    "pre-commit",
    "pnpm test",
    "pnpm run lint",
    "npm test",
    "npm run lint",
    "just test",
    "pants test",
    "pants lint",
    "terraform validate",
    "terraform fmt",
    "python -m pytest",
    "make test",
    "make lint",
]


def load_evaluator_prompt(harness_root: Path | None = None) -> str:
    """Load the evaluator system prompt, using custom if available."""
    if harness_root:
        custom = harness_root / ".ai" / "prompts" / "evaluator.md"
        if custom.is_file():
            return custom.read_text(encoding="utf-8")
    return DEFAULT_SYSTEM_PROMPT + json.dumps(EVALUATION_CONTRACT, indent=2)


def run_evaluator(
    *,
    spec: dict,
    config: HarnessConfig,
    project_path: str,
    root_path: str | None = None,
    harness_root: Path | None = None,
) -> dict:
    """Run the Evaluator agent. Returns the validated evaluation."""
    assembler = ContextAssembler(project_path, root_path)
    context = assembler.assemble(AgentRole.EVALUATOR)

    system_prompt = load_evaluator_prompt(harness_root)

    tools = [
        READ_FILE_TOOL,
        LIST_DIRECTORY_TOOL,
        SHELL_TOOL,
        GIT_DIFF_TOOL,
        GIT_STATUS_TOOL,
    ]
    # NOTE: No WRITE_FILE_TOOL — evaluator is read-only

    agent = BaseAgent(
        role=AgentRole.EVALUATOR,
        provider=config.provider,
        model=config.models.evaluator,
        system_prompt=system_prompt,
        tools=tools,
        project_root=project_path,
        context=context,
        timeout_seconds=config.timeout_seconds,
        allowed_shell_prefixes=EVALUATOR_SHELL_PREFIXES,
    )

    prompt = (
        "## Specification & Sprint Contract\n\n"
        f"{json.dumps(spec, indent=2)}\n\n"
        "## Instructions\n\n"
        "Review the current state of the codebase against the specification "
        "and sprint contract above. Use git_diff to see what changed, read "
        "the modified files, and run tests. Then produce your evaluation."
    )

    raw_response = agent.run(prompt)
    return parse_evaluator_response(raw_response)
