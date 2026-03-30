"""Shell command execution tool for agents."""

from __future__ import annotations

import subprocess
from typing import Any

DEFAULT_TIMEOUT = 120


def run_command(
    command: str,
    cwd: str,
    timeout: int = DEFAULT_TIMEOUT,
    allowed_prefixes: list[str] | None = None,
) -> dict[str, Any]:
    """Run a shell command and return stdout/stderr/returncode.

    If ``allowed_prefixes`` is set, the command must start with one of
    the listed prefixes (used to restrict the evaluator to test/lint only).
    """
    if allowed_prefixes:
        if not any(command.strip().startswith(p) for p in allowed_prefixes):
            return {
                "error": f"command not allowed. Must start with one of: {allowed_prefixes}",
                "returncode": -1,
            }

    try:
        result = subprocess.run(
            command,
            shell=True,
            cwd=cwd,
            capture_output=True,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired:
        return {
            "error": f"command timed out after {timeout}s",
            "returncode": -1,
        }
    except OSError as exc:
        return {
            "error": f"cannot execute command: {exc}",
            "returncode": -1,
        }

    stdout = result.stdout
    stderr = result.stderr

    # Truncate very long output
    max_chars = 50_000
    if len(stdout) > max_chars:
        stdout = stdout[:max_chars] + "\n... (truncated)"
    if len(stderr) > max_chars:
        stderr = stderr[:max_chars] + "\n... (truncated)"

    return {
        "stdout": stdout,
        "stderr": stderr,
        "returncode": result.returncode,
    }


# --- Tool definition for Anthropic API ---

SHELL_TOOL = {
    "name": "run_command",
    "description": (
        "Run a shell command in the project directory. "
        "Use for running tests, linting, building, or inspecting the project."
    ),
    "input_schema": {
        "type": "object",
        "properties": {
            "command": {
                "type": "string",
                "description": "The shell command to execute.",
            },
            "timeout": {
                "type": "integer",
                "description": "Timeout in seconds. Default 120.",
                "default": DEFAULT_TIMEOUT,
            },
        },
        "required": ["command"],
    },
}
