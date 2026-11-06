#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

from .context import repo_root

MARKER_COMMENT = "<!-- codex-pr-preview -->"
PREVIEW_ROOT = Path(".github/pr-previews/.local")
PREVIEW_ID_PATTERN = re.compile(r"^[a-z0-9][a-z0-9-]*$")
PREVIEW_VARIANTS = {"targeted", "full-page"}


def preview_file_digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_preview_metadata(path: Path) -> dict:
    if path.is_symlink():
        raise ValueError("Preview metadata must not use symbolic links.")
    try:
        data = json.loads(path.read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def write_preview_metadata(path: Path, data: dict) -> None:
    if path.is_symlink():
        raise ValueError("Preview metadata must not use symbolic links.")
    temporary_path = None
    try:
        with tempfile.NamedTemporaryFile(
            encoding="utf-8", mode="w", dir=path.parent, prefix=f".{path.name}-", delete=False
        ) as temporary:
            temporary_path = Path(temporary.name)
            json.dump(data, temporary, indent=2)
            temporary.write("\n")
        temporary_path.replace(path)
    finally:
        if temporary_path:
            temporary_path.unlink(missing_ok=True)


def capture_source_snapshot() -> dict:
    head_sha = run_git(["rev-parse", "HEAD"]).stdout.strip()
    status = run_git(["status", "--porcelain=v1", "-z", "--untracked-files=all"]).stdout
    fingerprint = hashlib.sha256()
    for value in (
        status,
        run_git(
            [
                "diff",
                "--binary",
                "--raw",
                "--no-abbrev",
                "--patch",
                "--no-ext-diff",
                "--no-textconv",
                "--cached",
                "HEAD",
                "--",
            ]
        ).stdout,
        run_git(["diff", "--binary", "--no-ext-diff", "--no-textconv", "--"]).stdout,
    ):
        fingerprint.update(value.encode())
        fingerprint.update(b"\0")
    untracked = run_git(["ls-files", "--others", "--exclude-standard", "-z"]).stdout
    modified = run_git(["ls-files", "--modified", "--deleted", "-z"]).stdout
    for relative_path in sorted(set(filter(None, (untracked + modified).split("\0")))):
        path = repo_root() / relative_path
        fingerprint.update(relative_path.encode())
        fingerprint.update(b"\0")
        if not path.exists() and not path.is_symlink():
            fingerprint.update(b"deleted\0")
            continue
        fingerprint.update(str(path.lstat().st_mode).encode())
        fingerprint.update(b"\0")
        content = str(path.readlink()).encode() if path.is_symlink() else path.read_bytes()
        fingerprint.update(hashlib.sha256(content).digest())
    return {"head_sha": head_sha, "dirty": bool(status), "source_fingerprint": fingerprint.hexdigest()}


def record_preview_capture(preview_files: list[Path], source_snapshot: dict) -> None:
    if (
        not isinstance(source_snapshot, dict)
        or not isinstance(source_snapshot.get("head_sha"), str)
        or not source_snapshot["head_sha"]
        or not isinstance(source_snapshot.get("dirty"), bool)
        or not isinstance(source_snapshot.get("source_fingerprint"), str)
        or not re.fullmatch(r"[0-9a-f]{64}", source_snapshot["source_fingerprint"])
    ):
        raise ValueError("Capture requires a source snapshot taken before rendering.")
    if capture_source_snapshot() != source_snapshot:
        raise RuntimeError("Source changed during capture. Re-capture previews before recording provenance.")
    metadata_path = preview_files[0].parent / "captures.json"
    metadata = read_preview_metadata(metadata_path)
    for path in preview_files:
        metadata[path.relative_to(repo_root()).as_posix()] = {
            "sha256": preview_file_digest(path),
            **source_snapshot,
        }
    if capture_source_snapshot() != source_snapshot:
        raise RuntimeError("Source changed while hashing previews. Re-capture before recording provenance.")
    write_preview_metadata(metadata_path, metadata)


def load_capture_metadata(preview_files: list[Path], uploaded_digests: dict[str, str] | None = None) -> dict[str, dict]:
    metadata_path = preview_files[0].parent / "captures.json"
    metadata = read_preview_metadata(metadata_path)
    return {
        path.relative_to(repo_root()).as_posix(): record
        for path in preview_files
        if isinstance(record := metadata.get(relative_path := path.relative_to(repo_root()).as_posix()), dict)
        and isinstance(record.get("head_sha"), str)
        and record["head_sha"]
        and isinstance(record.get("dirty"), bool)
        and isinstance(record.get("source_fingerprint"), str)
        and re.fullmatch(r"[0-9a-f]{64}", record["source_fingerprint"])
        and record.get("sha256")
        == (uploaded_digests.get(relative_path) if uploaded_digests is not None else preview_file_digest(path))
    }


def run_git(args: list[str], *, check: bool = True) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=repo_root(),
        check=False,
        capture_output=True,
        text=True,
    )
    if check and result.returncode != 0:
        raise subprocess.CalledProcessError(result.returncode, ["git", *args], result.stdout, result.stderr)
    return result


def current_branch_name() -> str:
    result = run_git(["symbolic-ref", "--quiet", "--short", "HEAD"], check=False)
    branch_name = result.stdout.strip()
    if result.returncode != 0 or not branch_name:
        raise RuntimeError("Unable to determine the current branch name. Pass --branch explicitly.")
    return branch_name


def sanitize_branch_name(branch_name: str) -> str:
    sanitized = re.sub(r"[^A-Za-z0-9._-]+", "-", branch_name.strip())
    sanitized = re.sub(r"-{2,}", "-", sanitized).strip("-")
    if not sanitized or not any(char.isalnum() for char in sanitized):
        raise ValueError("Branch name must contain at least one alphanumeric character.")
    digest = hashlib.sha256(branch_name.encode()).hexdigest()[:16]
    return f"{sanitized[:63].lower()}-{digest}"


def validate_preview_id(preview_id: str) -> str:
    normalized = preview_id.strip().lower()
    if not PREVIEW_ID_PATTERN.fullmatch(normalized):
        raise ValueError("preview_id must match ^[a-z0-9][a-z0-9-]*$ and use lowercase letters, digits, or hyphens.")
    return normalized


def branch_preview_dir(branch_name: str | None = None) -> Path:
    resolved_branch = branch_name or current_branch_name()
    directory = repo_root() / PREVIEW_ROOT / sanitize_branch_name(resolved_branch)
    expected = repo_root().resolve() / PREVIEW_ROOT / sanitize_branch_name(resolved_branch)
    if directory.resolve() != expected:
        raise ValueError("Preview directories must not use symbolic links.")
    return directory


def validate_preview_state(state: str | None) -> str | None:
    if state is None:
        return None
    if state not in {"before", "after"}:
        raise ValueError("preview state must be 'before' or 'after'.")
    return state


def validate_preview_variant(variant: str | None) -> str:
    if variant is None:
        return "targeted"
    if variant not in PREVIEW_VARIANTS:
        raise ValueError("preview variant must be 'targeted' or 'full-page'.")
    return variant


def preview_output_path(
    preview_id: str, branch_name: str | None = None, state: str | None = None, variant: str | None = None
) -> Path:
    resolved_preview_id = validate_preview_id(preview_id)
    resolved_state = validate_preview_state(state)
    resolved_variant = validate_preview_variant(variant)
    suffixes = [resolved_preview_id]
    if resolved_state:
        suffixes.append(resolved_state)
    if resolved_variant == "full-page":
        suffixes.append(resolved_variant)
    path = branch_preview_dir(branch_name) / f"{'-'.join(suffixes)}.png"
    if path.resolve() != path.parent.resolve() / path.name:
        raise ValueError("Preview output files must not use symbolic links.")
    return path


def preview_output_relpath(
    preview_id: str, branch_name: str | None = None, state: str | None = None, variant: str | None = None
) -> str:
    return preview_output_path(preview_id, branch_name, state, variant).relative_to(repo_root()).as_posix()


def list_preview_files(branch_name: str | None = None) -> list[Path]:
    directory = branch_preview_dir(branch_name)
    if not directory.exists():
        return []
    return sorted(path for path in directory.glob("*.png") if path.is_file())


def clean_preview_dir(branch_name: str | None = None) -> Path:
    directory = branch_preview_dir(branch_name)
    if directory.exists():
        shutil.rmtree(directory)
    return directory


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Resolve and manage branch-scoped frontend PR preview paths.")
    subparsers = parser.add_subparsers(dest="command", required=True)

    path_parser = subparsers.add_parser("path", help="Print the repo-relative PNG path for a preview target.")
    path_parser.add_argument("preview_id")
    path_parser.add_argument("--branch")
    path_parser.add_argument("--state", choices=["before", "after"])
    path_parser.add_argument("--variant", choices=sorted(PREVIEW_VARIANTS), default="targeted")

    id_parser = subparsers.add_parser("id", help="Normalize and print a preview target id.")
    id_parser.add_argument("preview_id")

    dir_parser = subparsers.add_parser("dir", help="Print the repo-relative directory for the current branch.")
    dir_parser.add_argument("--branch")

    list_parser = subparsers.add_parser("list", help="List existing repo-relative PNG paths for the branch.")
    list_parser.add_argument("--branch")
    list_parser.add_argument("--json", action="store_true")

    clean_parser = subparsers.add_parser("clean", help="Remove the branch-scoped preview directory if it exists.")
    clean_parser.add_argument("--branch")

    subparsers.add_parser("snapshot", help="Print source provenance before rendering preview PNGs.")

    record_parser = subparsers.add_parser("record", help="Record the source revision for captured preview PNGs.")
    record_parser.add_argument("preview_id")
    record_parser.add_argument("--source-snapshot", type=json.loads, required=True)
    record_parser.add_argument("--branch")
    record_parser.add_argument("--state", choices=["before", "after"])

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        if args.command == "path":
            print(preview_output_relpath(args.preview_id, args.branch, args.state, args.variant))
            return 0

        if args.command == "id":
            print(validate_preview_id(args.preview_id))
            return 0

        if args.command == "dir":
            path = branch_preview_dir(args.branch).relative_to(repo_root()).as_posix()
            print(path)
            return 0

        if args.command == "list":
            items = [path.relative_to(repo_root()).as_posix() for path in list_preview_files(args.branch)]
            if args.json:
                print(json.dumps(items))
            else:
                for item in items:
                    print(item)
            return 0

        if args.command == "clean":
            path = clean_preview_dir(args.branch).relative_to(repo_root()).as_posix()
            print(path)
            return 0

        if args.command == "snapshot":
            print(json.dumps(capture_source_snapshot(), sort_keys=True))
            return 0

        if args.command == "record":
            record_preview_capture(
                [
                    preview_output_path(args.preview_id, args.branch, args.state, variant)
                    for variant in sorted(PREVIEW_VARIANTS)
                ],
                args.source_snapshot,
            )
            return 0
    except (OSError, RuntimeError, ValueError, subprocess.CalledProcessError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    parser.error(f"Unknown command: {args.command}")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
