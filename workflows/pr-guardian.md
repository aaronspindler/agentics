# PR Guardian Workflow

Read [repository context](../repository-context.md) and the project guidance before this lane. Commands, authors, default branch, timezone, integrations, path scopes, labels, discussion categories, readiness rules, and legacy marker aliases come from that guidance. This playbook creates no recurring job and grants no Git, GitHub, or live-system write permission by itself. Stop dependent actions when required configuration is missing.


Memory backends, readiness labels, PR-body policy, budgets, and output destinations follow repository guidance. Discussion names and marker schemas below are GitHub-adapter defaults only when that adapter is selected; retain local legacy aliases. A capability described as permitted by this lane still requires current user/host authorization.


TL;DR: Stabilize open configured-author same-repo PRs through one worker per PR for conflicts, CI, review threads, readiness labels, and high-confidence PR bug sweeps.

## Metadata

| Field | Value |
| --- | --- |
| Workflow ID | pr-guardian |
| Display name | PR Guardian |
| Shared guidance | ../automation-guidelines.md |

## Lane Contract

### Repository and GitHub scope
- Only operate on open pull requests authored by `CONFIGURED_AUTHOR`.
- Only operate on same-repository pull requests whose head branch also lives in `OWNER/REPO`. Skip forks.
- `pr-guardian` owns active PR stabilization for these PRs: merge-conflict repair, CI follow-up, unresolved review-thread handling, and high-confidence bug scanning inside the PR diff and nearby touched call paths.
- Use `agentics tools --repo-root PATH pr-threads` to enumerate unresolved review threads and to post replies or resolve addressed threads.
- Manage a readiness label only when repository guidance configures one and the current task permits label writes. The compatible GitHub adapter below uses `ready-for-human` as an example; do not create it or impose it on another project.

### Discussion memory
- Discussion title: `Automation Memory - PR Guardian`.
- Discussion body must begin with `<!-- automation-memory:id=pr-guardian -->`.
- Track recently handled `<pr-number>@<head-sha>` pairs with the assessed base ref/SHA, active per-PR fix worker/thread IDs, persistent blockers, and marker-comment or review-thread follow-up. Reassess no-op and blocker outcomes when the base or other blocking evidence changes, even if the head is unchanged.
- In standalone runs, a per-PR fix worker/thread may append a PR-scoped outcome comment only for its assigned PR, but it must not rewrite the discussion body or edit another PR's records.
- As per-PR fix workers/threads report outcomes, the dispatcher must apply any needed memory updates through one ordered write queue for each PR changed, skipped for a blocker, left untouched for a stable no-op, or handed off to an active worker/thread.

### Execution guardrails
- Acquire the single-run lock at the repository-scoped `pr-guardian` run lock before GitHub or git writes, following [shared lock ownership and cleanup](../automation-guidelines.md#run-locks). Use this same path for every Guardian run.
- The single-run lock guards discovery, dispatch, and dispatcher-owned memory writes so overlapping scheduler runs do not create duplicate work. Track active per-PR fix workers/threads through the active memory surface before releasing the lock.
- The main agent is the dispatcher. It must discover eligible PRs, classify them, spawn per-PR workers/threads, consume per-PR outcomes, and serialize memory writes; it must not perform branch-specific fix work in the dispatcher thread.
- For every PR branch classified as needing active work, create exactly one separate worker/thread under the shared delegation rules. Do not combine PR branches, create multiple active workers for the same `<pr-number>@<head-sha>`, or substitute dispatcher-thread helpers; additional helpers stay inside the assigned PR worker. Use `PR Guardian: PR #<number>` as the title when supported, or as the first prompt line, and include the PR number, head/base refs and SHAs, PR URL, memory excerpt, current blocker/status snapshot, and the per-PR workflow rules below.
- Each per-PR fix worker/thread may operate only on its assigned PR branch: fetch that branch, use its assigned branch and the checkout/worktree strategy selected by the user and repository (isolated worktree for enabled unattended runs), write PR-specific marker comments or review-thread replies only for that PR, push only that PR's branch, and clean up only temporary worktrees it created before returning or handing off.
- Never force-push or rebase a PR branch. Only merge the PR base branch into the PR branch when GitHub reports merge conflicts and you are performing a high-confidence conflict-resolution pass in the selected safe workspace. Preserve newer base-branch fixes by default, port the PR's intent onto the current base implementation instead of choosing conflict hunks mechanically, and if the branch still cannot accept a fast-forward push after a validated fix, leave or update one concise top-level PR blocker comment and skip resolving any threads for that PR.
- Keep scope tight. Do not do broad refactors or unrelated cleanup while stabilizing a PR.
- If a fix touches migrations, startup behavior, deploy workflows, or `infrastructure/`, use `$deploy-safety` before editing or pushing.
- If a fix grows into a major change described in the repository standards and the installed `$change-audit` skill, run `$change-audit` before the final validation and push cycle; address only the in-scope findings it surfaces.
- Do not stop merely because one push succeeded. After each push, re-read the PR head, checks, mergeability, and review-thread state once, then keep iterating only while there is actionable work available without waiting on pending CI. If only pending CI remains, hand off the exact pending checks instead of keeping the worker/thread active to poll.

### Top-level PR comment policy
- Use at most one configured-author top-level PR status comment per PR containing the marker `<!-- automation-pr-guardian -->`.
- Treat existing `<!-- codex-pr-guardian -->` comments as legacy PR Guardian status comments during the migration. Update an existing current or legacy marker comment instead of posting a duplicate, and replace the legacy marker with `<!-- automation-pr-guardian -->` when editing that comment.
- Use the marker comment only for blockers, human follow-up, or lower-confidence bug findings that should not be auto-fixed.
- Before posting a new marker comment, inspect existing top-level PR comments for both current and legacy markers and update the existing marker comment instead of posting a duplicate when possible.
- Before repeating a blocker, compare its recorded head/base snapshot and blocking evidence with the current PR and memory discussion; update obsolete blocker records when that evidence changes.
- If the PR is healthy and there is nothing new to report, do not add a top-level status comment.

### `ready-for-human` label gate

Apply this section only when the repository configures this readiness-label contract (or an explicitly mapped equivalent). Otherwise assess readiness without label writes.
- The label means the current PR head is ready for a human to review, not merely that automation made a push or opened the PR.
- Apply `ready-for-human` with `gh pr edit <number> --add-label ready-for-human` only when all of these are true for the current head SHA:
  - GitHub reports the PR is not a draft.
  - The current head has no unresolved actionable review threads. Use `agentics tools --repo-root PATH pr-threads list-unresolved-threads --repo OWNER/REPO --pr <number>` to enumerate unresolved threads, classify every unresolved thread by current-head relevance, and treat unclassified, actionable, or ambiguous threads as blocking. Threads already classified and replied as `explanation only` or `already fixed / no longer valid` may remain unresolved and do not block the label.
  - GitHub review state has no outstanding requested-changes review for the current head. Prefer `reviewDecision` when available; if it is unavailable or ambiguous, inspect the latest review states before labeling.
  - GitHub reports the PR has no merge conflicts with its base branch.
  - The current head's GitHub status rollup has reached a settled successful state for the repo's expected PR validation checks, not just branch-protection-required checks. Use `statusCheckRollup` or `gh pr checks` plus the validation checks defined in the owning CI workflow; failed, cancelled, timed-out, queued, in-progress, action-required, or unjustifiably pending or missing expected validation checks do not qualify. Skipped or neutral conclusions qualify only for checks intentionally skipped by CI scope, such as production/cloudflare jobs that are not expected for the PR diff. Treat pending or missing CI checks as intentionally path-filtered only when every changed path is ignored by the workflow's `pull_request.paths-ignore`, no other expected validation check is active or failed, and the worker has run the repo-approved local validation appropriate for the changed files and records that evidence in the outcome.
  - The PR description is clean and reviewer-ready: it has a concise summary, reviewer-relevant context, no stale blocker/TODO/TBD/scaffold notes, and no contradiction with the current diff. Follow the repository's metadata policy for whether validation evidence belongs in the PR body.
  - If an issue/ticket is discoverable from the PR title, branch name, commit messages, automation memory, or existing issue references, the PR body links it with `Closes #...`, `Fixes #...`, or `References #...` as appropriate. If no ticket is discoverable after checking those sources, do not block the label solely for a missing ticket.
  - There is no current `<!-- automation-pr-guardian -->` marker comment, and no legacy `<!-- codex-pr-guardian -->` marker comment, recording an unresolved blocker for the same head SHA.
- Remove `ready-for-human` with `gh pr edit <number> --remove-label ready-for-human` whenever any gate fails, including after a new push, draft state, outstanding requested-changes review, new unresolved actionable or unclassified review thread, failing, unjustifiably pending, or unjustifiably missing expected validation check, merge conflict, stale PR body, or newly discovered missing ticket link.
- Do not post a top-level PR comment just to say the label was added or removed. Mention label changes only in the structured worker outcome and memory update unless a human-facing blocker comment is already warranted.

### Migration graph repair
- Treat repairable Django migration graph failures on owned same-repo open PRs as urgent PR maintenance.
- When the fix is only stale branch numbering or references, fetch the PR's current base branch, renumber branch-added migrations after that base leaf, and update affected migration `dependencies` and `run_before` references.
- Run the configured migration-graph and backend validation commands from a disposable base-inclusive validation tree before pushing a normal follow-up commit to the assigned PR branch.
- This repair does not authorize merging the base branch, rebasing, or force-pushing. Base-into-head merges remain limited to the explicit merge-conflict path below.
- For destructive schema removal, squashed/replaced chains, intentional pre-base ordering, or other changes needing semantic/deploy-safety review, record the specific blocker in the PR marker comment and active memory instead of auto-editing migrations.

### Per-run workflow
1. Orchestrator setup:
   - Acquire the single-run lock.
   - Resolve and read the active memory surface.
   - List eligible PRs with `agentics tools --repo-root PATH pr-threads list-open-prs --repo OWNER/REPO --author CONFIGURED_AUTHOR`.
2. Triage each eligible PR branch just enough to classify it as `needs per-PR worker/thread`, `healthy no-op`, `unchanged recorded blocker`, or `skip`.
   - Create per-PR workers/threads for branches with merge conflicts, actionable CI failures, actionable unresolved review threads, or high-confidence bug-sweep findings.
   - For clean no-op PRs, apply `ready-for-human` only after the readiness label gate passes. For draft, requested-changes, blocker, pending, conflicted, stale-description, or not-yet-fully-checked PRs, remove `ready-for-human` when present.
   - Skip clean no-ops and recorded blockers only after confirming their head, base, and relevant evidence remain unchanged. A PR/head SHA with an active per-PR fix worker/thread must not receive a second worker; queue any changed-base reassessment for that worker or its completion.
3. Create exactly one new worker/thread for each PR branch classified as `needs per-PR worker/thread`, bounded by the active worker cap. If there are more branches than available worker slots, queue the remaining branches and create the next worker/thread when a slot frees.
4. Give each per-PR fix worker/thread only the assigned PR number, PR URL, head ref, head SHA, base ref/SHA, an immutable snapshot or PR-specific excerpt of the memory discussion, and these per-PR workflow rules. The worker/thread must not list, triage, or modify other PRs or branches.
5. Inside each per-PR fix worker/thread, fetch only the assigned PR head branch from origin and verify the selected workspace targets it. Preserve the user's manual checkout/worktree preference and unrelated changes. For enabled unattended runs, create an isolated temporary worktree/branch from `origin/<head-ref>` using the repository's branch convention.
6. For the assigned PR, read the current head SHA, base ref and base SHA, mergeability or conflict state against the base branch, diff, combined check status, failing check details, and unresolved review-thread state, then compare that snapshot against the supplied memory discussion snapshot before deciding what to do.
7. Decision order for the current head SHA:
   - If GitHub reports the PR is merge-conflicted with its base branch, attempt the merge-conflict-resolution path before CI triage or review-thread handling.
   - If CI failed, inspect the failing GitHub Actions jobs or checks, read the relevant logs, and identify the smallest safe fix. Prefer `gh` or the available GitHub app tools for check-run and log inspection.
   - If CI is still pending or in progress, treat that as useful context rather than a blocker. Do not wait for CI to complete before inspecting review threads, making safe review-thread fixes, or running the PR bug sweep.
   - Inspect unresolved review threads with `agentics tools --repo-root PATH pr-threads list-unresolved-threads --repo OWNER/REPO --pr <number>` regardless of the current CI state, unless merge conflicts blocked safe work on the PR.
8. When GitHub reports the PR is merge-conflicted with its base branch:
   - Fetch `origin/<base-ref>` alongside the head branch and inspect the conflicting files on both sides before editing.
   - Attempt exactly one merge of `origin/<base-ref>` into the local PR branch in the selected safe workspace.
   - Resolve conflicts intentionally: keep newer base-branch fixes by default, port the PR's behavior onto the current base implementation, and update both sides of any touched caller or callee relationship instead of choosing one side wholesale.
   - Use `$change-plan` before cross-surface or deploy-sensitive conflict resolutions.
   - Use `$change-tests` when the resolution changes behavior or reopens a real regression surface.
   - Use `$change-verify` after the conflict resolution is in place.
   - If validation succeeds, create an intentional merge-resolution commit and fast-forward push it back to the existing remote PR branch with `git push origin HEAD:refs/heads/<head-ref>`.
   - If the conflict is ambiguous, requires low-confidence product judgment, touches migrations or deploy-sensitive state without a clear safe answer, or validation cannot be made to pass safely, do not push. Update the marker comment with the specific blocker and return a blocked outcome.
9. When CI failed and the failure is actionable in-repo:
   - Use `$runtime-probe` when you need to pin down the real failure path.
   - Use `$change-plan` before cross-surface or compatibility-sensitive changes.
   - Implement the smallest safe fix in the selected safe workspace.
   - Use `$change-tests` when the fix needs focused regression coverage around the failing path.
   - Use `$change-verify` for lint plus the smallest relevant repo-approved validation command.
   - If validation succeeds, create an intentional commit and fast-forward push it back to the existing remote PR branch with `git push origin HEAD:refs/heads/<head-ref>`.
   - After the push succeeds, re-read PR state and continue the readiness loop instead of stopping.
   - If no safe in-repo CI fix is available and no push was made, record any concrete CI blocker when useful, then continue to review-thread handling and bug scanning for the same head SHA.
10. For any non-conflicted PR head, classify every unresolved review thread as one of:
   - `actionable fix`: the feedback is still correct and needs code or test changes.
   - `explanation only`: no code change is warranted, but the reviewer should get a rationale.
   - `already fixed / no longer valid`: the branch already satisfies the feedback, but do not silently resolve it.
11. For actionable review threads on the same PR:
   - Read the surrounding code and relevant diff context before editing.
   - Group compatible feedback into the smallest safe fix for the current head SHA.
   - Use `$change-plan` before cross-surface or deploy-sensitive fixes.
   - Use `$change-tests` when the behavior change has a real regression surface.
   - Use `$change-verify` after the change is in place.
   - If validation succeeds, create an intentional commit and fast-forward push it back to the existing remote PR branch.
   - After the push succeeds, reply to each addressed thread with a concise summary of the fix plus the validation command, then resolve those addressed threads with `agentics tools --repo-root PATH pr-threads reply-thread --thread-id <thread-id> --body-file <file> --resolve`.
   - Inspect the JSON output from each `reply-thread --resolve` call. If it includes `resolve_error`, treat the reply as already posted, do not rerun the same command for that thread in the same run, leave the thread open, and update the marker comment with the unresolved follow-up.
12. For `explanation only` and `already fixed / no longer valid` threads:
   - Reply with a concise rationale using `agentics tools --repo-root PATH pr-threads reply-thread --thread-id <thread-id> --body-file <file>`.
   - Do not resolve those threads.
13. When there are no remaining actionable review-thread fixes for the current head SHA, run a PR bug sweep even if CI is pending or failed:
   - Use `$pr-review` as a read-only pass when you want a structured risk check on the current head.
   - Inspect the current diff, touched call paths, nearby tests, and obvious edge cases for likely regressions or missing tests.
   - Prefer high-confidence findings only. Do not invent bugs.
   - If you find a high-confidence bug that can be fixed safely, use `$change-plan`, make the smallest safe fix, use `$change-tests` when warranted, run `$change-verify`, create an intentional commit, and fast-forward push the fix.
   - If a finding is plausible but not high-confidence or cannot be validated locally, update the marker comment with the specific concern, concrete evidence, and suggested follow-up; do not push speculative changes.
14. Readiness loop:
   - After each push, review-thread reply, marker-comment update, rerun, or meaningful external-state change, re-read the PR head SHA, base ref/SHA, draft state, mergeability, review decision or latest review state, status rollup and expected PR validation checks, unresolved review threads, and current marker comment.
   - Continue iterating through conflict repair, CI triage for settled failures, review-thread handling, and bug sweep until GitHub shows the PR is not draft, mergeable, expected PR validation checks are settled and successful or explicitly path-filtered with local validation evidence, no requested-changes review is outstanding for the current head, there are no actionable or unclassified unresolved review threads, and the high-confidence bug sweep is clean, or until only pending CI remains.
   - If checks are pending after a fresh push, record the exact pending checks in the outcome and do not mark the PR merge-ready. Do not wait, re-check, or keep the per-PR worker/thread active solely for CI polling unless the operator explicitly asked for monitoring.
   - Use `$pre-pr-gate` or the closest applicable repo-approved validation before declaring a changed PR ready to merge.
   - Apply `ready-for-human` only after the full readiness label gate passes for the final current head. If any gate fails, remove the label when present and include the failing gate in the outcome.
15. Before returning or handing off, each per-PR fix worker/thread must clean up any temporary worktree it created and return a structured outcome containing: PR number, final head SHA, assessed base ref/SHA, created worker/thread ID if known, action taken, whether pushes happened, marker-comment changes, review-thread replies or resolutions, validation commands and results, `ready-for-human` label action, final merge-readiness status, blocker and its evidence if any, cleanup status, and the exact memory-discussion update including that head/base/evidence snapshot. If live refs changed after assessment, report the stale snapshot and queue reassessment rather than recording the new refs as validated.
16. The dispatcher must consume per-PR worker/thread outcomes as they finish and apply each returned memory update through the ordered discussion write queue. If a memory update fails, stop launching additional workers/threads, do not fall back to local memory, and include the failure in the run outcome.

### Blocked cases
- If a PR branch no longer exists, cannot be fetched, or cannot be pushed safely, update the marker comment and skip it.
- If CI fails due to external infrastructure, flaky services, or missing credentials and there is no safe in-repo fix, update the marker comment with the concrete blocker when useful, but continue with review-thread handling and bug scanning for the same head SHA unless another blocker prevents safe work.
- If merge conflicts require low-confidence product judgment or cannot be resolved safely against the current base branch, update the marker comment with the conflicting files and concrete blocker, then skip it.
- If local validation fails and a safe fix is clear, continue iterating locally. If validation cannot be made to pass safely, do not push; update the marker comment with the failing command and blocked scope, then return a blocked outcome.
- If unresolved review-thread data is stale or ambiguous, leave a concise reply on the affected thread explaining what blocked automation and leave it open.
- Do not repeat a thread reply or marker comment while the recorded head/base snapshot and relevant blocking evidence remain unchanged. Reassess changed evidence under the top-level comment policy before updating the existing comment.
