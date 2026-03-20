from __future__ import annotations

import subprocess
import tempfile
import unittest
from pathlib import Path

from agentic_check.git_input import collect_staged_payload, extract_hunk_ranges


def _run(command: list[str], cwd: str) -> None:
    subprocess.run(command, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


class GitInputTests(unittest.TestCase):
    def test_extract_hunk_ranges(self) -> None:
        diff = """diff --git a/sample.py b/sample.py
index 1111111..2222222 100644
--- a/sample.py
+++ b/sample.py
@@ -1,2 +1,2 @@
-a = 1
+b = 2
 c = 3
"""

        ranges = extract_hunk_ranges(diff)

        self.assertIn("sample.py", ranges)
        self.assertEqual(ranges["sample.py"], [(1, 2)])

    def test_collect_staged_payload_with_context(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            file_path = root / "app.py"

            _run(["git", "init"], cwd=tmp_dir)
            _run(["git", "config", "user.email", "test@example.com"], cwd=tmp_dir)
            _run(["git", "config", "user.name", "Test User"], cwd=tmp_dir)

            file_path.write_text("line1\nline2\nline3\n", encoding="utf-8")
            _run(["git", "add", "app.py"], cwd=tmp_dir)
            _run(["git", "commit", "-m", "init"], cwd=tmp_dir)

            file_path.write_text("line1\nline2 changed\nline3\n", encoding="utf-8")
            _run(["git", "add", "app.py"], cwd=tmp_dir)

            payload = collect_staged_payload(
                context_lines=2,
                max_diff_chars=10_000,
                max_chars_per_file=8_000,
                cwd=tmp_dir,
            )

            self.assertEqual(payload["changed_files"], ["app.py"])
            self.assertIn("line2 changed", payload["diff"])
            self.assertFalse(payload["diff_truncated"])
            self.assertEqual(payload["file_context"][0]["path"], "app.py")
            self.assertTrue(payload["file_context"][0]["snippets"])

    def test_collect_staged_payload_with_no_changes(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            _run(["git", "init"], cwd=tmp_dir)
            _run(["git", "config", "user.email", "test@example.com"], cwd=tmp_dir)
            _run(["git", "config", "user.name", "Test User"], cwd=tmp_dir)

            payload = collect_staged_payload(
                context_lines=2,
                max_diff_chars=10_000,
                max_chars_per_file=8_000,
                cwd=tmp_dir,
            )

            self.assertEqual(payload["changed_files"], [])
            self.assertEqual(payload["diff"], "")


if __name__ == "__main__":
    unittest.main()
