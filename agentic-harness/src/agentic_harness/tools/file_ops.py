"""File operation tools for agents."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

MAX_READ_LINES = 2000


def read_file(path: str, project_root: str, max_lines: int = MAX_READ_LINES) -> dict[str, Any]:
    """Read a file and return its contents."""
    resolved = _resolve_path(path, project_root)
    if not resolved.is_file():
        return {"error": f"file not found: {path}"}

    try:
        text = resolved.read_text(encoding="utf-8", errors="replace")
    except OSError as exc:
        return {"error": f"cannot read file: {exc}"}

    lines = text.splitlines()
    truncated = len(lines) > max_lines
    if truncated:
        lines = lines[:max_lines]

    return {
        "path": str(resolved),
        "content": "\n".join(lines),
        "total_lines": len(text.splitlines()),
        "truncated": truncated,
    }


def write_file(path: str, content: str, project_root: str) -> dict[str, Any]:
    """Write content to a file. Creates parent directories as needed."""
    resolved = _resolve_path(path, project_root)

    if _is_protected(resolved):
        return {"error": f"protected file, cannot write: {path}"}

    try:
        resolved.parent.mkdir(parents=True, exist_ok=True)
        resolved.write_text(content, encoding="utf-8")
    except OSError as exc:
        return {"error": f"cannot write file: {exc}"}

    return {
        "path": str(resolved),
        "bytes_written": len(content.encode("utf-8")),
    }


def list_directory(
    path: str, project_root: str, pattern: str = "*", max_entries: int = 200
) -> dict[str, Any]:
    """List files in a directory, optionally matching a glob pattern."""
    resolved = _resolve_path(path, project_root)
    if not resolved.is_dir():
        return {"error": f"not a directory: {path}"}

    try:
        entries = sorted(resolved.glob(pattern))[:max_entries]
    except OSError as exc:
        return {"error": f"cannot list directory: {exc}"}

    files: list[str] = []
    dirs: list[str] = []
    for entry in entries:
        rel = str(entry.relative_to(resolved))
        if entry.is_dir():
            dirs.append(rel + "/")
        else:
            files.append(rel)

    return {
        "path": str(resolved),
        "files": files,
        "directories": dirs,
        "total": len(files) + len(dirs),
    }


def _resolve_path(path: str, project_root: str) -> Path:
    """Resolve a path relative to the project root."""
    p = Path(path)
    if p.is_absolute():
        return p
    return Path(project_root) / p


PROTECTED_PATTERNS = {".env", ".pem", ".key", "credentials"}


def _is_protected(path: Path) -> bool:
    """Check if a file matches protected patterns."""
    name = path.name.lower()
    suffix = path.suffix.lower()
    if suffix in {".pem", ".key"}:
        return True
    if name == ".env" or name.startswith(".env."):
        return True
    if "credentials" in name or "secret" in name:
        return True
    return False


# --- Tool definitions for Anthropic API ---

READ_FILE_TOOL = {
    "name": "read_file",
    "description": "Read the contents of a file. Returns the text content and line count.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path relative to project root, or absolute path.",
            },
            "max_lines": {
                "type": "integer",
                "description": "Maximum lines to read. Default 2000.",
                "default": MAX_READ_LINES,
            },
        },
        "required": ["path"],
    },
}

WRITE_FILE_TOOL = {
    "name": "write_file",
    "description": "Write content to a file. Creates parent directories as needed. Cannot write to protected files (.env, .pem, .key, credentials).",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "File path relative to project root, or absolute path.",
            },
            "content": {
                "type": "string",
                "description": "The full content to write to the file.",
            },
        },
        "required": ["path", "content"],
    },
}

LIST_DIRECTORY_TOOL = {
    "name": "list_directory",
    "description": "List files and directories. Supports glob patterns.",
    "input_schema": {
        "type": "object",
        "properties": {
            "path": {
                "type": "string",
                "description": "Directory path relative to project root, or absolute path.",
            },
            "pattern": {
                "type": "string",
                "description": "Glob pattern to filter entries. Default '*'.",
                "default": "*",
            },
        },
        "required": ["path"],
    },
}
