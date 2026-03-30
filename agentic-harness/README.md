# Agentic Harness

Multi-agent orchestration harness for long-running development tasks. Based on the patterns described in [Harness Design for Long-Running Apps](https://www.anthropic.com/engineering/harness-design-long-running-apps).

## Architecture

Three independent agents orchestrated with **context resets** (no context compaction) and **file-based communication**:

- **Planner** — Expands a task brief into a detailed spec with a sprint contract
- **Generator** — Implements code changes, runs tests, iterates on feedback
- **Evaluator** — Independently reviews changes against the sprint contract (read-only, cannot write files)

```
Task Brief → Planner → spec.json → Generator ↔ Evaluator → result
```

## Install

```bash
pip install -e ./agentics/agentic-harness
```

## Usage

```bash
# Set your API key
export ANTHROPIC_API_KEY=sk-ant-...

# Full workflow
agentic-harness run --brief path/to/brief.md --project provider-payments/

# Plan only
agentic-harness plan --brief-text "Add TIN filtering to statements API" --project provider-payments/

# Resume from existing workspace
agentic-harness generate --workspace .harness/run-20260329-143022/ --project provider-payments/
agentic-harness evaluate --workspace .harness/run-20260329-143022/ --project provider-payments/

# Check status
agentic-harness status --workspace .harness/run-20260329-143022/

# Dry run (no API calls)
agentic-harness run --dry-run --brief-text "Add health check" --project provider-payments/
```

## Configuration

Create a `.harness.yaml` in your project directory (optional — defaults work out of the box):

```yaml
models:
  planner: claude-sonnet-4-20250514
  generator: claude-sonnet-4-20250514
  evaluator: claude-sonnet-4-20250514

orchestration:
  max_iterations: 5
  auto_commit: false

project:
  test_command: poetry run pytest
  lint_command: poetry run pre-commit run --all-files
```

## Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Anthropic API key (required for anthropic provider) |
| `OPENAI_API_KEY` | OpenAI API key (required for openai provider) |
| `AGENTIC_HARNESS_PROVIDER` | Override provider (anthropic/openai) |
| `AGENTIC_HARNESS_MAX_ITERATIONS` | Override max iterations |
| `AGENTIC_HARNESS_TIMEOUT_SECONDS` | Override API call timeout |

## Workspace

Each run creates a workspace directory with all artifacts:

```
.harness/run-20260329-143022/
├── brief.md              # Original task brief
├── spec.json             # Planner output
├── sprint_contract.json  # Definition of done
├── iteration-001/
│   ├── changes.json      # Generator output
│   ├── evaluation.json   # Evaluator grading
│   └── feedback.json     # Feedback for next iteration
├── result.json           # Final outcome
└── harness.log           # Structured log
```

## Key Design Principles

- **Context resets over compaction**: Each agent call is a fresh API call. State passes via JSON files, not in-context history.
- **Generator/Evaluator separation**: The evaluator cannot write files. This prevents self-evaluation bias.
- **Sprint contracts**: Definition of done agreed before code is written. Evaluator grades against it.
- **Zero dependencies**: Uses stdlib HTTP only (no SDK installs needed).
