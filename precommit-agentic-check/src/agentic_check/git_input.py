"""Collect staged git diff and nearby context for LLM checks."""

from __future__ import annotations

import re
import subprocess
from pathlib import Path
from typing import Any

HUNK_RE = re.compile(r"^@@ -\d+(?:,\d+)? \+(\d+)(?:,(\d+))? @@")


class GitInputError(RuntimeError):
    """Raised when git inspection fails."""


def _run_git(args: list[str], cwd: str | None = None) -> bytes:
    command = ["git", *args]
    completed = subprocess.run(
        command,
        cwd=cwd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=False,
    )
    if completed.returncode != 0:
        stderr = completed.stderr.decode("utf-8", errors="replace").strip()
        raise GitInputError(f"git command failed ({' '.join(command)}): {stderr}")
    return completed.stdout


def get_repo_root(cwd: str | None = None) -> str:
    out = _run_git(["rev-parse", "--show-toplevel"], cwd=cwd)
    return out.decode("utf-8", errors="replace").strip()


def get_staged_diff(context_lines: int, cwd: str) -> str:
    out = _run_git(
        ["diff", "--cached", f"--unified={context_lines}", "--no-color"],
        cwd=cwd,
    )
    return out.decode("utf-8", errors="replace")


def get_changed_files(cwd: str) -> list[str]:
    out = _run_git(["diff", "--cached", "--name-only", "--diff-filter=ACMR"], cwd=cwd)
    files = out.decode("utf-8", errors="replace").splitlines()
    return [item.strip() for item in files if item.strip()]


def get_staged_file_bytes(path: str, cwd: str) -> bytes:
    return _run_git(["show", f":{path}"], cwd=cwd)


def extract_hunk_ranges(diff_text: str) -> dict[str, list[tuple[int, int]]]:
    """Map each changed file to hunk ranges in the staged post-image."""
    current_file: str | None = None
    ranges: dict[str, list[tuple[int, int]]] = {}

    for line in diff_text.splitlines():
        if line.startswith("+++ b/"):
            current_file = line[len("+++ b/") :]
            if current_file not in ranges:
                ranges[current_file] = []
            continue

        if not current_file:
            continue

        match = HUNK_RE.match(line)
        if not match:
            continue

        start = int(match.group(1))
        count = int(match.group(2) or "1")
        if count == 0:
            continue

        end = start + count - 1
        ranges[current_file].append((start, end))

    return ranges


def _merge_ranges(ranges: list[tuple[int, int]]) -> list[tuple[int, int]]:
    if not ranges:
        return []

    sorted_ranges = sorted(ranges)
    merged = [sorted_ranges[0]]
    for start, end in sorted_ranges[1:]:
        prev_start, prev_end = merged[-1]
        if start <= prev_end + 1:
            merged[-1] = (prev_start, max(prev_end, end))
        else:
            merged.append((start, end))
    return merged


def _is_binary(raw: bytes) -> bool:
    return b"\x00" in raw


def _with_line_numbers(lines: list[str], start: int, end: int) -> str:
    numbered = [f"{index}: {lines[index - 1]}" for index in range(start, end + 1)]
    return "\n".join(numbered)


def build_nearby_context(
    changed_files: list[str],
    hunk_ranges: dict[str, list[tuple[int, int]]],
    context_lines: int,
    max_chars_per_file: int,
    cwd: str,
) -> list[dict[str, Any]]:
    contexts: list[dict[str, Any]] = []

    for path in changed_files:
        raw = get_staged_file_bytes(path, cwd=cwd)
        if _is_binary(raw):
            contexts.append(
                {
                    "path": path,
                    "is_binary": True,
                    "truncated": False,
                    "snippets": [],
                    "note": "binary file omitted",
                }
            )
            continue

        try:
            text = raw.decode("utf-8")
        except UnicodeDecodeError:
            contexts.append(
                {
                    "path": path,
                    "is_binary": True,
                    "truncated": False,
                    "snippets": [],
                    "note": "non-utf8 file omitted",
                }
            )
            continue

        lines = text.splitlines()
        if not lines:
            contexts.append(
                {
                    "path": path,
                    "is_binary": False,
                    "truncated": False,
                    "snippets": [],
                    "note": "empty file",
                }
            )
            continue

        ranges = hunk_ranges.get(path, [])
        if not ranges:
            ranges = [(1, min(len(lines), context_lines * 2))]

        expanded = [
            (max(1, start - context_lines), min(len(lines), end + context_lines))
            for start, end in ranges
        ]
        merged = _merge_ranges(expanded)

        remaining = max_chars_per_file
        snippets: list[dict[str, Any]] = []
        truncated = False

        for start, end in merged:
            if remaining <= 0:
                truncated = True
                break

            snippet_text = _with_line_numbers(lines, start, end)
            if len(snippet_text) > remaining:
                snippet_text = snippet_text[:remaining]
                truncated = True

            snippets.append(
                {
                    "start_line": start,
                    "end_line": end,
                    "content": snippet_text,
                }
            )
            remaining -= len(snippet_text)

        contexts.append(
            {
                "path": path,
                "is_binary": False,
                "truncated": truncated,
                "snippets": snippets,
            }
        )

    return contexts


def collect_staged_payload(
    context_lines: int,
    max_diff_chars: int,
    max_chars_per_file: int,
    cwd: str | None = None,
) -> dict[str, Any]:
    """Return staged diff and enriched context payload."""
    repo_root = get_repo_root(cwd=cwd)
    repo_root = str(Path(repo_root))

    diff = get_staged_diff(context_lines=context_lines, cwd=repo_root)
    if not diff.strip():
        return {
            "repo_root": repo_root,
            "changed_files": [],
            "diff": "",
            "diff_truncated": False,
            "file_context": [],
        }

    changed_files = get_changed_files(cwd=repo_root)
    hunk_ranges = extract_hunk_ranges(diff)

    diff_truncated = False
    if len(diff) > max_diff_chars:
        diff = diff[:max_diff_chars] + "\n...[diff truncated]"
        diff_truncated = True

    file_context = build_nearby_context(
        changed_files=changed_files,
        hunk_ranges=hunk_ranges,
        context_lines=context_lines,
        max_chars_per_file=max_chars_per_file,
        cwd=repo_root,
    )

    return {
        "repo_root": repo_root,
        "changed_files": changed_files,
        "diff": diff,
        "diff_truncated": diff_truncated,
        "file_context": file_context,
    }
