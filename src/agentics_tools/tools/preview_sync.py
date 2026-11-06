#!/usr/bin/env python3
from __future__ import annotations

import argparse
import hashlib
import json
import os
import re
import stat
import subprocess
import sys
import tempfile
from pathlib import Path
from urllib.parse import urlencode, urlsplit

from .context import has_explicit_repo_root, repo_root
from .preview import (
    MARKER_COMMENT,
    current_branch_name,
    list_preview_files,
    load_capture_metadata,
    read_preview_metadata,
    write_preview_metadata,
)

MINIMUM_GH_VERSION = (2, 99, 0)
MAX_IMAGE_BYTES = 10 * 1024 * 1024


def run(args: list[str], *, input_text: str | None = None) -> str:
    environment = None
    if has_explicit_repo_root():
        environment = dict(os.environ)
        environment.pop("GH_REPO", None)
    result = subprocess.run(
        args,
        cwd=repo_root(),
        input=input_text,
        check=False,
        capture_output=True,
        text=True,
        env=environment,
    )
    if result.returncode != 0:
        details = result.stderr.strip() or result.stdout.strip() or f"exit code {result.returncode}"
        raise RuntimeError(f"{' '.join(args)} failed: {details}")
    return result.stdout.strip()


def gh_json(args: list[str], *, input_text: str | None = None):
    host_args = ["--hostname", "github.com"] if args[0] == "api" else []
    stdout = run(["gh", *args, *host_args], input_text=input_text)
    return json.loads(stdout) if stdout else None


def require_attachment_support() -> None:
    match = re.search(r"gh version (\d+)\.(\d+)\.(\d+)", run(["gh", "--version"]))
    if not match or tuple(map(int, match.groups())) < MINIMUM_GH_VERSION:
        raise RuntimeError("Native PR attachments require gh 2.99.0 or newer. Upgrade GitHub CLI first.")


def infer_repo() -> str:
    repository = gh_json(["repo", "view", "--json", "nameWithOwner,url"])
    if urlsplit(repository["url"]).hostname != "github.com":
        raise RuntimeError("Native PR preview publication supports GitHub.com repositories only.")
    return repository["nameWithOwner"]


def infer_pr_number(repo: str, branch_name: str | None = None) -> int:
    branch = branch_name or current_branch_name()
    return int(run(["gh", "pr", "view", branch, "--repo", f"github.com/{repo}", "--json", "number", "--jq", ".number"]))


def current_head_sha() -> str:
    return run(["git", "rev-parse", "HEAD"])


def validate_preview_files(preview_files: list[Path]) -> None:
    for path in preview_files:
        try:
            info = path.lstat()
        except OSError as exc:
            raise RuntimeError(f"{path}: cannot read preview PNG.") from exc
        if not stat.S_ISREG(info.st_mode) or path.suffix != ".png":
            raise RuntimeError(f"{path}: previews must be regular PNG files.")
        if not info.st_size:
            raise RuntimeError(f"{path}: preview PNG is empty.")
        if info.st_size > MAX_IMAGE_BYTES:
            raise RuntimeError(f"{path}: GitHub image attachments must be at most 10 MiB.")
        with path.open("rb") as image:
            if image.read(8) != b"\x89PNG\r\n\x1a\n":
                raise RuntimeError(f"{path}: preview is not a PNG image.")
        if path.resolve() != repo_root().resolve() / path.relative_to(repo_root()):
            raise ValueError("Preview files must not use symbolic links.")


def attachment_url(value: str) -> str:
    if not isinstance(value, str):
        raise RuntimeError("GitHub did not return a permanent native attachment URL.")
    parsed = urlsplit(value)
    if (
        parsed.scheme != "https"
        or parsed.netloc != "github.com"
        or not parsed.path.startswith("/user-attachments/assets/")
        or not parsed.path.removeprefix("/user-attachments/assets/")
        or parsed.query
        or parsed.fragment
    ):
        raise RuntimeError("GitHub did not return a permanent native attachment URL.")
    return value


def upload_preview_files(
    repo: str, repository_id: int, preview_files: list[Path]
) -> tuple[dict[str, str], dict[str, str]]:
    validate_preview_files(preview_files)
    cache_path = preview_files[0].parent / "attachments.json"
    cache = read_preview_metadata(cache_path)
    files = cache.get("files", {}) if cache.get("repo") == repo and cache.get("repository_id") == repository_id else {}
    if not isinstance(files, dict):
        files = {}
    attachments = {}
    uploaded_digests = {}
    for path in preview_files:
        relative_path = path.relative_to(repo_root()).as_posix()
        content = path.read_bytes()
        if not content.startswith(b"\x89PNG\r\n\x1a\n") or len(content) > MAX_IMAGE_BYTES:
            raise RuntimeError(f"{path}: PNG changed during upload preparation. Re-capture and retry.")
        digest = hashlib.sha256(content).hexdigest()
        uploaded_digests[relative_path] = digest
        cached = files.get(relative_path, {})
        if isinstance(cached, dict) and cached.get("sha256") == digest:
            try:
                url = attachment_url(cached.get("url", ""))
            except RuntimeError:
                pass
            else:
                attachments[relative_path] = url
                continue

        # Use the same native endpoint as gh --attach, preserving the marker comment's ID.
        query = urlencode({"name": path.name, "content_type": "image/png", "repository_id": repository_id})
        with tempfile.NamedTemporaryFile(dir=path.parent, suffix=".bin") as snapshot:
            snapshot.write(content)
            snapshot.flush()
            uploaded = (
                gh_json(
                    [
                        "api",
                        f"https://uploads.github.com/user-attachments/assets?{query}",
                        "--method",
                        "POST",
                        "--header",
                        "Content-Type: application/octet-stream",
                        "--header",
                        "Accept: application/vnd.github+json",
                        "--input",
                        snapshot.name,
                    ]
                )
                or {}
            )
        url = attachment_url(uploaded.get("url", ""))
        files[relative_path] = {"sha256": digest, "url": url}
        write_preview_metadata(cache_path, {"repo": repo, "repository_id": repository_id, "files": files})
        attachments[relative_path] = url
    return attachments, uploaded_digests


def preview_file_label(preview_path: Path) -> str:
    stem = preview_path.stem
    variant = "targeted"
    if stem.endswith("-full-page"):
        stem = stem.removesuffix("-full-page")
        variant = "full page"
    state = ""
    for candidate in ("before", "after"):
        if stem.endswith(f"-{candidate}"):
            stem = stem.removesuffix(f"-{candidate}")
            state = candidate
            break
    return " ".join(part for part in (stem, state, variant) if part)


def build_comment_body(
    *,
    repo: str,
    head_sha: str,
    branch_name: str,
    attachments: dict[str, str],
    captures: dict[str, dict] | None = None,
) -> str:
    delimiter = "`" * (max((len(run) for run in re.findall(r"`+", branch_name)), default=0) + 1)
    lines = [
        MARKER_COMMENT,
        f"Frontend previews for {delimiter} {branch_name} {delimiter}.",
        "",
        f"PR head: [`{head_sha}`](https://github.com/{repo}/commit/{head_sha}).",
    ]
    for relative_path, url in attachments.items():
        label = preview_file_label(Path(relative_path))
        lines.extend(["", f"### {label}", ""])
        capture = (captures or {}).get(relative_path)
        if capture:
            source_sha = capture["head_sha"]
            suffix = " (with uncommitted changes)" if capture.get("dirty") else ""
            lines.append(f"Captured from [`{source_sha}`](https://github.com/{repo}/commit/{source_sha}){suffix}.")
        else:
            lines.append("Capture revision unavailable.")
        lines.extend(["", f"![{label}]({url})"])
    return "\n".join(lines)


def is_marker_comment(comment: dict) -> bool:
    return (comment.get("body") or "").split("\n", 1)[0] == MARKER_COMMENT


def is_owned_marker(comment: dict, login: str) -> bool:
    return is_marker_comment(comment) and comment.get("user", {}).get("login", "").lower() == login.lower()


def fetch_marker_comments(repo: str, pr_number: int) -> list[dict]:
    page = 1
    markers = []
    while True:
        comments = gh_json(["api", f"repos/{repo}/issues/{pr_number}/comments?per_page=100&page={page}"]) or []
        if not comments:
            break
        markers.extend(comment for comment in comments if is_marker_comment(comment))
        page += 1
    return sorted(markers, key=lambda comment: comment["id"])


def reject_foreign_markers(comments: list[dict], login: str) -> None:
    for comment in comments:
        if not is_owned_marker(comment, login):
            owner = comment.get("user", {}).get("login", "another account")
            raise RuntimeError(
                f"The PR preview comment is owned by {owner}. Sync as that account; do not create a second marker."
            )


def fetch_existing_marker_comment(repo: str, pr_number: int, login: str):
    comments = fetch_marker_comments(repo, pr_number)
    reject_foreign_markers(comments, login)
    return comments[0] if comments else None


def validate_current_head(repo: str, pr_number: int, head_sha: str) -> None:
    current_pr = gh_json(["api", f"repos/{repo}/pulls/{pr_number}"])
    if current_pr.get("head", {}).get("sha") != head_sha or current_head_sha() != head_sha:
        raise RuntimeError("The PR or local head changed during upload. Re-sync previews at the current PR head.")


def delete_owned_marker(repo: str, pr_number: int, comment_id: int, login: str, head_sha: str | None = None) -> None:
    endpoint = f"repos/{repo}/issues/comments/{comment_id}"
    try:
        comment = gh_json(["api", endpoint])
    except RuntimeError as exc:
        if "(HTTP 404)" in str(exc):
            return
        raise
    if not is_owned_marker(comment, login):
        raise RuntimeError("The preview comment changed ownership or marker. No comment was deleted.")
    if head_sha is not None:
        validate_current_head(repo, pr_number, head_sha)
    try:
        gh_json(["api", endpoint, "--method", "DELETE"])
    except RuntimeError as exc:
        if "(HTTP 404)" not in str(exc):
            raise


def write_marker_comment(
    repo: str, pr_number: int, body: str, login: str, head_sha: str, comment_id: int | None = None
):
    endpoint = (
        f"repos/{repo}/issues/comments/{comment_id}" if comment_id else f"repos/{repo}/issues/{pr_number}/comments"
    )
    if comment_id is not None:
        current = gh_json(["api", endpoint])
        if not is_owned_marker(current, login):
            raise RuntimeError("The preview comment changed ownership or marker. No comment was updated.")
    validate_current_head(repo, pr_number, head_sha)
    return gh_json(
        [
            "api",
            endpoint,
            "--method",
            "PATCH" if comment_id else "POST",
            "--header",
            "Content-Type: application/json",
            "--input",
            "-",
        ],
        input_text=json.dumps({"body": body}),
    )


def upsert_comment(repo: str, pr_number: int, body: str, login: str, head_sha: str) -> None:
    existing = fetch_existing_marker_comment(repo, pr_number, login)
    comment = write_marker_comment(repo, pr_number, body, login, head_sha, existing["id"] if existing else None)
    comments = fetch_marker_comments(repo, pr_number)
    try:
        reject_foreign_markers(comments, login)
    except RuntimeError:
        if not existing:
            delete_owned_marker(repo, pr_number, comment["id"], login)
        raise
    if not comments:
        raise RuntimeError("The preview marker disappeared during sync. Retry at the current PR head.")
    canonical = comments[0]
    if canonical["id"] != comment["id"]:
        canonical = write_marker_comment(repo, pr_number, body, login, head_sha, canonical["id"])
    for duplicate in comments[1:]:
        delete_owned_marker(repo, pr_number, duplicate["id"], login, head_sha)
    print(f"{'Updated' if existing else 'Created'} PR preview comment: {canonical['html_url']}")


def delete_comment(repo: str, pr_number: int, login: str) -> None:
    comments = [comment for comment in fetch_marker_comments(repo, pr_number) if is_owned_marker(comment, login)]
    if not comments:
        print("No owned PR preview comment found.")
        return
    for comment in comments:
        delete_owned_marker(repo, pr_number, comment["id"], login)
        print(f"Deleted PR preview comment {comment['id']}.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Upload native GitHub attachments and sync the frontend PR preview comment."
    )
    parser.add_argument("--repo", help="GitHub.com repository in owner/name form. Defaults to the current gh repo.")
    parser.add_argument("--pr", type=int, help="Pull request number. Defaults to the current gh pr.")
    parser.add_argument("--branch", help="Preview directory branch name. Defaults to the current git branch.")
    parser.add_argument(
        "--delete", action="store_true", help="Explicitly delete your marked preview comment; attachments remain."
    )
    return parser


def main() -> int:
    args = build_parser().parse_args()
    try:
        repo = args.repo or infer_repo()
        if not re.fullmatch(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+", repo):
            raise RuntimeError("--repo must name a GitHub.com repository in owner/name form.")
        pr_number = args.pr or infer_pr_number(repo, args.branch)
        if args.delete:
            login = gh_json(["api", "user"])["login"]
            delete_comment(repo, pr_number, login)
            return 0

        require_attachment_support()
        branch_name = args.branch or current_branch_name()
        preview_files = list_preview_files(branch_name)
        if not preview_files:
            raise RuntimeError("No local preview PNGs found. Capture previews first; published previews are unchanged.")
        validate_preview_files(preview_files)
        repository = gh_json(["api", f"repos/{repo}"])
        if not repository.get("permissions", {}).get("push"):
            raise RuntimeError("Native attachment uploads require repository write access.")
        pr = gh_json(["api", f"repos/{repo}/pulls/{pr_number}"])
        head_sha = current_head_sha()
        if pr.get("head", {}).get("sha") != head_sha:
            raise RuntimeError("Local HEAD must match the PR head before publishing previews.")
        login = gh_json(["api", "user"])["login"]
        fetch_existing_marker_comment(repo, pr_number, login)
        attachments, uploaded_digests = upload_preview_files(repo, repository["id"], preview_files)
        captures = load_capture_metadata(preview_files, uploaded_digests)
        body = build_comment_body(
            repo=repo,
            head_sha=head_sha,
            branch_name=branch_name,
            attachments=attachments,
            captures=captures,
        )
        validate_current_head(repo, pr_number, head_sha)
        upsert_comment(repo, pr_number, body, login, head_sha)
        return 0
    except (OSError, RuntimeError, subprocess.CalledProcessError, ValueError, KeyError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
