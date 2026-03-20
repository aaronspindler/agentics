from __future__ import annotations

import io
import os
import subprocess
import tempfile
import unittest
from contextlib import contextmanager, redirect_stdout
from pathlib import Path
from unittest.mock import patch

from agentic_check import cli


def _run(command: list[str], cwd: str) -> None:
    subprocess.run(command, cwd=cwd, check=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE)


@contextmanager
def _chdir(path: str):
    previous = os.getcwd()
    os.chdir(path)
    try:
        yield
    finally:
        os.chdir(previous)


class IntegrationFlowTests(unittest.TestCase):
    def test_warn_mode_allows_commit_path_on_fail(self) -> None:
        response = (
            '{"status":"fail","summary":"needs fixes","findings":['
            '{"severity":"medium","title":"Naming","file":"app.py","line":2,'
            '"reason":"variable is vague","recommendation":"rename variable"}'
            '],"suggested_patch":"diff --git a/app.py b/app.py"}'
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            root = Path(tmp_dir)
            prompt = root / ".ai" / "prompts" / "precommit_gate.md"
            prompt.parent.mkdir(parents=True, exist_ok=True)
            prompt.write_text("Check for obvious quality risks.", encoding="utf-8")

            app = root / "app.py"

            _run(["git", "init"], cwd=tmp_dir)
            _run(["git", "config", "user.email", "test@example.com"], cwd=tmp_dir)
            _run(["git", "config", "user.name", "Test User"], cwd=tmp_dir)

            app.write_text("value = 1\nprint(value)\n", encoding="utf-8")
            _run(["git", "add", "app.py"], cwd=tmp_dir)
            _run(["git", "commit", "-m", "init"], cwd=tmp_dir)

            app.write_text("value = 1\nprint(value + 1)\n", encoding="utf-8")
            _run(["git", "add", "app.py"], cwd=tmp_dir)

            stdout = io.StringIO()
            with patch("agentic_check.cli.generate_response", return_value=response):
                with _chdir(tmp_dir), redirect_stdout(stdout):
                    code = cli.run(
                        [
                            "--provider=openai",
                            "--model=gpt-4.1-mini",
                            "--prompt-file=.ai/prompts/precommit_gate.md",
                            "--strict=warn",
                        ]
                    )

            output = stdout.getvalue()
            self.assertEqual(code, 0)
            self.assertIn("agentic-check: FAIL", output)
            self.assertIn("suggested patch", output)


if __name__ == "__main__":
    unittest.main()
