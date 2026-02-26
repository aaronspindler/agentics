from __future__ import annotations

import io
import unittest
from contextlib import redirect_stderr, redirect_stdout
from unittest.mock import patch

from agentic_check import cli
from agentic_check.providers import ProviderError

PASS_RESPONSE = '{"status":"pass","summary":"clean","findings":[],"suggested_patch":null}'
FAIL_RESPONSE = (
    '{"status":"fail","summary":"issues found","findings":['
    '{"severity":"high","title":"Bug","file":"a.py","line":3,'
    '"reason":"Bad pattern","recommendation":"Fix it"}'
    '],"suggested_patch":null}'
)


class CliTests(unittest.TestCase):
    @patch("agentic_check.cli.generate_response", return_value=PASS_RESPONSE)
    @patch("agentic_check.cli.load_prompt", return_value="policy")
    @patch(
        "agentic_check.cli.collect_staged_payload",
        return_value={"diff": "diff here", "changed_files": ["a.py"], "file_context": []},
    )
    def test_pass_returns_zero(self, *_mocks: object) -> None:
        code = cli.run(
            [
                "--provider=openai",
                "--model=gpt-4.1-mini",
                "--prompt-file=.ai/prompts/precommit_gate.md",
            ]
        )
        self.assertEqual(code, 0)

    @patch("agentic_check.cli.generate_response", return_value=FAIL_RESPONSE)
    @patch("agentic_check.cli.load_prompt", return_value="policy")
    @patch(
        "agentic_check.cli.collect_staged_payload",
        return_value={"diff": "diff here", "changed_files": ["a.py"], "file_context": []},
    )
    def test_fail_returns_one_in_strict_error(self, *_mocks: object) -> None:
        code = cli.run(
            [
                "--provider=anthropic",
                "--model=claude-3-5-sonnet-latest",
                "--prompt-file=.ai/prompts/precommit_gate.md",
                "--strict=error",
            ]
        )
        self.assertEqual(code, 1)

    @patch("agentic_check.cli.generate_response", return_value=FAIL_RESPONSE)
    @patch("agentic_check.cli.load_prompt", return_value="policy")
    @patch(
        "agentic_check.cli.collect_staged_payload",
        return_value={"diff": "diff here", "changed_files": ["a.py"], "file_context": []},
    )
    def test_fail_returns_zero_in_warn_mode(self, *_mocks: object) -> None:
        code = cli.run(
            [
                "--provider=anthropic",
                "--model=claude-3-5-sonnet-latest",
                "--prompt-file=.ai/prompts/precommit_gate.md",
                "--strict=warn",
            ]
        )
        self.assertEqual(code, 0)

    @patch("agentic_check.cli.generate_response", side_effect=ProviderError("network down"))
    @patch("agentic_check.cli.load_prompt", return_value="policy")
    @patch(
        "agentic_check.cli.collect_staged_payload",
        return_value={"diff": "diff here", "changed_files": ["a.py"], "file_context": []},
    )
    def test_runtime_error_returns_zero_in_warn_mode(self, *_mocks: object) -> None:
        stderr = io.StringIO()
        with redirect_stderr(stderr):
            code = cli.run(
                [
                    "--provider=openai",
                    "--model=gpt-4.1-mini",
                    "--prompt-file=.ai/prompts/precommit_gate.md",
                    "--strict=warn",
                ]
            )

        self.assertEqual(code, 0)
        self.assertIn("continuing because --strict=warn", stderr.getvalue())

    @patch("agentic_check.cli.generate_response")
    @patch("agentic_check.cli.load_prompt", return_value="policy")
    @patch(
        "agentic_check.cli.collect_staged_payload",
        return_value={"diff": "", "changed_files": [], "file_context": []},
    )
    def test_no_staged_changes_skips_provider(self, _collect: object, _load: object, generate: object) -> None:
        stdout = io.StringIO()
        with redirect_stdout(stdout):
            code = cli.run(
                [
                    "--provider=openai",
                    "--model=gpt-4.1-mini",
                    "--prompt-file=.ai/prompts/precommit_gate.md",
                ]
            )

        self.assertEqual(code, 0)
        self.assertIn("no staged changes detected", stdout.getvalue())
        generate.assert_not_called()


if __name__ == "__main__":
    unittest.main()
