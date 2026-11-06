# Daily Bug Scan Workflow

Read [repository context](../repository-context.md) and the project guidance before this lane. Commands, authors, default branch, timezone, integrations, path scopes, labels, discussion categories, readiness rules, and legacy marker aliases come from that guidance. This playbook creates no recurring job and grants no Git, GitHub, or live-system write permission by itself. Stop dependent actions when required configuration is missing.


Memory backends, readiness labels, PR-body policy, budgets, and output destinations follow repository guidance. Discussion names and marker schemas below are GitHub-adapter defaults only when that adapter is selected; retain local legacy aliases. A capability described as permitted by this lane still requires current user/host authorization.


TL;DR: Find and fix high-confidence landed regressions outside active PR stabilization, one bounded PR per bug group.

## Metadata

| Field | Value |
| --- | --- |
| Workflow ID | daily-bug-scan |
| Display name | Daily Bug Scan |
| Shared guidance | ../automation-guidelines.md |

## Lane Contract

### Repository and ownership scope
- Focus this automation on likely regressions that have already landed on the configured default branch, recent non-PR branch work, or concrete bugs not already covered by an open configured-author PR.
- Before choosing work, inspect open same-repository pull requests authored by `CONFIGURED_AUTHOR` and exclude commit ranges or branch heads already represented by those PRs.
- `pr-guardian` owns bug scanning inside open configured-author same-repository PRs. Do not modify, comment on, or duplicate work already under active PR review.

### Discussion memory
- Discussion title: `Automation Memory - Daily Bug Scan`.
- Discussion body must begin with `<!-- automation-memory:id=daily-bug-scan -->`.
- Record the last reviewed commit boundary, selected candidate or no-op result, blocker state, and any PR link.

### Execution guardrails
- Use only concrete repo evidence such as commit SHAs, file paths, diffs, failing tests, CI signals, or reproduced behavior.
- Do not invent bugs. If the evidence is weak, conflicting, or speculative, skip the candidate.
- Prefer the smallest safe fix for each candidate. Avoid broad refactors, cleanup-only edits, or unrelated multi-item bundles.
- Keep edits within the assigned branch and scope. Follow the user/repository checkout strategy; enabled unattended code-changing runs require an isolated worktree.

### Per-run workflow
1. Read the active memory surface, inspect recent landed changes since the last reviewed boundary captured there or the trailing 24 hours when no usable boundary exists, and exclude ranges already under active PR review.
2. Select up to 5 high-confidence bug candidates supported by concrete repo evidence.
3. Partition the selected candidates into work items: group related bugs only when they share the same failing path or implementation surface, and keep distinctly different bugs in separate work items.
4. For each work item, use the assigned safe workspace/branch under the user's and repository's strategy. Enabled unattended runs use isolated worktrees; manually requested current-checkout work preserves unrelated changes.
5. If the real failing path is still unclear for a work item, use `$runtime-probe` before editing.
6. If a fix touches migrations, startup behavior, deploy workflows, or `infrastructure/`, use `$deploy-safety` before editing that work item.
7. Use `$change-plan` before cross-surface, compatibility-sensitive, or deploy-sensitive fixes.
8. Implement the smallest safe fix for the work item in its assigned workspace/branch.
9. Use `$change-tests` when the fix needs focused regression coverage near the failing path.
10. If the fix crosses the major-change threshold described in the repository standards and the installed `$change-audit` skill, run `$change-audit` before final validation and handoff. If that audit surfaces canonical doc drift tied to the fix, run `$change-docs` in the same branch.
11. Use `$change-verify` before publishing each fix.
12. Produce `$pr-handoff`, then run `$pr-metadata` to finalize the PR title, body, and labels for each branch.
13. If validation succeeds, open a ready-for-review PR with `$github:yeet` using the `$pr-metadata` title, body, and labels. The title must keep the `Daily Bug Scan:` prefix and the label set must include `automation` when the available GitHub tools allow it.
14. Record the reviewed boundary, every selected candidate, grouped work item, outcome, and any PR links through the active memory surface.

### Blocked or unclear cases
- If no high-confidence bug candidate exists, stop without error.
- If overlap with an open PR, missing repo evidence, or an unclear failure path prevents a safe fix for a candidate, skip that candidate.
- If validation fails for one work item, do not publish that PR; continue only if the failure is isolated and does not invalidate the remaining selected work.
- Exclude tool-generated or unrelated files from any PR.
- Record a concise no-op or blocker through the active memory surface when the run ends without a PR.

### Execution norms
- Fix up to 5 bug items per run, with at most 5 PRs per run.
- Open one PR per distinct bug or coherent related group; do not combine unrelated bug fixes into the same PR.
- Stop before the cap when evidence, validation confidence, PR overlap, or time budget makes additional candidates unsafe.
- Prefer no-op over speculative or partially validated changes.
- Do not open a PR with partial work, guessed fixes, or unvalidated scope.
