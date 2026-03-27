"""CLI entrypoint for the agentic pre-commit check."""

from __future__ import annotations

import argparse
import json
import os
import sys
from typing import Any

from .git_input import GitInputError, collect_staged_payload
from .prompt_loader import PromptError, load_prompt
from .providers import ProviderError, generate_response
from .schema import SchemaError, parse_model_response

DEFAULT_CONTEXT_LINES = 40
DEFAULT_MAX_TOKENS = 1200
DEFAULT_MAX_DIFF_CHARS = 50_000
DEFAULT_MAX_FILE_CONTEXT_CHARS = 12_000
DEFAULT_TIMEOUT_SECONDS = 30.0

SYSTEM_PROMPT = (
    "You are a deterministic code review gate for git pre-commit. "
    "Return JSON only. Do not include markdown fences or extra narration."
)

RESPONSE_CONTRACT = {
    "status": "pass|fail",
    "summary": "short summary",
    "findings": [
        {
            "severity": "low|medium|high",
            "title": "string",
            "file": "path or null",
            "line": "positive integer or null",
            "reason": "string",
            "recommendation": "string",
        }
    ],
    "suggested_patch": "optional unified diff string",
}


def parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Run LLM-backed pre-commit checks.")
    parser.add_argument("--provider", choices=["openai", "anthropic"], required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--prompt-file", required=True)
    parser.add_argument("--strict", choices=["error", "warn"], default="error")
    parser.add_argument("--context-lines", type=int, default=DEFAULT_CONTEXT_LINES)
    parser.add_argument("--max-tokens", type=int, default=DEFAULT_MAX_TOKENS)
    parser.add_argument("--output-json", action="store_true")
    parser.add_argument("filenames", nargs="*")
    return parser.parse_args(argv)


def _timeout_from_env() -> float:
    raw = os.getenv("AGENTIC_CHECK_TIMEOUT_SECONDS")
    if not raw:
        return DEFAULT_TIMEOUT_SECONDS

    try:
        timeout = float(raw)
    except ValueError:
        return DEFAULT_TIMEOUT_SECONDS

    if timeout <= 0:
        return DEFAULT_TIMEOUT_SECONDS
    return timeout


def _build_user_prompt(custom_prompt: str, payload: dict[str, Any]) -> str:
    return (
        "Apply this repository policy prompt to the staged changes payload.\n\n"
        f"Policy prompt:\n{custom_prompt.strip()}\n\n"
        "You must return a single JSON object that matches this contract exactly:\n"
        f"{json.dumps(RESPONSE_CONTRACT, indent=2)}\n\n"
        "Payload:\n"
        f"{json.dumps(payload, indent=2, ensure_ascii=True)}"
    )


def _print_findings(result: dict[str, Any]) -> None:
    status = result["status"].upper()
    print(f"agentic-check: {status} - {result['summary']}")

    for finding in result["findings"]:
        location = finding.get("file") or "<unspecified>"
        line = finding.get("line")
        location_text = f"{location}:{line}" if line else location
        print(f"[{finding['severity']}] {location_text} - {finding['title']}")
        print(f"  reason: {finding['reason']}")
        print(f"  recommendation: {finding['recommendation']}")

    patch = result.get("suggested_patch")
    if patch:
        print("agentic-check: suggested patch (not applied):")
        print(patch)


def _emit_json(payload: dict[str, Any]) -> None:
    print(json.dumps(payload, indent=2, ensure_ascii=True))


def run(argv: list[str] | None = None) -> int:
    args = parse_args(argv)
    timeout_seconds = _timeout_from_env()

    def handle_error(exc: Exception) -> int:
        message = f"agentic-check: error: {exc}"
        if args.strict == "warn":
            print(f"{message} (continuing because --strict=warn)", file=sys.stderr)
            if args.output_json:
                _emit_json({"status": "warn", "error": str(exc)})
            return 0

        print(message, file=sys.stderr)
        if args.output_json:
            _emit_json({"status": "error", "error": str(exc)})
        return 1

    try:
        prompt = load_prompt(args.prompt_file)
        payload = collect_staged_payload(
            context_lines=args.context_lines,
            max_diff_chars=DEFAULT_MAX_DIFF_CHARS,
            max_chars_per_file=DEFAULT_MAX_FILE_CONTEXT_CHARS,
        )

        if not payload["diff"].strip():
            print("agentic-check: no staged changes detected")
            if args.output_json:
                _emit_json({"status": "pass", "summary": "no staged changes", "findings": []})
            return 0

        user_prompt = _build_user_prompt(prompt, payload)
        raw_response = generate_response(
            provider=args.provider,
            model=args.model,
            system_prompt=SYSTEM_PROMPT,
            user_prompt=user_prompt,
            max_tokens=args.max_tokens,
            timeout_seconds=timeout_seconds,
        )
        result = parse_model_response(raw_response)

        _print_findings(result)
        if args.output_json:
            _emit_json(result)

        if result["status"] == "fail" and args.strict == "error":
            return 1
        return 0

    except (PromptError, GitInputError, ProviderError, SchemaError) as exc:
        return handle_error(exc)


def main() -> None:
    raise SystemExit(run())


if __name__ == "__main__":
    main()
