# Merged PR Comment Sweep Workflow

Read [repository context](../repository-context.md) and the project guidance before this lane. Commands, authors, default branch, timezone, integrations, path scopes, labels, discussion categories, readiness rules, and legacy marker aliases come from that guidance. This playbook creates no recurring job and grants no Git, GitHub, or live-system write permission by itself. Stop dependent actions when required configuration is missing.


Memory backends, readiness labels, PR-body policy, budgets, and output destinations follow repository guidance. Discussion names and marker schemas below are GitHub-adapter defaults only when that adapter is selected; retain local legacy aliases. A capability described as permitted by this lane still requires current user/host authorization.


TL;DR: Find unresolved review threads left on merged PRs, then either create deduplicated follow-up issues for high-severity or high-effort work, or open one validated fix PR per merged source PR.

## Metadata

| Field | Value |
| --- | --- |
| Workflow ID | merged-pr-comment-sweep |
| Display name | Merged PR Comment Sweep |
| Shared guidance | ../automation-guidelines.md |

## Lane Contract

### Repository and ownership scope
- Inspect merged pull requests authored by `CONFIGURED_AUTHOR` that targeted the configured default branch, including same-repo and fork-origin PRs, because follow-up work starts from the fetched configured default-branch ref.
- Only handle unresolved review threads on PRs that are already merged. Open PRs remain owned by `pr-guardian` and `pr-reviewer`.
- Treat the merged PR as the source grouping key. Do not combine unresolved comments from multiple source PRs into one follow-up issue, branch, or pull request.
- Use `agentics tools --repo-root PATH pr-threads list-merged-prs --repo OWNER/REPO --author CONFIGURED_AUTHOR --limit 50` to discover candidate merged PRs. Without a reliable cursor, the initial scope is the 50 most recent main-targeted merged PRs. With a cursor, add `--merged-since <YYYY-MM-DD>` using that cursor's date and increase `--limit` whenever the result count reaches the requested limit, until the entire cursor window is discovered. If discovery remains incomplete, retain the previous cursor and record the overflow/blocker for the next run.
- Use `agentics tools --repo-root PATH pr-threads list-unresolved-threads --repo OWNER/REPO --pr <number>` for each candidate with unresolved review threads.

### Markers
- Add this hidden marker to every source review-thread reply made by this lane:
  `<!-- automation-merged-pr-comment-sweep:source-pr=<number>;thread=<thread-id>;action=<issue|fix-pr|resolved|blocked>;target=<url-or-none> -->`
- Add this hidden marker to every issue created or updated by this lane:
  `<!-- automation-merged-pr-comment-sweep:source-pr=<number>;thread=<thread-id>;kind=issue -->`
- Add this hidden marker to every follow-up PR body created by this lane:
  `<!-- automation-merged-pr-comment-sweep:source-pr=<number>;threads=<comma-separated-thread-ids> -->`
- Treat existing live GitHub artifacts with `<!-- codex-merged-pr-comment-sweep:... -->` as legacy lane-owned markers for dedupe and update/retire decisions during the migration. Do not create new legacy markers.
- Follow-up PR titles must start with `Merged PR Comment Sweep:`. Issue titles should start with `[Merged PR follow-up] PR #<number>:` unless updating an existing matching issue.

### Discussion memory
- Discussion title: `Automation Memory - Merged PR Comment Sweep`.
- Discussion body must begin with `<!-- automation-memory:id=merged-pr-comment-sweep -->`.
- Track the last reliable merged-PR cursor, scanned PR numbers and merged SHAs from the `list-merged-prs` `merge_commit_oid` field, represented review-thread IDs, created issue URLs, created follow-up PR URLs, resolved-thread outcomes, skipped stale/no-longer-valid comments, active worker IDs, and blockers.

### Execution guardrails
- The dispatcher must not perform source-PR-specific classification or fixes inline. It discovers candidate merged PRs, dedupes against memory and GitHub markers, then creates one bounded worker per source PR that needs action.
- For each source PR, use exactly one worker/thread titled `Merged PR Comment Sweep: PR #<number>` when the tool supports titles, or as the first line of the worker prompt when it does not.
- Each source-PR worker may classify every unresolved thread on that merged PR, create or update issue tickets, create at most one follow-up fix PR, reply to source review threads, and resolve represented source review threads when safe.
- Code-changing follow-up work must start from the fetched configured default-branch ref in an isolated branch. It must not check out, merge, rebase, force-push, or mutate the already-merged source PR branch.
- Keep fixes small and cohesive. Do not bundle unrelated cleanup, broad refactors, or comments from unrelated source PRs into the same branch.
- Before creating a new issue or PR, search open issues, open PRs, source review-thread comments, and the active memory surface for the exact current or legacy marker or same source PR/thread IDs. Update existing represented work instead of creating duplicates.

### Classification rules
- `resolved/no longer valid`: The the fetched configured default-branch ref implementation already satisfies the review feedback, the thread is obsolete, or the comment was explanation-only and no code or issue follow-up is warranted. Reply with the lane marker and a concise rationale, then resolve the thread when the API permits.
- `ticket follow-up`: The feedback is still relevant but high severity, broad, risky, ambiguous, or high effort. Create or update a GitHub issue instead of editing code. High-severity or high-effort includes security/auth/billing/privacy/deploy risk, destructive migrations, unclear product decisions, cross-cutting architecture, flaky or unreproduced failures, large refactors, and work that cannot be validated with a focused repo-approved command.
- `fix-pr follow-up`: The feedback is still relevant on the fetched configured default-branch ref, low risk, and small enough to fix with a focused validation path. Group all compatible `fix-pr follow-up` threads from the same merged source PR into one branch and one PR.
- If a source PR has both ticket-sized and fix-sized comments, create the issue tickets first, then open one fix PR only for the low-risk compatible subset.

### Issue ticket rules
- Prefer one issue per coherent source-PR follow-up group. Split into multiple issues only when comments describe unrelated domains or validation paths.
- Issue bodies must include the source PR URL, source review-thread/comment URLs, the hidden marker for each represented thread, current-main evidence, severity or effort rationale, acceptance criteria, suggested validation, and known blockers.
- Label issues with `automation` and the most specific existing domain label from the configured label inventory. Add `bug` for correctness, regression, data-loss, security, deploy, or production-risk follow-up. Add `tech-debt` for cleanup, decomposition, maintainability, or testability follow-up.
- After an issue is created or updated and fully represents a review thread, reply to the source review thread with the issue URL and resolve it when the API permits.

### Fix PR rules
- Use `$change-plan` before cross-surface, compatibility-sensitive, migration, deploy, API, template-plus-JS, or workflow-sensitive fixes.
- Use `$change-tests` when the change has a meaningful regression surface.
- Use `$change-verify` with the smallest repo-approved validation command before publishing.
- Use `$pr-handoff`, then `$pr-metadata` before creating the PR. The PR title must start with `Merged PR Comment Sweep:` and the labels must include `automation` plus the most specific existing domain label when GitHub tooling allows it.
- The PR body must include the source PR URL, source review-thread/comment URLs, the PR hidden marker, and whether any threads from the same source PR were represented by issues instead. Report validation evidence in the operator handoff, placing it in the PR body only when repository metadata policy calls for it.
- After a follow-up PR is created and fully represents a review thread, reply to the source review thread with the PR URL and resolve it when the API permits. If PR creation fails after validated local edits, leave the source thread unresolved, record the blocker, and do not repeat the same reply on later runs.

### Per-run workflow
1. Read the active memory surface.
2. Discover recently merged PRs using the cursor-window rules above. Advance the cursor to the newest scanned `merged_at` only after the entire required window (or the initial 50-PR scope) has been discovered and every candidate is classified or durably queued. Include the cursor date on the next scan and dedupe by PR number/merged SHA so same-day merges are not skipped.
3. For each candidate with unresolved review threads, call `list-unresolved-threads` and dedupe against open issues, open PRs, current or legacy source-thread marker replies, and active-memory records. A `blocked` marker/outcome is retryable when its blocking evidence or current main changes; retain it in the durable queue rather than treating it as permanently handled. Do not duplicate an active worker or an existing open follow-up issue/PR.
4. Create one source-PR worker for each remaining PR with actionable unrepresented threads, bounded by the active worker cap. Queue the rest by source PR number, merged SHA from `merge_commit_oid`, and unresolved thread IDs.
5. Each source-PR worker inspects the fetched configured default-branch ref, the original review-thread context, nearby code/tests/docs, existing issues and PRs, and any relevant lane memory before classification.
6. Each source-PR worker applies the classification rules, creates issue tickets for high-severity or high-effort work, implements one grouped low-risk fix PR when warranted, and replies/resolves represented source threads.
7. Each worker returns a structured outcome: source PR number and URL, merged SHA from `merge_commit_oid` if known, thread IDs handled, classification per thread, issue URLs, follow-up PR URL, validation commands and results, review-thread reply/resolve results, blockers, cleanup status, and the exact memory update requested.
8. The dispatcher consumes worker outcomes and writes active-memory updates in order. If memory writes fail, stop launching new workers and include the failure in the run outcome.

### Blocked or unclear cases
- If GitHub auth, memory, spawned-agent/thread tooling, review-thread helper output, or issue/PR search is unavailable, record a blocker and do not create duplicate comments.
- If a review thread cannot be mapped to the fetched configured default-branch ref with enough confidence, create or update a ticket only when the uncertainty itself is actionable; otherwise leave a blocked marker reply and keep the thread unresolved.
- If validation fails for a low-risk fix and a safe repair is unclear, do not publish the PR. Create or update a ticket when the remaining issue is real and actionable; otherwise record the blocker.
- If the source review thread API rejects a reply or resolve operation after an issue or PR was created, record the issue/PR link and API error in memory without retry-spamming the thread.
- If no unrepresented unresolved threads are found, stop without error and record the no-op boundary in memory.
