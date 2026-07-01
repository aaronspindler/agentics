# CLAUDE.md

This repository is the canonical source of truth for Claude Code custom commands and shared reference files. The files here are the master copies; `~/.claude/commands/` and `~/.claude/shared/` are deployment targets.

## Repository Structure

- `commands/` -- Claude Code slash commands (deployed to `~/.claude/commands/`)
  - `review.md` -- Code review engine (`/review`)
  - `refine.md` -- Post-implementation refinement engine (`/refine`)
  - `suggest.md` -- PR suggestion posting engine (`/suggest`)
  - `design.md` -- Design document generator (`/design`)
  - `daily.md` -- Daily GitHub-activity note synthesizer (`/daily`)
  - `ticket.md` -- ClickUp ticket authoring engine (`/ticket`)
- `shared/` -- Shared reference files used by commands (deployed to `~/.claude/shared/`)
  - `pr-commands.md` -- Shared reference for review/refine/suggest
  - `review-rubrics.md` -- Security/architecture/test/debug rubrics for review and refine
  - `checkpoint.md` -- Shared approval-gate protocol for daily and ticket
  - `design-templates.md` -- Templates for design command

## Editing Workflow

1. **Edit files in this repo** -- all changes to commands and shared files should be made here
2. **After editing, deploy** -- run `make deploy` to copy the updated files to `~/.claude/`
3. **Verify sync** -- run `make status` to confirm all files are in sync

## Sync Commands

| Command | What it does |
|---------|-------------|
| `make deploy` | Copy all commands and shared files from this repo to `~/.claude/` |
| `make diff` | Show differences between repo files and deployed files |
| `make status` | Check whether deployed files are in sync with the repo |

## Important Rules

- **This repo is the source of truth.** Do not edit files directly in `~/.claude/commands/` or `~/.claude/shared/`. If you do, pull those changes back into this repo before they are lost.
- **Always run `make deploy` after editing.** Changes in this repo do not take effect until deployed to `~/.claude/`.
- **Path references in commands**: Commands reference shared files using `~/.claude/shared/...` paths. These resolve at Claude Code runtime from the deployed location. Do not change these to repo-relative paths.
- **Cross-file dependencies**: `review.md`, `refine.md`, and `suggest.md` depend on `shared/pr-commands.md`; `review.md` and `refine.md` also use `shared/review-rubrics.md`. The `design.md` command depends on `shared/design-templates.md`. `daily.md` and `ticket.md` depend on `shared/checkpoint.md`. When editing a shared file, consider the impact on all consuming commands.
- **Per-command configuration**: `daily.md` and `ticket.md` open with a `## Configuration` section (vault path / GitHub scope / Obsidian vault name / internal-docs path / org). These are user-specific — keep the committed defaults generic and placeholder-only. Never commit real vault paths, org names, or internal directory names.

## Adding New Commands

1. Create the new `.md` file in `commands/`
2. If the command needs shared reference material, add it to `shared/`
3. Run `make deploy` to install
4. The Makefile uses wildcards (`commands/*.md`, `shared/*.md`) so new files are automatically included
