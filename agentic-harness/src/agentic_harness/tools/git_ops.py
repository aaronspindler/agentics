"""Git operation tools for agents."""

from __future__ import annotations

import subprocess
from typing import Any


def _git(args: list[str], cwd: str, timeout: int = 30) -> dict[str, Any]:
    """Run a git command and return the result."""
    try:
        result = subprocess.run(
            ["git"] + args,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except FileNotFoundError:
        return {"error": "git is not installed", "returncode": -1}
    except subprocess.TimeoutExpired:
        return {"error": f"git command timed out after {timeout}s", "returncode": -1}

    return {
        "stdout": result.stdout,
        "stderr": result.stderr,
        "returncode": result.returncode,
    }


def git_diff(cwd: str, staged: bool = False) -> dict[str, Any]:
    """Show git diff (staged or unstaged)."""
    args = ["diff"]
    if staged:
        args.append("--cached")
    return _git(args, cwd)


def git_status(cwd: str) -> dict[str, Any]:
    """Show git status (short format)."""
    return _git(["status", "--short"], cwd)


def git_commit(cwd: str, message: str, files: list[str] | None = None) -> dict[str, Any]:
    """Stage files and commit."""
    if files:
        add_result = _git(["add"] + files, cwd)
        if add_result.get("returncode", -1) != 0:
            return add_result
    return _git(["commit", "-m", message], cwd)


# --- Tool definitions for Anthropic API ---

GIT_DIFF_TOOL = {
    "name": "git_diff",
    "description": "Show git diff of changes in the project. Use staged=true for staged changes only.",
    "input_schema": {
        "type": "object",
        "properties": {
            "staged": {
                "type": "boolean",
                "description": "If true, show only staged changes.",
                "default": False,
            },
        },
        "required": [],
    },
}

GIT_STATUS_TOOL = {
    "name": "git_status",
    "description": "Show git status (short format) of the project.",
    "input_schema": {
        "type": "object",
        "properties": {},
        "required": [],
    },
}

GIT_COMMIT_TOOL = {
    "name": "git_commit",
    "description": "Stage specified files and create a git commit.",
    "input_schema": {
        "type": "object",
        "properties": {
            "message": {
                "type": "string",
                "description": "Commit message.",
            },
            "files": {
                "type": "array",
                "items": {"type": "string"},
                "description": "List of file paths to stage before committing.",
            },
        },
        "required": ["message"],
    },
}
