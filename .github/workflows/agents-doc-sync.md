---
name: Agents Doc Sync
description: Check for divergence between CLAUDE.md and AGENTS.md; if found, update the file missing information so both stay consistent.
on:
  schedule: daily
  workflow_dispatch:

permissions:
  contents: read
  issues: read
  pull-requests: read

engine: codex

env:
  GH_AW_MODEL_AGENT_CODEX: ${{ vars.GH_AW_MODEL_AGENT_CODEX || '' }}
  GH_AW_MODEL_DETECTION_CODEX: ${{ vars.GH_AW_MODEL_DETECTION_CODEX || '' }}

tools:
  edit:
  bash: true
  github:
    toolsets: [default]

timeout-minutes: 15

safe-outputs:
  create-pull-request:
    title-prefix: "[docs] "
    labels: [documentation, automation]
    draft: false
    expires: 3d
---

# Agents Doc Sync Agent

You keep `CLAUDE.md` and `AGENTS.md` consistent. Both are routers into `.ai/`; they must expose the same structure and references so neither file is missing information.

## Your Mission

1. **Detect divergence** between `CLAUDE.md` and `AGENTS.md`.
2. **Identify which file is missing information** (or is older) and update it so both are consistent.
3. **Create a PR** only if you made edits.

## Task Steps

### 1. Read Both Files

- Read `CLAUDE.md` and `AGENTS.md` in the repository root.
- Parse each into three sections: **Core References** (bulleted list), **Rules** (numbered list; CLAUDE uses "Non-Negotiables", AGENTS uses "Hard Rules"), **Section Router** (bulleted list of anchor links).

### 2. Determine Source of Truth

- Run:
  - `git log -1 --format=%ct -- CLAUDE.md`
  - `git log -1 --format=%ct -- AGENTS.md`
- The file with the **larger timestamp** was modified more recently; treat it as the **source** for this run. If equal, treat CLAUDE.md as source.

### 3. Compare and Find Gaps

For each section (Core References, Rules, Section Router):

- List every item from each section of the **source** file.
- For each item, find an equivalent in the **non-source** file using these matching rules:
  - **Core References**: same `.ai/` path counts as a match (description wording may differ).
  - **Rules**: a match requires covering the **same specific behavioral constraint**, not just the same broad category. Example: "keep files concise" and "update docs for feature changes" both relate to documentation but mandate different behaviors — they are NOT a match.
  - **Section Router**: same anchor link target counts as a match (label wording may differ).
- Any source item with no match in the non-source file is a **gap**.

### 4. Update the File Missing Information

- Edit only the **non-source** file.
- **Core References**: Add any missing bullet so the list matches the source in content (wording may differ for audience: e.g. "AGENTS.md (shared agent rules and router)" in CLAUDE vs "README.md (public overview)" in both).
- **Rules**: Add any missing numbered rule. Preserve the target file's section title ("Non-Negotiables" for CLAUDE, "Hard Rules" for AGENTS). Adapt wording for audience (Claude vs agentic assistants) only where it makes sense; otherwise keep the same text.
- **Section Router**: Add any missing bullet; keep the same link text and anchor. Preserve the target file's heading "Section Router".
- Do **not** remove or reorder existing items; only **add** missing ones so both files are consistent.

### 5. Create Pull Request

- If you made no edits, call the `noop` safe-output tool and exit.
- If you made edits, proceed **without asking for permission** — this is a non-interactive GitHub Actions run. Follow `AGENTS.md` Hard Rule 2: non-interactive runs proceed with required git operations without pausing for approval.
  1. Create a local branch: `git checkout -b docs/agents-sync-$(date +%s)`
  2. Stage the changed file: `git add AGENTS.md` (or whichever file was updated)
  3. Commit: `git commit -m "Sync AGENTS.md: add missing items from CLAUDE.md"`
  4. Call the **create_pull_request** safe-output tool. Title format: "Sync CLAUDE.md and AGENTS.md: added missing [Core References / Rules / Section Router] items from [source file] to [updated file]."

## Guidelines

- Preserve each file's audience: CLAUDE.md is for Claude Code, AGENTS.md is for agentic coding assistants. Wording can differ slightly; content and coverage must align.
- Only add content; do not delete or rephrase existing items except when adding a new rule and renumbering is required.
- Keep both files concise; canonical long-form guidance stays in `.ai/*.md`.
