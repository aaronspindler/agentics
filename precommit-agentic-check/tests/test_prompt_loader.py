from __future__ import annotations

import tempfile
import unittest
from pathlib import Path

from agentic_check.prompt_loader import PromptError, load_prompt


class PromptLoaderTests(unittest.TestCase):
    def test_load_prompt_success(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            path = Path(tmp_dir) / "prompt.md"
            path.write_text("check staged code", encoding="utf-8")

            text = load_prompt("prompt.md", cwd=tmp_dir)

            self.assertEqual(text, "check staged code")

    def test_missing_prompt(self) -> None:
        with tempfile.TemporaryDirectory() as tmp_dir:
            with self.assertRaises(PromptError):
                load_prompt("missing.md", cwd=tmp_dir)


if __name__ == "__main__":
    unittest.main()
