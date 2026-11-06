import base64
import hashlib
import os
import re
import io
import json
import subprocess
import sys
import tempfile
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock
from urllib.parse import parse_qs, urlsplit

from unittest import TestCase

from agentics_tools.tools import context, preview, preview_sync

REPO = "example-org/example-repo"
BRANCH = "codex/example-branch"
BRANCH_DIRECTORY = f"codex-example-branch-{hashlib.sha256(BRANCH.encode()).hexdigest()[:16]}"
PREVIEW_DIRECTORY = f".github/pr-previews/.local/{BRANCH_DIRECTORY}"
BEFORE_PATH = f"{PREVIEW_DIRECTORY}/project-dashboard-before.png"
AFTER_PATH = f"{PREVIEW_DIRECTORY}/project-dashboard-after.png"
BEFORE_URL = "https://github.com/user-attachments/assets/11111111-1111-4111-8111-111111111111"
AFTER_URL = "https://github.com/user-attachments/assets/22222222-2222-4222-8222-222222222222"
PNG = base64.b64decode("iVBORw0KGgoAAAANSUhEUgAAAAEAAAABCAQAAAC1HAwCAAAAC0lEQVR42mP8/x8AAwMCAO+aP1sAAAAASUVORK5CYII=")


class RepositoryContextTests(TestCase):
    def setUp(self):
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.root = Path(directory.name).resolve()
        self.nested = self.root / "nested"
        self.nested.mkdir()
        subprocess.run(["git", "init", "--quiet"], cwd=self.root, check=True, capture_output=True)
        context.set_repo_root(None)
        self.addCleanup(context.set_repo_root, None)

    def test_discovers_callers_repository_from_nested_working_directory(self):
        with mock.patch.object(Path, "cwd", return_value=self.nested):
            self.assertEqual(context.repo_root(), self.root)
            self.assertFalse(context.has_explicit_repo_root())
            self.assertEqual(preview.branch_preview_dir(BRANCH).relative_to(self.root).as_posix(), PREVIEW_DIRECTORY)

    def test_explicit_target_is_canonical_and_independent_of_current_directory(self):
        context.set_repo_root(self.nested)
        with mock.patch.object(Path, "cwd", return_value=self.root / "does-not-exist"):
            self.assertTrue(context.has_explicit_repo_root())
            self.assertEqual(context.repo_root(), self.root)
            self.assertEqual(preview.repo_root(), self.root)
            self.assertEqual(preview_sync.repo_root(), self.root)
            self.assertEqual(preview.run_git(["rev-parse", "--show-toplevel"]).stdout.strip(), str(self.root))
            self.assertEqual(preview_sync.run(["git", "rev-parse", "--show-toplevel"]), str(self.root))

    def test_reset_returns_to_current_directory_discovery(self):
        context.set_repo_root(self.root)
        context.set_repo_root(None)
        with mock.patch.object(Path, "cwd", return_value=self.nested):
            self.assertFalse(context.has_explicit_repo_root())
            self.assertEqual(context.repo_root(), self.root)

    def test_selected_repository_removes_ambient_gh_repo_override(self):
        context.set_repo_root(self.root)
        with (
            mock.patch.dict(os.environ, {"GH_REPO": "ambient/wrong-repository", "PRESERVE_THIS": "yes"}),
            mock.patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "{}", "")) as run,
        ):
            preview_sync.run(["gh", "repo", "view"])
            self.assertNotIn("GH_REPO", run.call_args.kwargs["env"])
            self.assertEqual(run.call_args.kwargs["env"]["PRESERVE_THIS"], "yes")
            self.assertEqual(os.environ["GH_REPO"], "ambient/wrong-repository")

    def test_without_selected_repository_gh_environment_is_inherited(self):
        with (
            mock.patch.object(preview_sync, "repo_root", return_value=self.root),
            mock.patch.object(subprocess, "run", return_value=subprocess.CompletedProcess([], 0, "{}", "")) as run,
        ):
            preview_sync.run(["gh", "repo", "view"])
        self.assertIsNone(run.call_args.kwargs["env"])

    def test_invalid_target_and_non_repository_have_clear_errors(self):
        with self.assertRaisesRegex(ValueError, "directory does not exist"):
            context.set_repo_root(self.root / "missing")
        outside = tempfile.TemporaryDirectory()
        self.addCleanup(outside.cleanup)
        with self.assertRaisesRegex(RuntimeError, "No Git repository found"):
            context.set_repo_root(outside.name)
        with mock.patch.object(Path, "cwd", return_value=Path(outside.name)):
            with self.assertRaisesRegex(RuntimeError, "Use --repo-root"):
                context.repo_root()


class PreviewScriptTests(TestCase):
    def setUp(self):
        self.pr_preview = preview
        self.sync_pr_preview_comment = preview_sync
        directory = tempfile.TemporaryDirectory()
        self.addCleanup(directory.cleanup)
        self.temp_repo_root = Path(directory.name).resolve()
        subprocess.run(["git", "init", "--quiet"], cwd=self.temp_repo_root, check=True, capture_output=True)
        context.set_repo_root(self.temp_repo_root)
        self.addCleanup(context.set_repo_root, None)

    def create_preview(self, relative_path=BEFORE_PATH, content=PNG):
        path = self.temp_repo_root / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_bytes(content)
        return path

    def test_current_branch_name_raises_friendly_error_for_detached_head(self):
        with mock.patch.object(
            self.pr_preview.subprocess,
            "run",
            return_value=subprocess.CompletedProcess(
                args=["git", "symbolic-ref", "--quiet", "--short", "HEAD"],
                returncode=1,
                stdout="",
                stderr="detached HEAD",
            ),
        ):
            with self.assertRaisesRegex(RuntimeError, re.escape("Pass --branch explicitly.")):
                self.pr_preview.current_branch_name()

    def test_sanitize_branch_name_rejects_dot_segments(self):
        for branch_name in (".", "..", "-.-"):
            with self.subTest(branch_name=branch_name):
                with self.assertRaisesRegex(ValueError, re.escape("at least one alphanumeric character")):
                    self.pr_preview.sanitize_branch_name(branch_name)

    def test_branch_directories_are_distinct_after_slug_truncation_and_case_folding(self):
        branch_groups = (
            ("codex/foo/bar", "codex/foo-bar"),
            ("codex/" + "a" * 90 + "first", "codex/" + "a" * 90 + "second"),
            ("codex/Feature", "codex/feature"),
        )
        with mock.patch.object(self.pr_preview, "repo_root", return_value=self.temp_repo_root):
            for first_branch, second_branch in branch_groups:
                with self.subTest(first_branch=first_branch, second_branch=second_branch):
                    first_dir = self.pr_preview.branch_preview_dir(first_branch)
                    second_dir = self.pr_preview.branch_preview_dir(second_branch)
                    self.assertNotEqual(str(first_dir).casefold(), str(second_dir).casefold())
                    self.assertLessEqual(len(first_dir.name), 80)
                    first = self.pr_preview.preview_output_path("dashboard", first_branch)
                    first.parent.mkdir(parents=True)
                    first.write_bytes(PNG)
                    self.assertEqual(self.pr_preview.list_preview_files(second_branch), [])
                    self.pr_preview.clean_preview_dir(second_branch)
                    self.assertTrue(first.is_file())

    def test_versioned_branch_directory_cannot_reuse_or_delete_legacy_cache(self):
        branch = "codex/foo"
        legacy_branch = self.pr_preview.sanitize_branch_name(branch)
        legacy_path = self.create_preview(f".github/pr-previews/{legacy_branch}/dashboard.png")
        (legacy_path.parent / "attachments.json").write_text('{"legacy": "cache"}')
        with mock.patch.object(self.pr_preview, "repo_root", return_value=self.temp_repo_root):
            self.assertNotEqual(self.pr_preview.branch_preview_dir(branch), legacy_path.parent)
            self.assertEqual(self.pr_preview.list_preview_files(branch), [])
            self.pr_preview.clean_preview_dir(branch)
        self.assertTrue(legacy_path.is_file())
        self.assertTrue((legacy_path.parent / "attachments.json").is_file())

    def test_id_command_normalizes_mixed_case_preview_ids(self):
        stdout = io.StringIO()

        with mock.patch.object(sys, "argv", ["pr_preview.py", "id", "Project-App-Login"]):
            with redirect_stdout(stdout):
                exit_code = self.pr_preview.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(stdout.getvalue().strip(), "project-app-login")

    def test_path_command_adds_full_page_variant_suffix_after_state(self):
        stdout = io.StringIO()

        with mock.patch.object(
            sys,
            "argv",
            [
                "pr_preview.py",
                "path",
                "Project-Dashboard",
                "--branch",
                "codex/example-branch",
                "--state",
                "after",
                "--variant",
                "full-page",
            ],
        ):
            with redirect_stdout(stdout):
                exit_code = self.pr_preview.main()

        self.assertEqual(exit_code, 0)
        self.assertEqual(
            stdout.getvalue().strip(),
            f"{PREVIEW_DIRECTORY}/project-dashboard-after-full-page.png",
        )

    def test_preview_output_path_rejects_symlink_escapes_before_capture(self):
        outside_directory = tempfile.TemporaryDirectory()
        self.addCleanup(outside_directory.cleanup)
        preview_root = self.temp_repo_root / self.pr_preview.PREVIEW_ROOT
        preview_root.mkdir(parents=True)
        (preview_root / self.pr_preview.sanitize_branch_name("codex/escape-branch")).symlink_to(
            outside_directory.name, target_is_directory=True
        )
        safe_directory = preview_root / BRANCH_DIRECTORY
        safe_directory.mkdir()
        (safe_directory / "dashboard-after.png").symlink_to(Path(outside_directory.name) / "target.png")

        with mock.patch.object(self.pr_preview, "repo_root", return_value=self.temp_repo_root):
            with self.assertRaises(ValueError):
                self.pr_preview.branch_preview_dir("codex/escape-branch")
            with self.assertRaises(ValueError):
                self.pr_preview.preview_output_path("dashboard", "codex/escape-branch", "after")
            with self.assertRaises(ValueError):
                self.pr_preview.preview_output_path("dashboard", "codex/example-branch", "after")

    def test_preview_output_path_rejects_internal_branch_directory_symlink(self):
        original = PNG + b"existing asset"
        target = self.create_preview("protected-assets/dashboard-after.png", original)
        preview_root = self.temp_repo_root / self.pr_preview.PREVIEW_ROOT
        preview_root.mkdir(parents=True)
        (preview_root / self.pr_preview.sanitize_branch_name("codex/internal-branch")).symlink_to(
            target.parent, target_is_directory=True
        )

        with mock.patch.object(self.pr_preview, "repo_root", return_value=self.temp_repo_root):
            with self.assertRaisesRegex(ValueError, re.escape("directories must not use symbolic links")):
                self.pr_preview.preview_output_path("dashboard", "codex/internal-branch", "after")

        self.assertEqual(target.read_bytes(), original)

    def test_preview_output_path_rejects_internal_existing_output_file_symlink(self):
        original = PNG + b"existing asset"
        target = self.create_preview("protected-assets/image.png", original)
        preview_directory = self.temp_repo_root / PREVIEW_DIRECTORY
        preview_directory.mkdir(parents=True)
        (preview_directory / "dashboard-after.png").symlink_to(target)

        with mock.patch.object(self.pr_preview, "repo_root", return_value=self.temp_repo_root):
            with self.assertRaisesRegex(ValueError, re.escape("output files must not use symbolic links")):
                self.pr_preview.preview_output_path("dashboard", "codex/example-branch", "after")

        self.assertEqual(target.read_bytes(), original)


    def test_require_attachment_support_rejects_old_cli(self):
        with mock.patch.object(self.sync_pr_preview_comment, "run", return_value="gh version 2.96.0 (2026-06-01)"):
            with self.assertRaisesRegex(RuntimeError, re.escape("2.99.0")):
                self.sync_pr_preview_comment.require_attachment_support()

    def test_require_attachment_support_accepts_minimum_and_newer_cli(self):
        for version in ("2.99.0", "2.100.0", "3.0.0"):
            with self.subTest(version=version):
                with mock.patch.object(self.sync_pr_preview_comment, "run", return_value=f"gh version {version}"):
                    self.sync_pr_preview_comment.require_attachment_support()

    def test_gh_json_binds_api_requests_to_github_com(self):
        for endpoint in ("user", f"repos/{REPO}", "https://uploads.github.com/user-attachments/assets"):
            with self.subTest(endpoint=endpoint):
                with mock.patch.object(self.sync_pr_preview_comment, "run", return_value='{"id": 123}') as run:
                    self.assertEqual(self.sync_pr_preview_comment.gh_json(["api", endpoint]), {"id": 123})

                args = run.call_args.args[0]
                self.assertEqual(args[:2], ["gh", "api"])
                self.assertIn(endpoint, args)
                self.assertEqual(args[args.index("--hostname") + 1], "github.com")

    def test_infer_pr_number_binds_github_repository_and_branch(self):
        for branch in (None, "codex/requested-branch"):
            with self.subTest(branch=branch):
                with (
                    mock.patch.object(self.sync_pr_preview_comment, "run", return_value="2517") as run,
                    mock.patch.object(
                        self.sync_pr_preview_comment, "current_branch_name", return_value="codex/current-branch"
                    ) as current_branch,
                ):
                    self.assertEqual(self.sync_pr_preview_comment.infer_pr_number(REPO, branch), 2517)

                args = run.call_args.args[0]
                self.assertEqual(args[:4], ["gh", "pr", "view", branch or "codex/current-branch"])
                self.assertEqual(args[args.index("--repo") + 1], f"github.com/{REPO}")
                if branch is None:
                    current_branch.assert_called_once_with()
                else:
                    current_branch.assert_not_called()

    def test_validate_preview_files_rejects_unsafe_or_invalid_files(self):
        valid = self.create_preview()
        empty = self.create_preview(f"{PREVIEW_DIRECTORY}/empty.png", b"")
        invalid = self.create_preview(f"{PREVIEW_DIRECTORY}/invalid.png", b"private configuration")
        oversized = self.create_preview(f"{PREVIEW_DIRECTORY}/oversized.png")
        with oversized.open("r+b") as handle:
            handle.truncate(10 * 1024 * 1024 + 1)
        directory = self.temp_repo_root / PREVIEW_DIRECTORY / "directory.png"
        directory.mkdir()
        symlink = self.temp_repo_root / PREVIEW_DIRECTORY / "symlink.png"
        symlink.symlink_to(valid)
        missing = self.temp_repo_root / PREVIEW_DIRECTORY / "missing.png"
        outside_directory = tempfile.TemporaryDirectory()
        self.addCleanup(outside_directory.cleanup)
        (Path(outside_directory.name) / "outside.png").write_bytes(PNG)
        linked_directory = self.temp_repo_root / ".github/pr-previews/outside-branch"
        linked_directory.symlink_to(outside_directory.name, target_is_directory=True)
        escaped = linked_directory / "outside.png"

        with mock.patch.object(self.sync_pr_preview_comment, "repo_root", return_value=self.temp_repo_root):
            self.sync_pr_preview_comment.validate_preview_files([valid])
            for path in (missing, directory, symlink, empty, invalid, oversized, escaped):
                with self.subTest(filename=path.name):
                    with self.assertRaises((OSError, RuntimeError, ValueError)):
                        self.sync_pr_preview_comment.validate_preview_files([path])

    def test_upload_validates_all_files_before_any_network_write(self):
        valid = self.create_preview()
        empty = self.create_preview(AFTER_PATH, b"")

        with (
            mock.patch.object(self.sync_pr_preview_comment, "repo_root", return_value=self.temp_repo_root),
            mock.patch.object(self.sync_pr_preview_comment, "gh_json") as gh_json,
        ):
            with self.assertRaises((RuntimeError, ValueError)):
                self.sync_pr_preview_comment.upload_preview_files(REPO, 123, [valid, empty])

        gh_json.assert_not_called()

    def test_upload_uses_native_attachment_endpoint_and_binary_input(self):
        preview = self.create_preview()

        def inspect_snapshot(args):
            snapshot = Path(args[args.index("--input") + 1])
            self.assertNotEqual(snapshot, preview)
            self.assertEqual(snapshot.parent, preview.parent)
            self.assertEqual(snapshot.read_bytes(), PNG)
            return {"url": BEFORE_URL}

        with (
            mock.patch.object(self.sync_pr_preview_comment, "repo_root", return_value=self.temp_repo_root),
            mock.patch.object(self.sync_pr_preview_comment, "gh_json", side_effect=inspect_snapshot) as gh_json,
        ):
            attachments, uploaded_digests = self.sync_pr_preview_comment.upload_preview_files(REPO, 123, [preview])

        self.assertEqual(attachments, {BEFORE_PATH: BEFORE_URL})
        self.assertEqual(uploaded_digests, {BEFORE_PATH: self.pr_preview.preview_file_digest(preview)})
        args = gh_json.call_args.args[0]
        upload_url = urlsplit(args[1])
        self.assertEqual(args[0], "api")
        self.assertEqual(upload_url.scheme, "https")
        self.assertEqual(upload_url.netloc, "uploads.github.com")
        self.assertEqual(upload_url.path, "/user-attachments/assets")
        self.assertEqual(
            parse_qs(upload_url.query),
            {"name": [preview.name], "content_type": ["image/png"], "repository_id": ["123"]},
        )
        self.assertEqual(args[args.index("--method") + 1], "POST")
        self.assertIn("Content-Type: application/octet-stream", args)

    def test_upload_reuses_unchanged_content_and_uploads_changed_content(self):
        preview = self.create_preview()

        with (
            mock.patch.object(self.sync_pr_preview_comment, "repo_root", return_value=self.temp_repo_root),
            mock.patch.object(
                self.sync_pr_preview_comment, "gh_json", side_effect=[{"url": BEFORE_URL}, {"url": AFTER_URL}]
            ) as gh_json,
        ):
            first, first_digests = self.sync_pr_preview_comment.upload_preview_files(REPO, 123, [preview])
            second, second_digests = self.sync_pr_preview_comment.upload_preview_files(REPO, 123, [preview])
            preview.write_bytes(PNG + b"changed")
            changed, changed_digests = self.sync_pr_preview_comment.upload_preview_files(REPO, 123, [preview])

        self.assertEqual(first, {BEFORE_PATH: BEFORE_URL})
        self.assertEqual(second, first)
        self.assertEqual(changed, {BEFORE_PATH: AFTER_URL})
        self.assertEqual(first_digests, second_digests)
        self.assertNotEqual(changed_digests, first_digests)
        self.assertEqual(gh_json.call_count, 2)

    def test_upload_does_not_reuse_another_repository_attachment(self):
        preview = self.create_preview()

        with (
            mock.patch.object(self.sync_pr_preview_comment, "repo_root", return_value=self.temp_repo_root),
            mock.patch.object(
                self.sync_pr_preview_comment, "gh_json", side_effect=[{"url": BEFORE_URL}, {"url": AFTER_URL}]
            ) as gh_json,
        ):
            self.sync_pr_preview_comment.upload_preview_files(REPO, 123, [preview])
            attachments, _ = self.sync_pr_preview_comment.upload_preview_files("other/repository", 456, [preview])

        self.assertEqual(attachments, {BEFORE_PATH: AFTER_URL})
        self.assertEqual(gh_json.call_count, 2)

    def test_upload_does_not_reuse_cache_for_recreated_repository_with_same_name(self):
        preview = self.create_preview()
        with (
            mock.patch.object(self.sync_pr_preview_comment, "repo_root", return_value=self.temp_repo_root),
            mock.patch.object(
                self.sync_pr_preview_comment, "gh_json", side_effect=[{"url": BEFORE_URL}, {"url": AFTER_URL}]
            ) as api,
        ):
            self.sync_pr_preview_comment.upload_preview_files(REPO, 123, [preview])
            attachments, _ = self.sync_pr_preview_comment.upload_preview_files(REPO, 456, [preview])
        self.assertEqual(attachments, {BEFORE_PATH: AFTER_URL})
        self.assertEqual(api.call_count, 2)
        cache = json.loads((preview.parent / "attachments.json").read_text())
        self.assertEqual(cache["repository_id"], 456)

    def test_upload_persists_completed_assets_for_partial_retry(self):
        before = self.create_preview()
        after = self.create_preview(AFTER_PATH)
        cache = before.parent / "attachments.json"

        with (
            mock.patch.object(self.sync_pr_preview_comment, "repo_root", return_value=self.temp_repo_root),
            mock.patch.object(
                self.sync_pr_preview_comment,
                "gh_json",
                side_effect=[{"url": BEFORE_URL}, RuntimeError("upload interrupted")],
            ) as first_attempt,
        ):
            with self.assertRaisesRegex(RuntimeError, re.escape("upload interrupted")):
                self.sync_pr_preview_comment.upload_preview_files(REPO, 123, [before, after])

        self.assertEqual(first_attempt.call_count, 2)
        self.assertIn(BEFORE_URL, cache.read_text())
        with (
            mock.patch.object(self.sync_pr_preview_comment, "repo_root", return_value=self.temp_repo_root),
            mock.patch.object(self.sync_pr_preview_comment, "gh_json", return_value={"url": AFTER_URL}) as retry,
        ):
            attachments, _ = self.sync_pr_preview_comment.upload_preview_files(REPO, 123, [before, after])

        self.assertEqual(attachments, {BEFORE_PATH: BEFORE_URL, AFTER_PATH: AFTER_URL})
        retry.assert_called_once()
        self.assertIn(AFTER_URL, cache.read_text())

    def test_upload_rejects_unexpected_asset_urls(self):
        preview = self.create_preview()
        for url in (
            "https://example.com/user-attachments/assets/123",
            "http://github.com/user-attachments/assets/123",
            "https://github.com/example-org/example-repo/blob/main/secret.png",
        ):
            with self.subTest(url=url):
                with (
                    mock.patch.object(self.sync_pr_preview_comment, "repo_root", return_value=self.temp_repo_root),
                    mock.patch.object(self.sync_pr_preview_comment, "gh_json", return_value={"url": url}),
                ):
                    with self.assertRaises((RuntimeError, ValueError)):
                        self.sync_pr_preview_comment.upload_preview_files(REPO, 123, [preview])

    def test_upload_recovers_from_malformed_cache_or_invalid_cached_url(self):
        preview = self.create_preview()
        invalid_url_cache = {
            "repo": REPO,
            "repository_id": 123,
            "files": {BEFORE_PATH: {"sha256": self.pr_preview.preview_file_digest(preview), "url": None}},
        }
        for cache_contents in ("{truncated", json.dumps(invalid_url_cache)):
            with self.subTest(cache_contents=cache_contents):
                (preview.parent / "attachments.json").write_text(cache_contents)
                with (
                    mock.patch.object(self.sync_pr_preview_comment, "repo_root", return_value=self.temp_repo_root),
                    mock.patch.object(
                        self.sync_pr_preview_comment, "gh_json", return_value={"url": BEFORE_URL}
                    ) as gh_json,
                ):
                    attachments, _ = self.sync_pr_preview_comment.upload_preview_files(REPO, 123, [preview])

                self.assertEqual(attachments, {BEFORE_PATH: BEFORE_URL})
                gh_json.assert_called_once()

    def test_upload_rejects_attachment_metadata_symlink_without_changing_target(self):
        preview = self.create_preview()
        protected = self.temp_repo_root / "protected.json"
        original = b'{"protected": true}\n'
        protected.write_bytes(original)
        (preview.parent / "attachments.json").symlink_to(protected)

        with (
            mock.patch.object(self.sync_pr_preview_comment, "repo_root", return_value=self.temp_repo_root),
            mock.patch.object(self.sync_pr_preview_comment, "gh_json") as gh_json,
        ):
            with self.assertRaises(ValueError):
                self.sync_pr_preview_comment.upload_preview_files(REPO, 123, [preview])

        self.assertEqual(protected.read_bytes(), original)
        gh_json.assert_not_called()

    def test_upload_ignores_obsolete_temporary_metadata_symlink(self):
        preview = self.create_preview()
        protected = self.temp_repo_root / "protected.json"
        original = b'{"protected": true}\n'
        protected.write_bytes(original)
        (preview.parent / "attachments.tmp").symlink_to(protected)

        with (
            mock.patch.object(self.sync_pr_preview_comment, "repo_root", return_value=self.temp_repo_root),
            mock.patch.object(self.sync_pr_preview_comment, "gh_json", return_value={"url": BEFORE_URL}),
        ):
            attachments, _ = self.sync_pr_preview_comment.upload_preview_files(REPO, 123, [preview])

        self.assertEqual(attachments, {BEFORE_PATH: BEFORE_URL})
        self.assertEqual(protected.read_bytes(), original)
        self.assertIn(BEFORE_URL, (preview.parent / "attachments.json").read_text())

    def test_fetch_existing_marker_comment_reads_all_pages_before_returning_owned_match(self):
        gh_json = mock.Mock(
            side_effect=[
                [{"id": 1, "body": "Unrelated comment", "user": {"login": "someone-else"}}],
                [{"id": 2, "body": f"{self.pr_preview.MARKER_COMMENT}\nhello", "user": {"login": "preview-owner"}}],
                [],
            ]
        )

        with mock.patch.object(self.sync_pr_preview_comment, "gh_json", gh_json):
            actual = self.sync_pr_preview_comment.fetch_existing_marker_comment(REPO, 1116, "preview-owner")

        self.assertEqual(actual["id"], 2)
        self.assertEqual(
            gh_json.mock_calls,
            [
                mock.call(
                    [
                        "api",
                        "repos/example-org/example-repo/issues/1116/comments?per_page=100&page=1",
                    ]
                ),
                mock.call(
                    [
                        "api",
                        "repos/example-org/example-repo/issues/1116/comments?per_page=100&page=2",
                    ]
                ),
                mock.call(
                    [
                        "api",
                        "repos/example-org/example-repo/issues/1116/comments?per_page=100&page=3",
                    ]
                ),
            ],
        )

    def test_fetch_existing_marker_comment_leaves_other_authors_untouched(self):
        gh_json = mock.Mock(
            side_effect=[
                [{"id": 1, "body": self.pr_preview.MARKER_COMMENT, "user": {"login": "someone-else"}}],
                [],
            ]
        )

        with mock.patch.object(self.sync_pr_preview_comment, "gh_json", gh_json):
            with self.assertRaisesRegex(RuntimeError, re.escape("owned by")):
                self.sync_pr_preview_comment.fetch_existing_marker_comment(REPO, 1116, "preview-owner")

    def test_fetch_existing_marker_comment_selects_oldest_owned_marker_across_pages(self):
        gh_json = mock.Mock(
            side_effect=[
                [{"id": 1, "body": self.pr_preview.MARKER_COMMENT, "user": {"login": "preview-owner"}}],
                [{"id": 2, "body": self.pr_preview.MARKER_COMMENT, "user": {"login": "preview-owner"}}],
                [],
            ]
        )

        with mock.patch.object(self.sync_pr_preview_comment, "gh_json", gh_json):
            existing = self.sync_pr_preview_comment.fetch_existing_marker_comment(REPO, 1116, "preview-owner")
        self.assertEqual(existing["id"], 1)

    def test_marker_mentions_are_not_owned_automation_comments(self):
        marker = self.pr_preview.MARKER_COMMENT
        comments = [
            {"id": 1, "body": f"Please preserve {marker}", "user": {"login": "preview-owner"}},
            {"id": 2, "body": f"Quoted marker:\n{marker}", "user": {"login": "preview-owner"}},
        ]
        with mock.patch.object(self.sync_pr_preview_comment, "gh_json", side_effect=[comments, []]):
            self.assertIsNone(self.sync_pr_preview_comment.fetch_existing_marker_comment(REPO, 2517, "preview-owner"))

    def test_build_comment_body_embeds_native_attachments_and_head_sha(self):
        full_page_path = f"{PREVIEW_DIRECTORY}/project-dashboard-after-full-page.png"
        body = self.sync_pr_preview_comment.build_comment_body(
            repo=REPO,
            head_sha="abc123",
            branch_name="codex/example-branch",
            attachments={BEFORE_PATH: BEFORE_URL, full_page_path: AFTER_URL},
        )

        self.assertIn(self.pr_preview.MARKER_COMMENT, body)
        self.assertIn("Frontend previews for ` codex/example-branch `.", body)
        self.assertNotIn(BRANCH_DIRECTORY, body)
        self.assertIn("abc123", body)
        self.assertIn("before targeted", body)
        self.assertIn("after full page", body)
        self.assertIn(f"]({BEFORE_URL})", body)
        self.assertIn(f"]({AFTER_URL})", body)
        self.assertEqual(body.count("!["), 2)
        self.assertNotIn("/blob/", body)
        self.assertNotIn("raw.githubusercontent.com", body)
        self.assertNotIn("Remove `.github/pr-previews", body)
        self.assertIn("Capture revision unavailable.", body)

    def test_comment_branch_label_uses_code_delimiter_longer_than_embedded_backticks(self):
        branch = "codex/<preview>__`label``"
        body = self.sync_pr_preview_comment.build_comment_body(
            repo=REPO, head_sha="abc123", branch_name=branch, attachments={}
        )
        self.assertIn(f"Frontend previews for ``` {branch} ```.", body)
        self.assertNotIn(self.pr_preview.sanitize_branch_name(branch), body)

    def initialize_source_repo(self):
        source = self.temp_repo_root / "source.txt"
        source.write_text("original source\n")
        (self.temp_repo_root / ".gitignore").write_text(".github/pr-previews/\n")
        for args in (
            ["init", "--quiet"],
            ["config", "user.name", "Preview tests"],
            ["config", "user.email", "preview@example.com"],
            ["config", "commit.gpgsign", "false"],
            ["config", "core.autocrlf", "false"],
            ["add", "."],
            ["commit", "--quiet", "-m", "Initial source"],
        ):
            subprocess.run(["git", *args], cwd=self.temp_repo_root, check=True, capture_output=True)
        return source

    def test_capture_metadata_preserves_stable_clean_and_dirty_sources_and_ignores_modified_images(self):
        source = self.initialize_source_repo()
        before = self.create_preview()
        after = self.create_preview(AFTER_PATH)
        with mock.patch.object(self.pr_preview, "repo_root", return_value=self.temp_repo_root):
            clean = self.pr_preview.capture_source_snapshot()
            self.pr_preview.record_preview_capture([before], clean)
            source.write_text("changed source\n")
            dirty = self.pr_preview.capture_source_snapshot()
            self.pr_preview.record_preview_capture([after], dirty)
            captures = self.pr_preview.load_capture_metadata([before, after])
            self.assertEqual(captures[BEFORE_PATH]["head_sha"], clean["head_sha"])
            self.assertFalse(captures[BEFORE_PATH]["dirty"])
            self.assertTrue(captures[AFTER_PATH]["dirty"])
            self.assertEqual(captures[AFTER_PATH]["source_fingerprint"], dirty["source_fingerprint"])
            before.write_bytes(PNG + b"modified")
            remaining = self.pr_preview.load_capture_metadata([before, after])
        self.assertEqual(set(remaining), {AFTER_PATH})

    def test_source_snapshot_detects_edits_to_already_dirty_and_nonignored_untracked_files(self):
        source = self.initialize_source_repo()
        source.write_text("first edit\n")
        with mock.patch.object(self.pr_preview, "repo_root", return_value=self.temp_repo_root):
            first = self.pr_preview.capture_source_snapshot()
            source.write_text("second edit\n")
            second = self.pr_preview.capture_source_snapshot()
            untracked = self.temp_repo_root / "new-template.html"
            untracked.write_text("first untracked version")
            third = self.pr_preview.capture_source_snapshot()
            untracked.write_text("second untracked version")
            fourth = self.pr_preview.capture_source_snapshot()
        self.assertEqual(first["head_sha"], second["head_sha"])
        self.assertTrue(first["dirty"] and second["dirty"])
        self.assertEqual(len({item["source_fingerprint"] for item in (first, second, third, fourth)}), 4)

    def test_source_snapshot_includes_staged_content_when_worktree_matches_head(self):
        source = self.initialize_source_repo()
        with mock.patch.object(self.pr_preview, "repo_root", return_value=self.temp_repo_root):
            source.write_text("first staged edit\n")
            subprocess.run(["git", "add", "source.txt"], cwd=self.temp_repo_root, check=True, capture_output=True)
            source.write_text("original source\n")
            first = self.pr_preview.capture_source_snapshot()
            source.write_text("second staged edit\n")
            subprocess.run(["git", "add", "source.txt"], cwd=self.temp_repo_root, check=True, capture_output=True)
            source.write_text("original source\n")
            second = self.pr_preview.capture_source_snapshot()
        self.assertTrue(first["dirty"] and second["dirty"])
        self.assertNotEqual(first["source_fingerprint"], second["source_fingerprint"])

    def test_source_snapshot_ignores_local_preview_artifacts(self):
        self.initialize_source_repo()
        with mock.patch.object(self.pr_preview, "repo_root", return_value=self.temp_repo_root):
            before = self.pr_preview.capture_source_snapshot()
            preview = self.create_preview()
            (preview.parent / "attachments.json").write_text('{"upload": "in progress"}')
            self.assertEqual(self.pr_preview.capture_source_snapshot(), before)

    def test_capture_drift_rejects_provenance_without_replacing_existing_metadata(self):
        source = self.initialize_source_repo()
        preview = self.create_preview()
        metadata_path = preview.parent / "captures.json"
        metadata_path.write_text('{"existing": "capture"}')
        original_metadata = metadata_path.read_bytes()
        with mock.patch.object(self.pr_preview, "repo_root", return_value=self.temp_repo_root):
            snapshot = self.pr_preview.capture_source_snapshot()
            source.write_text("changed during rendering\n")
            with self.assertRaisesRegex(RuntimeError, re.escape("Source changed during capture")):
                self.pr_preview.record_preview_capture([preview], snapshot)
        self.assertEqual(metadata_path.read_bytes(), original_metadata)

    def test_head_drift_during_capture_cannot_write_provenance(self):
        source = self.initialize_source_repo()
        preview = self.create_preview()
        with mock.patch.object(self.pr_preview, "repo_root", return_value=self.temp_repo_root):
            snapshot = self.pr_preview.capture_source_snapshot()
            source.write_text("new revision\n")
            subprocess.run(["git", "add", "source.txt"], cwd=self.temp_repo_root, check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "--quiet", "-m", "Advance source"],
                cwd=self.temp_repo_root,
                check=True,
                capture_output=True,
            )
            with self.assertRaisesRegex(RuntimeError, re.escape("Source changed during capture")):
                self.pr_preview.record_preview_capture([preview], snapshot)
        self.assertFalse((preview.parent / "captures.json").exists())

    def test_source_drift_while_hashing_previews_cannot_write_provenance(self):
        source = self.initialize_source_repo()
        preview = self.create_preview()
        original_digest = self.pr_preview.preview_file_digest(preview)

        def change_source(path):
            source.write_text("changed while hashing\n")
            return original_digest

        with mock.patch.object(self.pr_preview, "repo_root", return_value=self.temp_repo_root):
            snapshot = self.pr_preview.capture_source_snapshot()
            with mock.patch.object(self.pr_preview, "preview_file_digest", side_effect=change_source):
                with self.assertRaisesRegex(RuntimeError, re.escape("Source changed while hashing")):
                    self.pr_preview.record_preview_capture([preview], snapshot)
        self.assertFalse((preview.parent / "captures.json").exists())


    def test_capture_metadata_symlink_cannot_change_protected_target(self):
        self.initialize_source_repo()
        preview = self.create_preview()
        protected = self.temp_repo_root / "protected.json"
        original = b'{"protected": true}\n'
        protected.write_bytes(original)
        (preview.parent / "captures.json").symlink_to(protected)
        with mock.patch.object(self.pr_preview, "repo_root", return_value=self.temp_repo_root):
            snapshot = self.pr_preview.capture_source_snapshot()
            with self.assertRaises(ValueError):
                self.pr_preview.record_preview_capture([preview], snapshot)
            with self.assertRaises(ValueError):
                self.pr_preview.load_capture_metadata([preview])
        self.assertEqual(protected.read_bytes(), original)

    def test_capture_metadata_falls_back_when_json_or_records_are_malformed(self):
        preview = self.create_preview()
        digest = self.pr_preview.preview_file_digest(preview)
        malformed = (
            "{truncated",
            json.dumps(["wrong top-level shape"]),
            json.dumps({BEFORE_PATH: "wrong record shape"}),
            json.dumps({BEFORE_PATH: {"sha256": digest}}),
            json.dumps({BEFORE_PATH: {"sha256": digest, "head_sha": 123, "dirty": False}}),
            json.dumps({BEFORE_PATH: {"sha256": digest, "head_sha": "head123", "dirty": "false"}}),
            json.dumps({BEFORE_PATH: {"sha256": digest, "head_sha": "head123", "dirty": False}}),
        )
        with mock.patch.object(self.pr_preview, "repo_root", return_value=self.temp_repo_root):
            for contents in malformed:
                with self.subTest(contents=contents):
                    (preview.parent / "captures.json").write_text(contents)
                    self.assertEqual(self.pr_preview.load_capture_metadata([preview]), {})

    def test_build_comment_body_reports_capture_revision_separately_from_pr_head(self):
        body = self.sync_pr_preview_comment.build_comment_body(
            repo=REPO,
            head_sha="prhead123",
            branch_name="codex/example-branch",
            attachments={BEFORE_PATH: BEFORE_URL},
            captures={BEFORE_PATH: {"head_sha": "captured456", "dirty": True}},
        )

        self.assertIn(f"https://github.com/{REPO}/commit/prhead123", body)
        self.assertIn(f"https://github.com/{REPO}/commit/captured456", body)
        self.assertIn("with uncommitted changes", body)
        self.assertNotIn("Capture revision unavailable.", body)

    def marker_comment(self, comment_id, login="preview-owner"):
        return {
            "id": comment_id,
            "body": self.pr_preview.MARKER_COMMENT,
            "user": {"login": login},
            "html_url": f"https://github.com/comment/{comment_id}",
        }

    def test_upsert_comment_updates_owned_marker_id_after_head_check(self):
        comment = self.marker_comment(42)
        calls = mock.Mock()
        calls.attach_mock(mock.Mock(return_value=comment), "lookup")
        calls.attach_mock(mock.Mock(), "validate")
        calls.attach_mock(mock.Mock(return_value=comment), "write")
        with (
            mock.patch.object(self.sync_pr_preview_comment, "fetch_existing_marker_comment", calls.lookup),
            mock.patch.object(self.sync_pr_preview_comment, "fetch_marker_comments", return_value=[comment]),
            mock.patch.object(self.sync_pr_preview_comment, "validate_current_head", calls.validate),
            mock.patch.object(self.sync_pr_preview_comment, "gh_json", calls.write),
            redirect_stdout(io.StringIO()),
        ):
            self.sync_pr_preview_comment.upsert_comment(REPO, 2517, "preview body", "preview-owner", "head123")
        self.assertEqual([call[0] for call in calls.mock_calls], ["lookup", "write", "validate", "write"])
        args = calls.write.call_args.args[0]
        self.assertEqual(args[1], f"repos/{REPO}/issues/comments/42")
        self.assertEqual(args[args.index("--method") + 1], "PATCH")
        self.assertEqual(json.loads(calls.write.call_args.kwargs["input_text"]), {"body": "preview body"})

    def test_upsert_concurrent_create_keeps_oldest_owned_marker_and_removes_duplicate(self):
        canonical = self.marker_comment(10)
        created = self.marker_comment(42)
        with (
            mock.patch.object(self.sync_pr_preview_comment, "fetch_existing_marker_comment", return_value=None),
            mock.patch.object(self.sync_pr_preview_comment, "fetch_marker_comments", return_value=[canonical, created]),
            mock.patch.object(self.sync_pr_preview_comment, "validate_current_head") as validate,
            mock.patch.object(
                self.sync_pr_preview_comment, "gh_json", side_effect=[created, canonical, canonical, created, None]
            ) as gh_json,
            redirect_stdout(io.StringIO()),
        ):
            self.sync_pr_preview_comment.upsert_comment(REPO, 2517, "preview body", "preview-owner", "head123")
        requests = [call.args[0] for call in gh_json.call_args_list]
        self.assertEqual(requests[0][requests[0].index("--method") + 1], "POST")
        self.assertEqual(requests[1][1], f"repos/{REPO}/issues/comments/10")
        self.assertEqual(requests[1], ["api", f"repos/{REPO}/issues/comments/10"])
        self.assertEqual(requests[2][requests[2].index("--method") + 1], "PATCH")
        self.assertEqual(requests[3], ["api", f"repos/{REPO}/issues/comments/42"])
        self.assertEqual(requests[4], ["api", f"repos/{REPO}/issues/comments/42", "--method", "DELETE"])
        self.assertEqual(validate.call_count, 3)

    def test_upsert_existing_owned_duplicates_converge(self):
        canonical = self.marker_comment(10)
        duplicate = self.marker_comment(42)
        with (
            mock.patch.object(self.sync_pr_preview_comment, "fetch_existing_marker_comment", return_value=canonical),
            mock.patch.object(
                self.sync_pr_preview_comment, "fetch_marker_comments", return_value=[canonical, duplicate]
            ),
            mock.patch.object(self.sync_pr_preview_comment, "validate_current_head"),
            mock.patch.object(
                self.sync_pr_preview_comment, "gh_json", side_effect=[canonical, canonical, duplicate, None]
            ) as api,
            redirect_stdout(io.StringIO()),
        ):
            self.sync_pr_preview_comment.upsert_comment(REPO, 2517, "preview body", "preview-owner", "head123")
        self.assertEqual(api.call_args.args[0], ["api", f"repos/{REPO}/issues/comments/42", "--method", "DELETE"])

    def test_foreign_marker_race_removes_only_this_invocations_new_owned_marker(self):
        created = self.marker_comment(42)
        foreign = self.marker_comment(10, "someone-else")
        with (
            mock.patch.object(self.sync_pr_preview_comment, "fetch_existing_marker_comment", return_value=None),
            mock.patch.object(self.sync_pr_preview_comment, "fetch_marker_comments", return_value=[foreign, created]),
            mock.patch.object(
                self.sync_pr_preview_comment,
                "validate_current_head",
                side_effect=[None, RuntimeError("PR advanced after our POST")],
            ) as validate,
            mock.patch.object(self.sync_pr_preview_comment, "gh_json", side_effect=[created, created, None]) as api,
        ):
            with self.assertRaisesRegex(RuntimeError, re.escape("owned by someone-else")):
                self.sync_pr_preview_comment.upsert_comment(REPO, 2517, "preview body", "preview-owner", "head123")
        self.assertEqual(api.call_args.args[0], ["api", f"repos/{REPO}/issues/comments/42", "--method", "DELETE"])
        validate.assert_called_once_with(REPO, 2517, "head123")
        self.assertTrue(all(call.args[0][1] != f"repos/{REPO}/issues/comments/10" for call in api.call_args_list))

    def test_duplicate_is_revalidated_before_deletion(self):
        canonical = self.marker_comment(10)
        duplicate = self.marker_comment(42)
        changed = self.marker_comment(42, "someone-else")
        with (
            mock.patch.object(self.sync_pr_preview_comment, "fetch_existing_marker_comment", return_value=canonical),
            mock.patch.object(
                self.sync_pr_preview_comment, "fetch_marker_comments", return_value=[canonical, duplicate]
            ),
            mock.patch.object(self.sync_pr_preview_comment, "validate_current_head"),
            mock.patch.object(
                self.sync_pr_preview_comment, "gh_json", side_effect=[canonical, canonical, changed]
            ) as api,
        ):
            with self.assertRaisesRegex(RuntimeError, re.escape("No comment was deleted")):
                self.sync_pr_preview_comment.upsert_comment(REPO, 2517, "preview body", "preview-owner", "head123")
        self.assertFalse(any("DELETE" in call.args[0] for call in api.call_args_list))

    def test_repurposed_owned_marker_is_not_overwritten(self):
        original = self.marker_comment(42)
        repurposed = {**original, "body": "Manual review notes"}
        with (
            mock.patch.object(self.sync_pr_preview_comment, "fetch_existing_marker_comment", return_value=original),
            mock.patch.object(self.sync_pr_preview_comment, "validate_current_head") as validate,
            mock.patch.object(self.sync_pr_preview_comment, "gh_json", return_value=repurposed) as api,
        ):
            with self.assertRaisesRegex(RuntimeError, re.escape("No comment was updated")):
                self.sync_pr_preview_comment.upsert_comment(REPO, 2517, "preview body", "preview-owner", "head123")
        api.assert_called_once_with(["api", f"repos/{REPO}/issues/comments/42"])
        validate.assert_not_called()

    def test_concurrent_duplicate_cleanup_tolerates_already_deleted_targets(self):
        canonical = self.marker_comment(10)
        missing = self.marker_comment(42)
        remaining = self.marker_comment(43)
        for deleted_during in ("lookup", "delete"):
            with self.subTest(deleted_during=deleted_during):
                responses = [canonical, canonical]
                if deleted_during == "delete":
                    responses.append(missing)
                responses.extend([RuntimeError("gh: Not Found (HTTP 404)"), remaining, None])
                with (
                    mock.patch.object(
                        self.sync_pr_preview_comment, "fetch_existing_marker_comment", return_value=canonical
                    ),
                    mock.patch.object(
                        self.sync_pr_preview_comment,
                        "fetch_marker_comments",
                        return_value=[canonical, missing, remaining],
                    ),
                    mock.patch.object(self.sync_pr_preview_comment, "validate_current_head"),
                    mock.patch.object(self.sync_pr_preview_comment, "gh_json", side_effect=responses) as api,
                    redirect_stdout(io.StringIO()),
                ):
                    self.sync_pr_preview_comment.upsert_comment(REPO, 2517, "preview body", "preview-owner", "head123")
                self.assertEqual(
                    api.call_args.args[0], ["api", f"repos/{REPO}/issues/comments/43", "--method", "DELETE"]
                )

    def test_head_advance_during_paginated_lookup_stops_before_marker_mutation(self):
        for existing in (None, self.marker_comment(42)):
            for changed_head in ("remote", "local"):
                with self.subTest(existing=existing, changed_head=changed_head):
                    lookup_finished = False

                    def response(args, existing=existing, changed_head=changed_head):
                        nonlocal lookup_finished
                        endpoint = args[1]
                        if endpoint.endswith("comments?per_page=100&page=1"):
                            return [{"id": 1, "body": "unrelated comment"}]
                        if endpoint.endswith("comments?per_page=100&page=2"):
                            return [existing] if existing else []
                        if endpoint.endswith("comments?per_page=100&page=3"):
                            return []
                        if endpoint == f"repos/{REPO}/issues/comments/42" and len(args) == 2:
                            return existing
                        if endpoint == f"repos/{REPO}/pulls/2517":
                            lookup_finished = True
                            return {"head": {"sha": "advanced456" if changed_head == "remote" else "head123"}}
                        self.fail(f"Unexpected mutation after stale lookup: {args}")

                    with (
                        mock.patch.object(
                            self.sync_pr_preview_comment,
                            "current_head_sha",
                            return_value="advanced456" if changed_head == "local" else "head123",
                        ),
                        mock.patch.object(self.sync_pr_preview_comment, "gh_json", side_effect=response) as api,
                    ):
                        with self.assertRaisesRegex(RuntimeError, re.escape("head changed")):
                            self.sync_pr_preview_comment.upsert_comment(
                                REPO, 2517, "preview body", "preview-owner", "head123"
                            )
                    self.assertTrue(lookup_finished)
                    self.assertFalse(any("--method" in call.args[0] for call in api.call_args_list))

    def test_delete_comment_deletes_only_revalidated_owned_marker(self):
        comment = self.marker_comment(42)
        with (
            mock.patch.object(self.sync_pr_preview_comment, "fetch_marker_comments", return_value=[comment]),
            mock.patch.object(self.sync_pr_preview_comment, "gh_json", side_effect=[comment, None]) as gh_json,
            redirect_stdout(io.StringIO()),
        ):
            self.sync_pr_preview_comment.delete_comment(REPO, 2517, "preview-owner")
        self.assertEqual(
            [call.args[0] for call in gh_json.call_args_list],
            [
                ["api", f"repos/{REPO}/issues/comments/42"],
                ["api", f"repos/{REPO}/issues/comments/42", "--method", "DELETE"],
            ],
        )

    def test_explicit_delete_preserves_foreign_markers_while_removing_own_marker(self):
        owned = self.marker_comment(42)
        foreign = self.marker_comment(10, "someone-else")
        with (
            mock.patch.object(self.sync_pr_preview_comment, "fetch_marker_comments", return_value=[foreign, owned]),
            mock.patch.object(self.sync_pr_preview_comment, "gh_json", side_effect=[owned, None]) as api,
            redirect_stdout(io.StringIO()),
        ):
            self.sync_pr_preview_comment.delete_comment(REPO, 2517, "preview-owner")
        self.assertEqual(api.call_args.args[0], ["api", f"repos/{REPO}/issues/comments/42", "--method", "DELETE"])
        self.assertTrue(all(call.args[0][1] != f"repos/{REPO}/issues/comments/10" for call in api.call_args_list))

    def test_parser_exposes_explicit_delete(self):
        args = self.sync_pr_preview_comment.build_parser().parse_args(["--delete"])
        self.assertTrue(args.delete)
        self.assertFalse(hasattr(args, "delete_missing"))

    def test_missing_local_images_leave_published_previews_untouched(self):
        stderr = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                ["sync_pr_preview_comment.py", "--repo", REPO, "--pr", "2517", "--branch", "codex/example-branch"],
            ),
            mock.patch.object(self.sync_pr_preview_comment, "require_attachment_support"),
            mock.patch.object(self.sync_pr_preview_comment, "list_preview_files", return_value=[]),
            mock.patch.object(self.sync_pr_preview_comment, "gh_json") as gh_json,
            mock.patch.object(self.sync_pr_preview_comment, "upsert_comment") as upsert,
            mock.patch.object(self.sync_pr_preview_comment, "delete_comment") as delete,
            redirect_stderr(stderr),
        ):
            exit_code = self.sync_pr_preview_comment.main()

        self.assertEqual(exit_code, 1)
        self.assertIn("published previews are unchanged", stderr.getvalue())
        gh_json.assert_not_called()
        upsert.assert_not_called()
        delete.assert_not_called()

    def test_unsupported_inferred_repository_host_stops_before_mutations(self):
        stderr = io.StringIO()
        with (
            mock.patch.object(
                sys, "argv", ["sync_pr_preview_comment.py", "--pr", "2517", "--branch", "codex/example-branch"]
            ),
            mock.patch.object(
                self.sync_pr_preview_comment,
                "gh_json",
                return_value={"nameWithOwner": REPO, "url": f"https://enterprise.example/{REPO}"},
            ) as gh_json,
            mock.patch.object(self.sync_pr_preview_comment, "require_attachment_support"),
            mock.patch.object(self.sync_pr_preview_comment, "list_preview_files") as list_files,
            mock.patch.object(self.sync_pr_preview_comment, "upload_preview_files") as upload,
            mock.patch.object(self.sync_pr_preview_comment, "upsert_comment") as upsert,
            mock.patch.object(self.sync_pr_preview_comment, "delete_comment") as delete,
            redirect_stderr(stderr),
        ):
            exit_code = self.sync_pr_preview_comment.main()

        self.assertEqual(exit_code, 1)
        self.assertIn("github.com", stderr.getvalue().lower())
        gh_json.assert_called_once_with(["repo", "view", "--json", "nameWithOwner,url"])
        list_files.assert_not_called()
        upload.assert_not_called()
        upsert.assert_not_called()
        delete.assert_not_called()

    def test_explicit_delete_does_not_require_local_images(self):
        with (
            mock.patch.object(sys, "argv", ["sync_pr_preview_comment.py", "--repo", REPO, "--pr", "2517", "--delete"]),
            mock.patch.object(self.sync_pr_preview_comment, "require_attachment_support"),
            mock.patch.object(self.sync_pr_preview_comment, "gh_json", return_value={"login": "preview-owner"}),
            mock.patch.object(self.sync_pr_preview_comment, "list_preview_files") as list_files,
            mock.patch.object(self.sync_pr_preview_comment, "delete_comment") as delete,
        ):
            exit_code = self.sync_pr_preview_comment.main()

        self.assertEqual(exit_code, 0)
        list_files.assert_not_called()
        delete.assert_called_once_with(REPO, 2517, "preview-owner")

    def test_mismatched_pr_head_prevents_upload(self):
        preview = self.create_preview()
        stderr = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                ["sync_pr_preview_comment.py", "--repo", REPO, "--pr", "2517", "--branch", "codex/example-branch"],
            ),
            mock.patch.object(self.sync_pr_preview_comment, "repo_root", return_value=self.temp_repo_root),
            mock.patch.object(self.sync_pr_preview_comment, "require_attachment_support"),
            mock.patch.object(self.sync_pr_preview_comment, "list_preview_files", return_value=[preview]),
            mock.patch.object(self.sync_pr_preview_comment, "load_capture_metadata", return_value={}),
            mock.patch.object(
                self.sync_pr_preview_comment,
                "gh_json",
                side_effect=[{"id": 123, "permissions": {"push": True}}, {"head": {"sha": "remote123"}}],
            ),
            mock.patch.object(self.sync_pr_preview_comment, "current_head_sha", return_value="local123"),
            mock.patch.object(self.sync_pr_preview_comment, "upload_preview_files") as upload,
            mock.patch.object(self.sync_pr_preview_comment, "upsert_comment") as upsert,
            redirect_stderr(stderr),
        ):
            exit_code = self.sync_pr_preview_comment.main()

        self.assertEqual(exit_code, 1)
        self.assertIn("Local HEAD must match the PR head", stderr.getvalue())
        upload.assert_not_called()
        upsert.assert_not_called()

    def test_main_uploads_native_attachments_and_creates_marker_after_head_recheck(self):
        preview = self.create_preview()
        captures = {BEFORE_PATH: {"head_sha": "capture123", "dirty": False}}
        with (
            mock.patch.object(
                sys,
                "argv",
                ["sync_pr_preview_comment.py", "--repo", REPO, "--pr", "2517", "--branch", "codex/example-branch"],
            ),
            mock.patch.object(self.sync_pr_preview_comment, "repo_root", return_value=self.temp_repo_root),
            mock.patch.object(self.sync_pr_preview_comment, "require_attachment_support"),
            mock.patch.object(self.sync_pr_preview_comment, "list_preview_files", return_value=[preview]),
            mock.patch.object(self.sync_pr_preview_comment, "load_capture_metadata", return_value=captures),
            mock.patch.object(self.sync_pr_preview_comment, "fetch_existing_marker_comment", return_value=None),
            mock.patch.object(
                self.sync_pr_preview_comment, "fetch_marker_comments", return_value=[self.marker_comment(42)]
            ),
            mock.patch.object(self.sync_pr_preview_comment, "current_head_sha", return_value="head123"),
            mock.patch.object(
                self.sync_pr_preview_comment,
                "gh_json",
                side_effect=[
                    {"id": 123, "permissions": {"push": True}},
                    {"head": {"sha": "head123"}, "body": "Existing PR description"},
                    {"login": "preview-owner"},
                    {"url": BEFORE_URL},
                    {"head": {"sha": "head123"}},
                    {"head": {"sha": "head123"}},
                    {"id": 42, "html_url": "https://github.com/comment/42"},
                ],
            ) as gh_json,
            redirect_stdout(io.StringIO()),
        ):
            exit_code = self.sync_pr_preview_comment.main()

        self.assertEqual(exit_code, 0)
        calls = gh_json.call_args_list
        self.assertTrue(calls[3].args[0][1].startswith("https://uploads.github.com/user-attachments/assets?"))
        self.assertEqual(calls[4].args[0], ["api", f"repos/{REPO}/pulls/2517"])
        self.assertEqual(calls[5].args[0], ["api", f"repos/{REPO}/pulls/2517"])
        comment_args = calls[6].args[0]
        self.assertEqual(comment_args[1], f"repos/{REPO}/issues/2517/comments")
        self.assertEqual(comment_args[comment_args.index("--method") + 1], "POST")
        body = json.loads(calls[6].kwargs["input_text"])["body"]
        self.assertIn(self.pr_preview.MARKER_COMMENT, body)
        self.assertIn(BEFORE_URL, body)
        self.assertIn("capture123", body)
        self.assertIn("head123", body)
        self.assertIn(BEFORE_URL, (preview.parent / "attachments.json").read_text())

    def publish_during_recapture(self, *, mutate_cache=False):
        preview = self.create_preview()
        original_digest = self.pr_preview.preview_file_digest(preview)
        capture_path = preview.parent / "captures.json"
        self.pr_preview.write_preview_metadata(
            capture_path,
            {
                BEFORE_PATH: {
                    "sha256": original_digest,
                    "head_sha": "before123",
                    "dirty": False,
                    "source_fingerprint": "a" * 64,
                }
            },
        )

        def gh_response(args, *, input_text=None):
            endpoint = args[1]
            if endpoint == f"repos/{REPO}":
                return {"id": 123, "permissions": {"push": True}}
            if endpoint == f"repos/{REPO}/pulls/2517":
                return {"head": {"sha": "head123"}}
            if endpoint == "user":
                return {"login": "preview-owner"}
            if endpoint.startswith("https://uploads.github.com/user-attachments/assets?"):
                snapshot = Path(args[args.index("--input") + 1])
                self.assertEqual(snapshot.read_bytes(), PNG)
                preview.write_bytes(PNG + b"recaptured")
                self.pr_preview.write_preview_metadata(
                    capture_path,
                    {
                        BEFORE_PATH: {
                            "sha256": self.pr_preview.preview_file_digest(preview),
                            "head_sha": "recapture456",
                            "dirty": True,
                            "source_fingerprint": "b" * 64,
                        }
                    },
                )
                self.assertEqual(snapshot.read_bytes(), PNG)
                return {"url": BEFORE_URL}
            if endpoint == f"repos/{REPO}/issues/2517/comments":
                self.assertIsNotNone(input_text)
                return {"id": 42, "html_url": "https://github.com/comment/42"}
            self.fail(f"Unexpected GitHub request: {args}")

        upload_preview_files = self.sync_pr_preview_comment.upload_preview_files

        def upload_then_mutate_cache(repo, repository_id, preview_files):
            attachments, uploaded_digests = upload_preview_files(repo, repository_id, preview_files)
            if mutate_cache:
                self.pr_preview.write_preview_metadata(
                    preview.parent / "attachments.json",
                    {
                        "repo": repo,
                        "files": {
                            BEFORE_PATH: {
                                "sha256": self.pr_preview.preview_file_digest(preview),
                                "url": BEFORE_URL,
                            }
                        },
                    },
                )
            return attachments, uploaded_digests

        with (
            mock.patch.object(
                sys,
                "argv",
                ["sync_pr_preview_comment.py", "--repo", REPO, "--pr", "2517", "--branch", "codex/example-branch"],
            ),
            mock.patch.object(self.pr_preview, "repo_root", return_value=self.temp_repo_root),
            mock.patch.object(self.sync_pr_preview_comment, "repo_root", return_value=self.temp_repo_root),
            mock.patch.object(self.sync_pr_preview_comment, "require_attachment_support"),
            mock.patch.object(self.sync_pr_preview_comment, "list_preview_files", return_value=[preview]),
            mock.patch.object(self.sync_pr_preview_comment, "fetch_existing_marker_comment", return_value=None),
            mock.patch.object(
                self.sync_pr_preview_comment, "fetch_marker_comments", return_value=[self.marker_comment(42)]
            ),
            mock.patch.object(self.sync_pr_preview_comment, "current_head_sha", return_value="head123"),
            mock.patch.object(self.sync_pr_preview_comment, "gh_json", side_effect=gh_response) as gh_json,
            mock.patch.object(
                self.sync_pr_preview_comment, "upload_preview_files", side_effect=upload_then_mutate_cache
            ),
            redirect_stdout(io.StringIO()),
        ):
            exit_code = self.sync_pr_preview_comment.main()

        self.assertEqual(exit_code, 0)
        comment_body = json.loads(gh_json.call_args.kwargs["input_text"])["body"]
        uploaded = json.loads((preview.parent / "attachments.json").read_text())
        return comment_body, uploaded, original_digest

    def test_recapture_during_upload_preserves_snapshot_and_does_not_mislabel_source(self):
        comment_body, uploaded, original_digest = self.publish_during_recapture()
        self.assertIn(BEFORE_URL, comment_body)
        self.assertIn("Capture revision unavailable.", comment_body)
        self.assertNotIn("recapture456", comment_body)
        self.assertEqual(uploaded["files"][BEFORE_PATH]["sha256"], original_digest)

    def test_mutable_cache_after_upload_cannot_relabel_published_capture_source(self):
        comment_body, uploaded, original_digest = self.publish_during_recapture(mutate_cache=True)
        self.assertNotEqual(uploaded["files"][BEFORE_PATH]["sha256"], original_digest)
        self.assertIn(BEFORE_URL, comment_body)
        self.assertIn("Capture revision unavailable.", comment_body)
        self.assertNotIn("recapture456", comment_body)

    def test_pr_head_changes_during_upload_leave_cached_assets_and_existing_comment(self):
        preview = self.create_preview()
        stderr = io.StringIO()
        with (
            mock.patch.object(
                sys,
                "argv",
                ["sync_pr_preview_comment.py", "--repo", REPO, "--pr", "2517", "--branch", "codex/example-branch"],
            ),
            mock.patch.object(self.sync_pr_preview_comment, "repo_root", return_value=self.temp_repo_root),
            mock.patch.object(self.sync_pr_preview_comment, "require_attachment_support"),
            mock.patch.object(self.sync_pr_preview_comment, "list_preview_files", return_value=[preview]),
            mock.patch.object(self.sync_pr_preview_comment, "load_capture_metadata", return_value={}),
            mock.patch.object(self.sync_pr_preview_comment, "fetch_existing_marker_comment", return_value=None),
            mock.patch.object(
                self.sync_pr_preview_comment, "fetch_marker_comments", return_value=[self.marker_comment(42)]
            ),
            mock.patch.object(self.sync_pr_preview_comment, "current_head_sha", return_value="head123"),
            mock.patch.object(
                self.sync_pr_preview_comment,
                "gh_json",
                side_effect=[
                    {"id": 123, "permissions": {"push": True}},
                    {"head": {"sha": "head123"}},
                    {"login": "preview-owner"},
                    {"url": BEFORE_URL},
                    {"head": {"sha": "advanced456"}},
                ],
            ) as gh_json,
            mock.patch.object(self.sync_pr_preview_comment, "upsert_comment") as upsert,
            redirect_stderr(stderr),
        ):
            exit_code = self.sync_pr_preview_comment.main()

        self.assertEqual(exit_code, 1)
        self.assertIn("head changed during upload", stderr.getvalue())
        self.assertEqual(gh_json.call_count, 5)
        self.assertIn(BEFORE_URL, (preview.parent / "attachments.json").read_text())
        upsert.assert_not_called()
