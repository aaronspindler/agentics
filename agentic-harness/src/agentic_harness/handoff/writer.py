"""Write structured handoff files to the workspace."""

from __future__ import annotations

import json
from pathlib import Path
from typing import Any


def write_handoff(workspace: Path, filename: str, data: Any) -> Path:
    """Write a JSON handoff file to the workspace directory."""
    workspace.mkdir(parents=True, exist_ok=True)
    path = workspace / filename
    path.write_text(json.dumps(data, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def write_iteration_handoff(
    workspace: Path, iteration: int, filename: str, data: Any
) -> Path:
    """Write a handoff file into an iteration subdirectory."""
    iter_dir = workspace / f"iteration-{iteration:03d}"
    return write_handoff(iter_dir, filename, data)


def write_brief(workspace: Path, brief: str) -> Path:
    """Copy the task brief into the workspace."""
    workspace.mkdir(parents=True, exist_ok=True)
    path = workspace / "brief.md"
    path.write_text(brief, encoding="utf-8")
    return path


def append_log(workspace: Path, entry: str) -> None:
    """Append a line to the workspace log."""
    workspace.mkdir(parents=True, exist_ok=True)
    log_path = workspace / "harness.log"
    with open(log_path, "a", encoding="utf-8") as f:
        f.write(entry + "\n")
