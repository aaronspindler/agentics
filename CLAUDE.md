# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

Central repository for reusable AI agent configuration, rules, and workflows. Standardizes how AI assistants and automation behave across projects. No application code — only workflow definitions, agent rules, and configuration.

## Key Commands

### gh aw (Agentic Workflows)

```bash
gh aw init                    # Initialize a repo for agentic workflows
gh aw compile                 # Compile workflow .md → .lock.yml (required before Actions run)
gh aw compile --validate      # Compile with validation
gh aw logs [workflow-name]    # Debug workflow runs
gh aw audit <run-id>          # Audit a specific run
gh aw fix --write             # Fix and recompile (e.g. after Dependabot PRs)
gh aw compile --dependabot    # Recompile for Dependabot dependency updates
```

### precommit-agentic-check (Python subproject)

```bash
# Install locally (editable)
python3 -m pip install -e ./precommit-agentic-check

# Run tests
python3 -m unittest discover -s precommit-agentic-check/tests -v

# Run the CLI directly
agentic-check --provider=openai --model=gpt-4.1-mini --prompt-file=.ai/prompts/precommit_gate.md --strict=error
```

### claude-commands (Claude Code custom commands)

```bash
cd claude-commands
make deploy   # Copy commands and shared files to ~/.claude/
make diff     # Show differences between repo and deployed files
make status   # Check sync state
```

### Pre-commit hooks

```bash
pre-commit run -a   # Run all hooks
```

## Architecture

### Three Subprojects

1. **`.github/workflows/`** — gh aw agentic workflow definitions (markdown → compiled YAML)
2. **precommit-agentic-check/** — Standalone Python package (`agentic-check` CLI) that runs LLM-backed pre-commit checks on staged diffs. Packaged with setuptools, requires Python ≥3.10, published to PyPI on tags matching `precommit-agentic-check-v*`.
3. **claude-commands/** — Claude Code custom slash commands (`/review`, `/refine`, `/suggest`, `/design`) and shared reference files. This repo is the source of truth; files are deployed to `~/.claude/` via `make deploy`.

### Claude Commands

Custom slash commands for Claude Code that automate code review, refinement, design, and suggestion workflows across Pearl's monorepo.

#### Structure

```
claude-commands/
├── CLAUDE.md              # Subproject-specific guidance
├── Makefile               # Deploy, diff, and status targets
├── commands/              # Slash commands (deployed to ~/.claude/commands/)
│   ├── review.md          # /review — Code review engine for PRs
│   ├── refine.md          # /refine — Post-implementation refinement (fix, ship, update PR)
│   ├── suggest.md         # /suggest — Post suggestions from a /review report to a PR
│   └── design.md          # /design — Design document and ticket generator
└── shared/                # Shared reference files (deployed to ~/.claude/shared/)
    ├── pr-commands.md      # Shared config for review/refine/suggest (argument parsing, project detection, style guides)
    └── design-templates.md # 1-pager and ticket templates for /design
```

#### Commands

| Command | Purpose |
|---------|---------|
| `/review <PR>` | Checkout a PR into a worktree, run lint/tests, perform deep code analysis, and produce a findings report. Never commits or pushes. |
| `/refine` | Discover issues on the current branch, fix them, commit, update or create a PR, and monitor CI. |
| `/suggest <issues>` | Post specific findings from a `/review` report as inline PR comments. |
| `/design <brief>` | Explore the codebase, produce a 1-pager design doc, then break it into implementation tickets. |

#### Editing Workflow

1. **Edit files in `claude-commands/`** — this repo is the source of truth
2. **Deploy**: `cd claude-commands && make deploy` — copies files to `~/.claude/`
3. **Verify**: `make status` — confirms all files are in sync

#### Key Rules

- **Never edit `~/.claude/commands/` or `~/.claude/shared/` directly** — edit here, then deploy.
- **Path references**: Commands reference shared files via `~/.claude/shared/...` paths, resolved at Claude Code runtime. Do not change these to repo-relative paths.
- **Cross-file dependencies**: `review.md`, `refine.md`, and `suggest.md` all depend on `shared/pr-commands.md`. `design.md` depends on `shared/design-templates.md`. When editing a shared file, consider impact on all consumers.
- **Adding new commands**: Create a `.md` in `commands/`, optionally add shared material to `shared/`, then `make deploy`. The Makefile uses wildcards so new files are automatically included.

### Workflow Authoring Pipeline

1. **Author** workflow source as markdown with YAML frontmatter in `.github/workflows/`
2. **Compile** with `gh aw compile` to produce `.lock.yml` files in `.github/workflows/`
3. `.lock.yml` files are auto-generated (`linguist-generated=true`, `merge=ours` in `.gitattributes`) — never edit them by hand

### Directory Map

- `.github/workflows/*.md` — Workflow source files (markdown + YAML frontmatter)
- `.github/workflows/*.lock.yml` — Compiled lock files (auto-generated, do not edit)
- `.github/workflows/*.yml` — Non-workflow GitHub Actions (maintenance, copilot setup, precommit CI)
- `.github/agents/` — GitHub Copilot agent definitions (dispatcher for gh-aw prompts)
- `.github/aw/` — `gh aw` action lock metadata (pinned SHAs)
- `precommit-agentic-check/` — Python package for LLM-backed pre-commit gates
- `claude-commands/` — Claude Code custom commands (source of truth, deployed to `~/.claude/`)
- `.vscode/` — VS Code settings and MCP server config for `gh aw mcp-server`

### Workflow File Structure

Each workflow `.md` file has:
- **YAML frontmatter**: `name`, `description`, `on` (triggers), `permissions`, `engine`, `tools`, `timeout-minutes`, `safe-outputs`, optional `env`
- **Markdown body**: Agent instructions (mission, task steps, guidelines)

Supported engines: `copilot`, `claude`, `codex`, or custom.

## Key Conventions

- When creating a workflow, produce exactly **one** `.md` file — do not create separate documentation files
- Workflow lock files (`.lock.yml`) use `merge=ours` strategy; conflicts resolve by recompiling
- Never merge Dependabot PRs that modify generated manifests (`.github/workflows/package.json`, etc.) — update the source `.md` files and rerun `gh aw compile --dependabot`
- Workflow source `.md` files live in `.github/workflows/` — author and edit them there directly.
- The `CLAUDE.md` and `AGENTS.md` files must stay in sync (the `agents-doc-sync` workflow enforces this)
- **claude-commands**: Never edit files directly in `~/.claude/commands/` or `~/.claude/shared/` — edit in this repo, then `make deploy`. Commands reference shared files via `~/.claude/shared/...` paths resolved at runtime.
