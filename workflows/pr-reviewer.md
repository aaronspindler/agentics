# PR Reviewer Workflow

Read [repository context](../repository-context.md) and the project guidance before this lane. Commands, authors, default branch, timezone, integrations, path scopes, labels, discussion categories, readiness rules, and legacy marker aliases come from that guidance. This playbook creates no recurring job and grants no Git, GitHub, or live-system write permission by itself. Stop dependent actions when required configuration is missing.


Memory backends, readiness labels, PR-body policy, budgets, and output destinations follow repository guidance. Discussion names and marker schemas below are GitHub-adapter defaults only when that adapter is selected; retain local legacy aliases. A capability described as permitted by this lane still requires current user/host authorization.


TL;DR: Run deep read-only PR reviews with one worker per PR/head SHA and deduplicated review comments.

## Metadata

| Field | Value |
| --- | --- |
| Workflow ID | pr-reviewer |
| Display name | PR Reviewer |
| Shared guidance | ../automation-guidelines.md |

## Lane Contract

### Repository and review scope
- Review every open pull request in the repository, including fork PRs. This automation is read-only with respect to code and branches; it may write GitHub review comments only.
- `pr-reviewer` owns deep review and review-comment hygiene. `pr-guardian` owns active fixes, pushes, CI repair, merge-conflict repair, and resolving addressed review threads after fixes.
- Do not edit files, commit, push, merge, rebase, force-push, create branches intended for publication, or open pull requests from this automation.

### Discussion memory
- Discussion title: `Automation Memory - PR Reviewer`.
- Discussion body must begin with `<!-- automation-memory:id=pr-reviewer -->`.
- Track reviewed `<pr-number>@<head-sha>` pairs with the reviewed base ref/SHA, active per-PR review worker/thread IDs, automation-owned finding keys and comment URLs, no-finding outcomes, and any skipped or blocked PRs.
- In standalone runs, a per-PR review worker/thread may append a PR-scoped outcome comment only for its assigned PR, but it must not rewrite the discussion body or edit another PR's records.

### Execution guardrails
- Acquire the single-run lock at the repository-scoped `pr-reviewer` run lock before GitHub writes, following [shared lock ownership and cleanup](../automation-guidelines.md#run-locks).
- The main agent is the dispatcher. It must discover open PRs, create exactly one per-PR review worker/thread per PR/head SHA that needs review, consume outcomes, and serialize memory discussion writes. It must not do PR-specific review work in the dispatcher thread.
- Create each per-PR review worker/thread under the shared delegation rules; dispatcher-thread tasks or helpers do not satisfy the boundary, and additional helpers stay inside the assigned PR worker. Use `PR Reviewer: PR #<number>` as the title when supported, or as the first prompt line, and include the PR number and URL, author, head repository/ref/SHA, base ref/SHA, review-memory excerpt, existing automation finding keys, and the per-PR workflow rules below.
- Create review workers/threads for every open PR, bounded by the active worker cap. Queue remaining PRs and launch the next review worker/thread when a slot frees. Do not combine multiple PRs in one worker/thread.
- If a PR/head SHA already has an active review worker/thread recorded in the memory discussion, do not create a duplicate worker/thread. Re-read or resume that worker/thread when tooling supports it, or record that it is still active.
- Prefer existing CI evidence and code inspection over broad local test runs.

### Required context for each PR
- Read the current PR metadata, title/body, base/head refs and SHAs, author, draft state, changed files, review decision, merge state, checks, and CI summary.
- Read all current PR conversation surfaces before reviewing: top-level issue comments, submitted reviews, review bodies, review comments, resolved and unresolved review threads with every thread comment, existing requested changes, existing approvals, existing `<!-- automation-pr-reviewer` markers, and legacy `<!-- codex-pr-reviewer` markers.
- Use `agentics tools --repo-root PATH pr-threads list-unresolved-threads --repo OWNER/REPO --pr <number>` for unresolved-thread detail, and use GraphQL or `gh api` for resolved threads, submitted reviews, top-level comments, and review comments that the helper does not expose.
- Before posting anything, build a dedupe map of human and automation feedback so the same finding is not repeated.

### Deep-review contract
- This must be a deep review, not a shallow diff skim. Inspect the full diff, full changed files, touched call paths, nearby callers/callees, relevant tests, migrations, API contracts, templates/JS pairs, workflow files, and app-specific docs when the changed area calls for them.
- Use suitable read-only specialists only inside the already-created per-PR worker/thread when they improve coverage: `pr_explorer` for call-path mapping, `reviewer` for correctness/security/regression/deploy risk, `test_gap_explorer` for missing tests, `auditor` for cohesion or docs drift, and design/visual reviewers for visible frontend or product/copy changes.
- For each nontrivial changed surface, identify what would break if the change is wrong, then inspect that path directly.
- Do not report style-only preferences, speculative concerns, or findings already covered by current PR feedback unless you add materially new evidence.
- Prefer fewer high-confidence comments over broad shallow commentary.

### Comment policy
- Use stable finding ids in the form `REVIEW-NNN` in each review outcome for human readability.
- Include a hidden marker in every automation-owned PR review comment or top-level fallback comment:
  `<!-- automation-pr-reviewer:finding=<stable-finding-key>; head=<head-sha> -->`
- Treat existing `<!-- codex-pr-reviewer:... -->` comments as automation-owned legacy reviewer findings during the migration. Use them in the dedupe map, update or retire them when the finding persists or is fixed, and emit only the current `automation-pr-reviewer` marker on new comments.
- Derive `<stable-finding-key>` from the normalized file path, affected symbol or route, risk category, and short finding slug. Keep the same key when a finding persists across a new head SHA.
- Prefer precise inline review comments on the current diff for actionable findings. Use a single top-level marker comment only when the finding cannot be anchored to a current diff line.
- If an existing automation-owned finding still applies, update the existing comment when GitHub permits it; otherwise reply with the revised evidence and do not create a duplicate.
- If an existing automation-owned finding no longer applies, reply once that it appears fixed on the current head and resolve only automation-owned review threads when the API permits safe resolution. Do not resolve human-authored review threads.
- If a human reviewer already made the same point, do not duplicate it. Add a concise reply only when there is important new evidence or a sharper reproduction path.
- If a PR has no findings and no stale automation-owned comments to retire, leave the PR quiet and record the clean review in the memory discussion.
- Never post comments that expose secrets, tokens, private customer data, or unnecessary raw logs.

### Per-run workflow
1. Dispatcher setup:
   - Acquire the single-run lock.
   - Resolve and read the active memory surface.
   - Inventory all open PRs with `gh api --paginate --method GET 'repos/OWNER/REPO/pulls?state=open&per_page=100' --jq '.[] | {number, url: .html_url, head_sha: .head.sha}'`. Complete every page before dispatch; if discovery fails, record the blocker instead of treating partial output as the full queue.
   - Read each PR's current metadata and conversation state required above before deciding whether it needs review.
2. For every open PR, decide whether the current `<pr-number>@<head-sha>` needs a new review worker/thread:
   - Needs review when the head SHA is not recorded as cleanly reviewed, the reviewed base ref/SHA is missing or changed, existing automation findings may need updates, the PR has new human comments/reviews since the last reviewer run, or the prior review worker/thread is missing/blocked.
   - Skip duplicate worker/thread creation when the same head SHA already has an active per-PR review worker/thread in memory.
3. Create exactly one separate worker/thread for each PR needing review, queueing above the active worker cap. Do not begin PR-specific review work until that PR's worker/thread exists.
4. Each per-PR review worker/thread must:
   - Fetch the PR head and base refs read-only, using a temporary worktree when full-file inspection materially improves confidence.
   - Gather the required PR comment/review/thread context before starting the review.
   - Map changed files to touched runtime, test, docs, deploy, and frontend surfaces.
   - Inspect real call paths and relevant tests, not just the diff hunk.
   - Produce a findings-first review report with exact file/line references, severity, confidence, impact, evidence, and duplicate-feedback notes.
   - Immediately before any review-comment write, re-read the PR state, head SHA, base ref/SHA, and relevant feedback for dedupe. Post or update only comments that meet the high-confidence threshold when the PR remains open and that snapshot still matches the reviewed diff. If the head or base changed, stop posting and return `stale-head` or `stale-base` with the old and new snapshot so the dispatcher can queue a fresh review.
   - Avoid code edits and branch mutations entirely.
5. Before returning, re-read the head SHA and base ref/SHA again. If they changed after any comments were posted, report those writes and the stale snapshot; do not record the new snapshot as reviewed or clean.
6. Each per-PR worker/thread returns a structured outcome: PR number, head SHA and base ref/SHA reviewed, worker/thread ID if known, files and surfaces inspected, helper agents used, comments read, findings posted or updated, stale comments retired, no-finding result when applicable, blockers, and the exact memory-discussion update requested.
7. The dispatcher consumes per-PR outcomes as they finish and applies each returned memory update through an ordered discussion write queue. If a memory update fails, stop launching additional review workers/threads and include the failure in the run outcome.

### Blocked cases
- If a PR cannot be fetched or its diff cannot be read, record the blocker in memory and add or update one top-level `<!-- automation-pr-reviewer:blocked -->` PR comment only when the blocker affects review quality and is not already recorded for the same head SHA.
- If GitHub comment APIs fail after a review found issues, record the unposted findings and API error in memory without retry-spamming the PR.
- If a finding depends on an expensive or unavailable validation path, either gather more code evidence or downgrade it to residual risk in memory; do not post low-confidence review noise.
