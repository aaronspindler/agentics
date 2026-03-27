# Agentics

A central repository for reusable configuration, rules, and workflows for AI-powered tools and agents. Everything needed to standardize how AI assistants and automation behave across projects lives here.

## What's Included

- **Claude Rules** — `CLAUDE.md` files and conventions for Claude Code / Claude CLI
- **Codex Rules** — Configuration and instructions for OpenAI Codex agents
- **Cursor Rules** — `.cursorrules` and settings for Cursor IDE
- **GitHub Agentic Workflows** — Reusable `gh aw` workflow definitions
- **GitHub Actions Workflows** — CI/CD workflows that leverage AI agents

## Repository Layout

- `workflows/` — Reusable agentic workflow definitions (for `gh aw`)
- `.github/workflows/` — This repository's own installed/compiled workflows and maintenance jobs
- `precommit-agentic-check/` — Isolated Python subproject for an LLM-backed pre-commit hook

## Subprojects

### precommit-agentic-check

- Purpose: Run an agentic check in pre-commit using staged diff + nearby context.
- Runtime: Python package (`agentic-check` CLI).
- Config surface: model/provider/prompt in `.pre-commit-config.yaml`, credentials via env vars.
- Docs: `precommit-agentic-check/README.md`

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

- Source file: `workflows/agents-doc-sync.md`
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