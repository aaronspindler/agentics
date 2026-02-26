# precommit-agentic-check

`precommit-agentic-check` is an LLM-backed pre-commit gate for staged git changes.

It is designed for monorepos and can be installed as a Python package while remaining isolated in its own project folder.

## What it does

- Reads staged changes (`git diff --cached`) with nearby context.
- Loads a repo-defined policy prompt from `--prompt-file`.
- Calls an LLM provider (`openai` or `anthropic`).
- Enforces a structured JSON pass/fail contract.
- Optionally prints a suggested patch (display-only, never auto-applied).

## Configuration model

Configure behavior in `.pre-commit-config.yaml`:

- `--provider`
- `--model`
- `--prompt-file`
- `--strict`
- optional `--context-lines`, `--max-tokens`

Keep API keys only in environment variables.

## Example `.pre-commit-config.yaml`

```yaml
repos:
  - repo: local
    hooks:
      - id: agentic-check
        name: Agentic Check
        entry: agentic-check
        language: python
        pass_filenames: false
        additional_dependencies:
          - precommit-agentic-check==0.1.0
        args:
          - --provider=openai
          - --model=gpt-4.1-mini
          - --prompt-file=.ai/prompts/precommit_gate.md
          - --strict=error
```

## Environment variables

### OpenAI

- `OPENAI_API_KEY` (required)
- `OPENAI_BASE_URL` (optional)

### Anthropic

- `ANTHROPIC_API_KEY` (required)

### Shared

- `AGENTIC_CHECK_TIMEOUT_SECONDS` (optional)

## CLI

```bash
agentic-check \
  --provider=openai \
  --model=gpt-4.1-mini \
  --prompt-file=.ai/prompts/precommit_gate.md \
  --strict=error
```

## Response contract

The model must return JSON:

```json
{
  "status": "pass|fail",
  "summary": "short text",
  "findings": [
    {
      "severity": "low|medium|high",
      "title": "string",
      "file": "path/or/null",
      "line": 123,
      "reason": "string",
      "recommendation": "string"
    }
  ],
  "suggested_patch": "optional unified diff"
}
```

## Local development

```bash
python3 -m pip install -e ./precommit-agentic-check
python3 -m unittest discover -s precommit-agentic-check/tests -v
```
