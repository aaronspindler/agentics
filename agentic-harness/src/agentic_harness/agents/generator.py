"""Generator agent: implements code changes based on a spec."""

from __future__ import annotations

import json
from pathlib import Path

from ..config import HarnessConfig
from ..context import AgentRole, ContextAssembler
from ..tools.file_ops import LIST_DIRECTORY_TOOL, READ_FILE_TOOL, WRITE_FILE_TOOL
from ..tools.git_ops import GIT_COMMIT_TOOL, GIT_DIFF_TOOL, GIT_STATUS_TOOL
from ..tools.shell import SHELL_TOOL
from .base import BaseAgent

DEFAULT_SYSTEM_PROMPT = """\
You are a Generator agent in a multi-agent development harness.

Your job is to implement code changes according to a specification \
produced by the Planner agent. A separate Evaluator agent will review \
your work, so focus on correctness and completeness.

## Your responsibilities:
1. Read the spec carefully — it defines what to build
2. Read existing code to understand the codebase
3. Write code changes (modify existing files, create new files)
4. Run tests and linting to verify your changes
5. Fix any issues found by tests or linting

## Rules:
- Follow the project's coding style and patterns (see project docs)
- Write tests as specified in the sprint contract
- Do NOT modify files outside the scope defined in the spec
- Do NOT commit secrets, API keys, or PHI
- Run tests after making changes to verify correctness
- If tests fail, fix the code — don't skip tests

## Sprint contract:
The Evaluator will grade your work against the sprint contract below. \
Every acceptance criterion and test requirement must be met for a \
passing grade.

## Output:
After completing all changes, respond with a brief summary of what \
you did and which files were modified. Include any issues you \
encountered.
"""


def load_generator_prompt(harness_root: Path | None = None) -> str:
    """Load the generator system prompt, using custom if available."""
    if harness_root:
        custom = harness_root / ".ai" / "prompts" / "generator.md"
        if custom.is_file():
            return custom.read_text(encoding="utf-8")
    return DEFAULT_SYSTEM_PROMPT


def run_generator(
    *,
    spec: dict,
    feedback: dict | None,
    config: HarnessConfig,
    project_path: str,
    root_path: str | None = None,
    harness_root: Path | None = None,
) -> str:
    """Run the Generator agent. Returns the agent's text summary."""
    assembler = ContextAssembler(project_path, root_path)
    context = assembler.assemble(AgentRole.GENERATOR)

    system_prompt = load_generator_prompt(harness_root)

    tools = [
        READ_FILE_TOOL,
        WRITE_FILE_TOOL,
        LIST_DIRECTORY_TOOL,
        SHELL_TOOL,
        GIT_DIFF_TOOL,
        GIT_STATUS_TOOL,
    ]

    if config.auto_commit:
        tools.append(GIT_COMMIT_TOOL)

    agent = BaseAgent(
        role=AgentRole.GENERATOR,
        provider=config.provider,
        model=config.models.generator,
        system_prompt=system_prompt,
        tools=tools,
        project_root=project_path,
        context=context,
        timeout_seconds=config.timeout_seconds,
        auto_commit=config.auto_commit,
    )

    # Build the user prompt with spec and optional feedback
    prompt_parts = [
        "## Specification\n",
        json.dumps(spec, indent=2),
    ]

    if feedback:
        prompt_parts.append("\n\n## Evaluator Feedback (from previous iteration)\n")
        prompt_parts.append(
            "Fix the issues below. The Evaluator found these problems "
            "with the previous implementation:\n"
        )
        prompt_parts.append(json.dumps(feedback, indent=2))

    return agent.run("\n".join(prompt_parts))
