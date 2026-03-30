"""Planner agent: expands a task brief into a detailed spec."""

from __future__ import annotations

import json
from pathlib import Path

from ..config import HarnessConfig
from ..context import AgentRole, ContextAssembler
from ..schema import SPEC_CONTRACT, parse_planner_response
from ..tools.file_ops import LIST_DIRECTORY_TOOL, READ_FILE_TOOL
from .base import BaseAgent

DEFAULT_SYSTEM_PROMPT = """\
You are a Planner agent in a multi-agent development harness.

Your job is to take a brief task description and produce a detailed \
implementation specification that a separate Generator agent will use \
to write code.

## Your responsibilities:
1. Analyze the task brief and project context
2. Explore the codebase to understand what exists
3. Produce a structured spec with:
   - Clear title and description
   - List of files to modify and create
   - Implementation approach
   - A sprint contract (definition of done) with acceptance criteria, \
test requirements, security checklist, and style requirements
4. Identify what is OUT OF SCOPE to prevent scope creep

## Rules:
- Be specific about file paths and function signatures
- Keep the approach high-level; avoid writing actual code
- Focus on WHAT to build, not HOW to implement every line
- The sprint contract is critical — the Evaluator agent will grade \
against it

## Output format:
Return a single JSON object matching this contract:
"""


def load_planner_prompt(harness_root: Path | None = None) -> str:
    """Load the planner system prompt, using custom if available."""
    if harness_root:
        custom = harness_root / ".ai" / "prompts" / "planner.md"
        if custom.is_file():
            return custom.read_text(encoding="utf-8")
    return DEFAULT_SYSTEM_PROMPT + json.dumps(SPEC_CONTRACT, indent=2)


def run_planner(
    *,
    brief: str,
    config: HarnessConfig,
    project_path: str,
    root_path: str | None = None,
    harness_root: Path | None = None,
) -> dict:
    """Run the Planner agent and return the validated spec."""
    assembler = ContextAssembler(project_path, root_path)
    context = assembler.assemble(AgentRole.PLANNER)

    system_prompt = load_planner_prompt(harness_root)

    tools = [READ_FILE_TOOL, LIST_DIRECTORY_TOOL]

    agent = BaseAgent(
        role=AgentRole.PLANNER,
        provider=config.provider,
        model=config.models.planner,
        system_prompt=system_prompt,
        tools=tools,
        project_root=project_path,
        context=context,
        timeout_seconds=config.timeout_seconds,
    )

    raw_response = agent.run(f"Task Brief:\n\n{brief}")
    return parse_planner_response(raw_response)
