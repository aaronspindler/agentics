# Agentics

A central repository for reusable configuration, rules, and workflows for AI-powered tools and agents. Everything needed to standardize how AI assistants and automation behave across projects lives here.

## What's Included

- **Claude Rules** — `CLAUDE.md` files and conventions for Claude Code / Claude CLI
- **Codex Rules** — Configuration and instructions for OpenAI Codex agents
- **Cursor Rules** — `.cursorrules` and settings for Cursor IDE
- **GitHub Agentic Workflows** — Reusable `gh aw` workflow definitions
- **GitHub Actions Workflows** — CI/CD workflows that leverage AI agents
- **Claude Commands** — Custom slash commands for Claude Code (`/review`, `/refine`, `/suggest`, `/design`)

## Repository Layout

- `.github/workflows/` — Agentic workflow definitions, compiled lock files, and maintenance jobs
- `precommit-agentic-check/` — Isolated Python subproject for an LLM-backed pre-commit hook
- `agentic-harness/` — Multi-agent orchestration harness for long-running development tasks
- `claude-commands/` — Claude Code custom slash commands and shared reference files

## Subprojects

### precommit-agentic-check

- Purpose: Run an agentic check in pre-commit using staged diff + nearby context.
- Runtime: Python package (`agentic-check` CLI).
- Config surface: model/provider/prompt in `.pre-commit-config.yaml`, credentials via env vars.
- Docs: `precommit-agentic-check/README.md`

### agentic-harness

- Purpose: Orchestrate multi-agent workflows (Planner → Generator ↔ Evaluator) for long-running development tasks across the monorepo.
- Runtime: Python package (`agentic-harness` CLI), zero dependencies.
- Design: Based on [Harness Design for Long-Running Apps](https://www.anthropic.com/engineering/harness-design-long-running-apps) — context resets (not compaction), generator/evaluator separation, file-based handoffs.
- Key features:
  - **Three-agent system**: Planner (spec + sprint contract), Generator (code + tests), Evaluator (read-only grading)
  - **Context resets**: Each agent call is a fresh API call; state passes via JSON workspace files
  - **Project-aware**: Auto-detects project type (Poetry, pnpm, Pants, Terraform) and loads `.ai/` docs per agent role
  - **Resumable**: Workspace artifacts allow resuming from any phase
- Config surface: `.harness.yaml` per project, credentials via env vars (`ANTHROPIC_API_KEY` / `OPENAI_API_KEY`).
- Docs: `agentic-harness/README.md`

```bash
# Install
pip install -e ./agentic-harness

# Full workflow
agentic-harness run --brief-text "Add TIN filtering" --project ../provider-payments/

# Plan only
agentic-harness plan --brief path/to/brief.md --project ../provider-payments/

# Dry run (no API calls)
agentic-harness run --dry-run --brief-text "Add health check" --project ../provider-payments/
```

### claude-commands

Custom slash commands for Claude Code that automate code review, refinement, design, and suggestion workflows.

#### Available Commands

| Command | Purpose |
|---------|---------|
| `/review <PR>` | Checkout a PR into a worktree, run lint/tests, perform deep code analysis, and produce a findings report. Never commits or pushes. |
| `/refine` | Discover issues on the current branch, fix them, commit, update or create a PR, and monitor CI. |
| `/suggest <issues>` | Post specific findings from a `/review` report as inline PR comments. |
| `/design <brief>` | Explore the codebase, produce a 1-pager design doc, then break it into implementation tickets. |

#### Structure

```
claude-commands/
├── commands/           # Slash commands (deployed to ~/.claude/commands/)
│   ├── review.md
│   ├── refine.md
│   ├── suggest.md
│   └── design.md
└── shared/             # Shared reference files (deployed to ~/.claude/shared/)
    ├── pr-commands.md
    └── design-templates.md
```

#### Installation

```bash
cd claude-commands
make deploy
```

This copies commands to `~/.claude/commands/` and shared files to `~/.claude/shared/`, where Claude Code picks them up at runtime.

#### Usage

After deploying, the commands are available as slash commands inside any Claude Code session:

```
/review 42              # Review PR #42
/refine                 # Fix issues on the current branch and update the PR
/suggest 1,3            # Post findings #1 and #3 from a review as PR comments
/design "Add patient export API"   # Generate a design doc and tickets
```

#### Managing Commands

| Make target | What it does |
|-------------|-------------|
| `make deploy` | Copy all commands and shared files to `~/.claude/` |
| `make diff` | Show differences between repo files and deployed files |
| `make status` | Check whether deployed files are in sync with the repo |

**Important**: This repo is the source of truth. Never edit files directly in `~/.claude/commands/` or `~/.claude/shared/` — edit here, then `make deploy`.
## Getting Started with gh aw

1. Install and authenticate GitHub CLI (`gh`).
2. Install the `gh aw` extension:

```bash
gh extension install github/gh-aw
```

If already installed, upgrade to the latest version:

```bash
gh extension upgrade gh-aw
```

3. Initialize your target repository for agentic workflows:

```bash
gh aw init
```

## Available Workflows

| Workflow                            | Summary                                                                                       | Install                                                            |
| ----------------------------------- | --------------------------------------------------------------------------------------------- | ------------------------------------------------------------------ |
| [Agents Doc Sync](#agents-doc-sync) | Keeps `CLAUDE.md` and `AGENTS.md` aligned and opens a PR only when sync changes are required. | `gh aw add-wizard aaronspindler/agentic_workflows/agents-doc-sync` |

## Workflow Details

### Agents Doc Sync

- Source file: `.github/workflows/agents-doc-sync.md`
- Mission: Detect divergence between `CLAUDE.md` and `AGENTS.md`, update the file missing information, and create a PR only when edits are made.
- Triggers:
  - `schedule` (daily)
  - `workflow_dispatch` (manual)
- Permissions: `contents: read`, `issues: read`, `pull-requests: read`
- Engine / timeout: `codex`, `15` minutes
- Tools: `edit`, `bash`, `github` (default toolset)
- Required configuration:
  - Required: none
  - Optional repository variables: `GH_AW_MODEL_AGENT_CODEX`, `GH_AW_MODEL_DETECTION_CODEX`
- Safe output behavior: PR titles are prefixed with `[docs]` , labels include `documentation` and `automation`, and PR expiry is `3d`.

Install:

```bash
gh aw add-wizard aaronspindler/agentic_workflows/agents-doc-sync
```
