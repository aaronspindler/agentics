# Test Gap Detection Workflow

Read [repository context](../repository-context.md) and the project guidance before this lane. Commands, authors, default branch, timezone, integrations, path scopes, labels, discussion categories, readiness rules, and legacy marker aliases come from that guidance. This playbook creates no recurring job and grants no Git, GitHub, or live-system write permission by itself. Stop dependent actions when required configuration is missing.


Memory backends, readiness labels, PR-body policy, budgets, and output destinations follow repository guidance. Discussion names and marker schemas below are GitHub-adapter defaults only when that adapter is selected; retain local legacy aliases. A capability described as permitted by this lane still requires current user/host authorization.


TL;DR: Add focused regression coverage for concrete missing-test opportunities outside active PR stabilization.

## Metadata

| Field | Value |
| --- | --- |
| Workflow ID | test-gap-detection |
| Display name | Test Gap Detection |
| Shared guidance | ../automation-guidelines.md |

## Lane Contract

### Repository and ownership scope
- Focus this automation on landed changes, recent branch work not already represented by an open configured-author PR, or concrete missing-test regressions discovered outside active PR stabilization.
- Before choosing work, inspect open same-repository pull requests authored by `CONFIGURED_AUTHOR` and exclude branch heads or commit ranges already under active PR review.
- `pr-guardian` owns test-gap follow-up inside open configured-author same-repository PRs. Do not modify, comment on, or duplicate work already covered by that PR loop.

### Discussion memory
- Discussion title: `Automation Memory - Test Gap Detection`.
- Discussion body must begin with `<!-- automation-memory:id=test-gap-detection -->`.
- Record the last reviewed commit boundary, selected test gap or no-op result, blocker state, and any PR link.

### Execution guardrails
- Keep scope tight to the changed area. Avoid broad refactors, speculative coverage campaigns, or unrelated cleanup.
- Prefer small, reliable tests that fail before and pass after. Favor unit tests for tight logic and integration tests only when the user path requires them.
- Keep edits within the assigned branch and scope. Follow the user/repository checkout strategy; enabled unattended code-changing runs require an isolated worktree.

### Per-run workflow
1. Read the active memory surface, inspect recent landed changes since the last reviewed boundary captured there or the trailing 24 hours when no usable boundary exists, and exclude work already represented by open configured-author PRs.
2. Select up to 5 concrete missing-test opportunities with clear regression surfaces.
3. Partition the selected opportunities into work items: group related gaps only when they cover the same changed area or regression surface, and keep distinctly different gaps in separate work items.
4. For each work item, use the assigned safe workspace/branch under the user's and repository's strategy. Enabled unattended runs use isolated worktrees; manually requested current-checkout work preserves unrelated changes.
5. If missing coverage depends on an unclear failure path, use `$runtime-probe` before broadening into any code-plus-test change.
6. Use `$change-tests` to keep the test work tightly scoped to the selected area.
7. Use `$change-plan` only when a minimal runtime change is required alongside the test to make the regression concrete or correct.
8. Implement the smallest coherent test-only or code-plus-test change in the assigned workspace/branch.
9. If the work crosses the major-change threshold described in the repository standards and the installed `$change-audit` skill, run `$change-audit` before publishing. If that audit surfaces canonical doc drift tied to the change, run `$change-docs` in the same branch.
10. Use `$change-verify` before publishing each test-only or code-plus-test change.
11. Produce `$pr-handoff`, then run `$pr-metadata` to finalize the PR title, body, and labels for each branch.
12. If validation succeeds, open a ready-for-review PR with `$github:yeet` using the `$pr-metadata` title, body, and labels. Use the configured title prefix and existing labels; `Test Gap Detection:` and `automation` are compatible adapter defaults, not new label-creation authority.
13. Record the reviewed boundary, every selected opportunity, grouped work item, outcome, and any PR links through the active memory surface.

### Blocked or unclear cases
- If no concrete missing-test candidate exists, stop without error.
- If overlap with an open PR, missing regression evidence, or unclear behavior prevents a safe change, skip that candidate.
- If validation fails for one work item, do not publish that PR; continue only if the failure is isolated and does not invalidate the remaining selected work.
- Exclude tool-generated or unrelated files from any PR.
- Record a concise no-op or blocker through the active memory surface when the run ends without a PR.

### Execution norms
- Fix up to 5 test-gap items per run, with at most 5 PRs per run.
- Open one PR per distinct missing-test opportunity or coherent related group; do not combine unrelated test gaps into the same PR.
- Stop before the cap when evidence, validation confidence, PR overlap, or time budget makes additional opportunities unsafe.
- Prefer no-op over speculative or over-broad test additions.
- Do not open a PR with partial work, guessed expectations, or unvalidated scope.
