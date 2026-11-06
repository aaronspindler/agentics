# Docs Cohesion Keeper Workflow

Read [repository context](../repository-context.md) and the project guidance before this lane. Commands, authors, default branch, timezone, integrations, path scopes, labels, discussion categories, readiness rules, and legacy marker aliases come from that guidance. This playbook creates no recurring job and grants no Git, GitHub, or live-system write permission by itself. Stop dependent actions when required configuration is missing.


Memory backends, readiness labels, PR-body policy, budgets, and output destinations follow repository guidance. Discussion names and marker schemas below are GitHub-adapter defaults only when that adapter is selected; retain local legacy aliases. A capability described as permitted by this lane still requires current user/host authorization.


TL;DR: Maintain high-confidence internal repo documentation cohesion with small docs-only PRs.

## Metadata

| Field | Value |
| --- | --- |
| Workflow ID | docs-cohesion-keeper |
| Display name | Docs Cohesion Keeper |
| Shared guidance | ../automation-guidelines.md |

## Lane Contract

### Repository and documentation scope
- Maintain only the human-facing documentation surfaces described below.

### Discussion memory
- Discussion title: `Automation Memory - Docs Cohesion Keeper`.
- Discussion body must begin with `<!-- automation-memory:id=docs-cohesion-keeper -->`.
- Record the selected drift items or no-op result, blocker state, and any PR link.

### Execution guardrails
- This automation maintains human-facing repo docs only. Never edit code, tests, dependency manifests, skill definitions, agent definitions, scheduler adapters, the installed workflow resources, or GitHub issue text.
- Treat `installed skill entrypoints`, `agent definitions.toml`, the installed workflow resources*.md, and relevant app docs under the configured product documentation as source-of-truth inputs when repo docs describe those surfaces.
- Before choosing work, inspect open pull requests and skip any documentation drift already covered by an open PR or active automation PR.

### Per-run workflow
1. Read the active memory surface, then use `$docs-audit` to identify high-confidence internal documentation drift.
2. Select up to 5 high-confidence docs-only maintenance items for the run.
   - Prefer stale workflow references, missing index/router updates, contradictory canonical guidance, duplicated guidance that should be consolidated, or obviously outdated app-doc discoverability.
   - Group related findings into one branch when they improve the same doc surface or router/index cohesion.
   - Split distinctly different documentation drift into separate work items with separate branches and PRs.
   - Skip low-confidence or speculative cleanup.
3. For each work item, use the assigned safe workspace/branch under the user's and repository's strategy. Enabled unattended runs use isolated worktrees; manually requested current-checkout work preserves unrelated changes.
4. If a work item can be completed within the human-facing documentation catalogued by the repository documentation inventory, use `$docs-maintain` to apply the smallest coherent updates across the selected items; skill, custom-agent, and workflow source definitions remain out of scope.
5. Use `$change-verify` on all edited docs once per work item.
6. Produce `$pr-handoff` for each branch, then run `$pr-metadata` to finalize the PR title, body, and labels.
7. Open a ready-for-review PR with `$github:yeet` using the `$pr-metadata` title, body, and labels when the docs-only changes are validated and materially improve clarity or cohesion. Use the configured title prefix and existing labels; `Docs Cohesion Keeper:` and `automation` are compatible adapter defaults, not new label-creation authority.
8. Record every selected drift item, grouped work item, outcome, and any PR links through the active memory surface.

### Blocked or unclear cases
- If no high-confidence docs-only drift exists, stop without error.
- If a fix would require code changes, behavior changes, unresolved product decisions, or edits to tracked skill/agent/automation definitions, skip that candidate.
- If validation fails for one work item, do not publish that PR; continue only if the failure is isolated and does not invalidate the remaining selected work.
- Record a concise no-op or blocker through the active memory surface when the run ends without a PR.

### Execution norms
- Primary goal: improve doc cohesion and consistency across canonical repo docs in each run; prefer one validated PR for a small related batch, and separate PRs for distinctly different drift.
- Fix up to 5 docs items per run, with at most 5 PRs per run.
- Prefer no-op over guessing.
