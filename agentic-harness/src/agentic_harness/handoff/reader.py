"""Read structured handoff files from the workspace."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def read_handoff(workspace: Path, filename: str) -> Any | None:
    """Read a JSON handoff file from the workspace. Returns None if missing."""
    path = workspace / filename
    if not path.is_file():
        return None
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (json.JSONDecodeError, OSError):
        return None


def read_iteration_handoff(
    workspace: Path, iteration: int, filename: str
) -> Any | None:
    """Read a handoff file from an iteration subdirectory."""
    iter_dir = workspace / f"iteration-{iteration:03d}"
    return read_handoff(iter_dir, filename)


def read_brief(workspace: Path) -> str | None:
    """Read the task brief from the workspace."""
    path = workspace / "brief.md"
    if not path.is_file():
        return None
    try:
        return path.read_text(encoding="utf-8")
    except OSError:
        return None


def get_latest_iteration(workspace: Path) -> int:
    """Find the highest iteration number in the workspace."""
    max_iter = 0
    for entry in workspace.iterdir():
        if entry.is_dir() and entry.name.startswith("iteration-"):
            try:
                num = int(entry.name.split("-")[1])
                max_iter = max(max_iter, num)
            except (ValueError, IndexError):
                pass
    return max_iter
