"""Resolve tool operations against the caller's selected Git repository."""

from __future__ import annotations

import subprocess
from pathlib import Path

_selected_repo_root: Path | None = None


def _git_root(directory: Path) -> Path:
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=directory,
            capture_output=True,
            text=True,
            check=False,
        )
    except OSError as exc:
        raise RuntimeError(f"Unable to inspect Git repository at {directory}: {exc}") from exc
    if result.returncode != 0 or not result.stdout.strip():
        raise RuntimeError(f"No Git repository found at {directory}. Use --repo-root to select one.")
    return Path(result.stdout.strip()).resolve()


def set_repo_root(path: str | Path | None) -> None:
    """Select a Git repository, or reset to discovery from the current directory."""
    global _selected_repo_root
    if path is None:
        _selected_repo_root = None
        return
    directory = Path(path).expanduser().resolve()
    if not directory.is_dir():
        raise ValueError(f"Repository directory does not exist: {directory}")
    _selected_repo_root = _git_root(directory)


def repo_root() -> Path:
    """Return the selected root, otherwise discover the caller's Git repository."""
    return _selected_repo_root if _selected_repo_root is not None else _git_root(Path.cwd())


def has_explicit_repo_root() -> bool:
    """Whether the caller selected a repository rather than using ambient context."""
    return _selected_repo_root is not None
