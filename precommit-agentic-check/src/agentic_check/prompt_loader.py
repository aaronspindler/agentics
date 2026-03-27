"""Prompt loading utilities."""

from __future__ import annotations

from pathlib import Path


class PromptError(RuntimeError):
    """Raised when prompt loading fails."""


def load_prompt(prompt_file: str, cwd: str | None = None) -> str:
    """Load a prompt file, resolving relative paths from the provided cwd."""
    base = Path(cwd) if cwd else Path.cwd()
    path = Path(prompt_file)
    if not path.is_absolute():
        path = base / path

    if not path.exists():
        raise PromptError(f"prompt file not found: {path}")
    if not path.is_file():
        raise PromptError(f"prompt path is not a file: {path}")

    text = path.read_text(encoding="utf-8")
    if not text.strip():
        raise PromptError(f"prompt file is empty: {path}")
    return text
