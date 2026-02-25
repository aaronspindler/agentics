# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Repository Purpose

Central repository for reusable AI agent configuration, rules, and workflows. Standardizes how AI assistants and automation behave across projects. No application code — only workflow definitions, agent rules, and configuration.

## Key Commands

```bash
# Initialize a repo for agentic workflows
gh aw init

# Compile workflow .md files into .lock.yml files (required before workflows run in Actions)
gh aw compile

# Compile with validation
gh aw compile --validate

# Debug workflow runs
gh aw logs [workflow-name]
gh aw audit <run-id>

# Fix and recompile (e.g. after Dependabot PRs)
gh aw fix --write
gh aw compile --dependabot
```

## Architecture

### Workflow Authoring Pipeline

1. **Author** workflow source as markdown with YAML frontmatter in `workflows/` (canonical source)
2. **Mirror** the same `.md` file into `.github/workflows/` (both locations must stay in sync — any add/edit/delete must be applied to both in the same change)
3. **Compile** with `gh aw compile` to produce `.lock.yml` files in `.github/workflows/`
4. `.lock.yml` files are auto-generated (`linguist-generated=true`, `merge=ours` in `.gitattributes`) — never edit them by hand

### Directory Map

- `workflows/` — Canonical workflow source files (markdown + YAML frontmatter)
- `.github/workflows/*.md` — Mirrored copies of workflow source files (must match `workflows/`)
- `.github/workflows/*.lock.yml` — Compiled lock files (auto-generated, do not edit)
- `.github/workflows/*.yml` — Non-workflow GitHub Actions (maintenance, copilot setup)
- `.github/agents/` — GitHub Copilot agent definitions
- `.github/aw/` — `gh aw` action lock metadata
- `.ai/plans/` — Planning documents for proposed changes
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
- Before compiling or committing, diff-review staged changes to confirm every workflow source add/edit/delete in `workflows/` has a matching change in `.github/workflows/` (and vice-versa). If either side is missing, fix it before proceeding.
- The `CLAUDE.md` and `AGENTS.md` files must stay in sync (the `agents-doc-sync` workflow enforces this)
