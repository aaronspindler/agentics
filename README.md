# Agentics

> CLI tools, slash commands, and workflows that put AI agents to work across the development lifecycle — from code review to long-running feature implementation.

## Subprojects

### claude-commands

> Custom slash commands for Claude Code that automate code review, refinement, design, and PR feedback.

Four commands that handle multi-phase workflows end-to-end:

| Command | What it does |
|---------|-------------|
| `/review <PR>` | Checks out a PR into an isolated worktree, runs lint/tests, performs deep code analysis across 9 severity levels, validates findings against actual code, and produces a numbered findings report. Never commits or pushes. |
| `/refine` | Discovers issues on the current branch (lint, tests, CI failures, PR comments), fixes them in up to 3 rounds, commits, pushes, creates/updates the PR, and watches CI. |
| `/suggest <issues>` | Posts specific findings from a `/review` report as inline PR comments with `suggestion` blocks. Detects stale reviews and deduplicates against existing comments. |
| `/design <brief>` | Explores the codebase, produces a 1-pager design doc with alternatives and comparison matrix, then breaks the solution into sequenced implementation tickets. |

Commands share common config via `shared/pr-commands.md` (argument parsing, project type detection, PR comment fetching) and `shared/design-templates.md` (document structure).

**Install & usage:**

```bash
cd claude-commands && make deploy   # copies to ~/.claude/commands/ and ~/.claude/shared/

# Then in any Claude Code session:
/review 42
/refine
/suggest 1,3
/design "Add patient export API"
```

| Make target | What it does |
|-------------|-------------|
| `make deploy` | Copy commands and shared files to `~/.claude/` |
| `make diff` | Show differences between repo and deployed files |
| `make status` | Check whether deployed files are in sync |

This repo is the source of truth — never edit files directly in `~/.claude/`.

---

### precommit-agentic-check

> LLM-powered pre-commit gate that reviews staged git changes against a policy prompt and returns a structured pass/fail verdict.

Reads your staged diff with surrounding context, sends it to an LLM with a policy prompt, and enforces a JSON response contract (pass/fail, findings with severity/file/line, optional suggested patch). Zero runtime dependencies — uses stdlib HTTP only.

**Install & usage:**

```yaml
# .pre-commit-config.yaml
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
          - --provider=anthropic       # or openai
          - --model=claude-sonnet-4-20250514
          - --prompt-file=.ai/prompts/precommit_gate.md
          - --strict=error             # or warn (continue on LLM failure)
```

Requires `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in the environment. Customize the policy prompt to match your project's standards.

Docs: [`precommit-agentic-check/README.md`](precommit-agentic-check/README.md)

---

### agentic-harness

> Multi-agent orchestration harness for long-running development tasks, based on Anthropic's [Harness Design for Long-Running Apps](https://www.anthropic.com/engineering/harness-design-long-running-apps).

Orchestrates three independent agents — **Planner** (expands a brief into a spec + sprint contract), **Generator** (writes code, runs tests), and **Evaluator** (read-only grading against the contract) — with context resets between each call and file-based handoffs. The evaluator cannot write files, preventing self-evaluation bias. Zero runtime dependencies.

```
Brief → Planner → spec.json → Generator ↔ Evaluator (up to N iterations) → result
```

**Install & usage:**

```bash
pip install -e ./agentic-harness
export ANTHROPIC_API_KEY=sk-ant-...

agentic-harness run --brief-text "Add TIN filtering" --project ../provider-payments/
agentic-harness plan --brief path/to/brief.md --project ../provider-payments/
agentic-harness run --dry-run --brief-text "Add health check" --project ../provider-payments/
```

Auto-detects project type (Poetry, pnpm, Pants, Terraform) and loads `.ai/` docs per agent role. Workspaces are resumable — see [`agentic-harness/README.md`](agentic-harness/README.md) for configuration and workspace details.

---

## GitHub Agentic Workflows

AI-powered workflows authored as markdown with YAML frontmatter, compiled to GitHub Actions via [`gh aw`](https://github.com/github/gh-aw).

**Getting started:**

```bash
gh extension install github/gh-aw   # or: gh extension upgrade gh-aw
gh aw init                           # initialize a repo for agentic workflows
gh aw compile                        # compile .md sources into .lock.yml
```

**Available workflows:**

| Workflow | Summary | Install |
|----------|---------|---------|
| [Agents Doc Sync](#agents-doc-sync) | Keeps `CLAUDE.md` and `AGENTS.md` aligned; opens a PR only when sync changes are needed. | `gh aw add-wizard aaronspindler/agentic_workflows/agents-doc-sync` |

### Agents Doc Sync

Detects divergence between `CLAUDE.md` and `AGENTS.md`, updates the file missing information, and creates a PR only when edits are made.

- **Source**: `.github/workflows/agents-doc-sync.md`
- **Triggers**: daily schedule + manual (`workflow_dispatch`)
- **Engine**: Codex (15-minute timeout)
- **Safe outputs**: PRs prefixed with `[docs]`, labeled `documentation` + `automation`, auto-expire after 3 days

---

## Repository Layout

```
agentics/
├── claude-commands/             # Claude Code slash commands (source of truth)
│   ├── commands/                #   /review, /refine, /suggest, /design
│   ├── shared/                  #   Shared config and templates
│   └── Makefile                 #   deploy, diff, status
├── precommit-agentic-check/     # LLM-backed pre-commit gate (Python package)
│   ├── src/agentic_check/       #   CLI, providers, schema, git input
│   ├── tests/
│   └── .ai/prompts/             #   Policy prompt template
├── agentic-harness/             # Multi-agent orchestration harness (Python package)
│   ├── src/agentic_harness/     #   CLI, agents, providers, tools, orchestrator
│   ├── tests/
│   └── .ai/prompts/             #   Planner, generator, evaluator prompts
├── .github/
│   ├── workflows/               #   Agentic workflow sources (.md) + compiled (.lock.yml)
│   └── agents/                  #   GitHub Copilot agent dispatcher
├── CLAUDE.md                    # Guidance for Claude Code in this repo
├── AGENTS.md                    # Guidance for agentic coding assistants
└── LICENSE                      # MIT
```
