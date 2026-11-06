# Automation Orchestrator Workflow

Read [repository context](../repository-context.md) and the project guidance before this lane. Commands, authors, default branch, timezone, integrations, path scopes, labels, discussion categories, readiness rules, and legacy marker aliases come from that guidance. This playbook creates no recurring job and grants no Git, GitHub, or live-system write permission by itself. Stop dependent actions when required configuration is missing.


Memory backends, readiness labels, PR-body policy, budgets, and output destinations follow repository guidance. Discussion names and marker schemas below are GitHub-adapter defaults only when that adapter is selected; retain local legacy aliases. A capability described as permitted by this lane still requires current user/host authorization.


TL;DR: Reference contract for an explicitly requested manual maintenance dispatcher. This package provides no recurring scheduler or host adapter. Reading this file does not start a run or authorize writes; a future scheduler requires separate explicit setup.

## Metadata

| Field | Value |
| --- | --- |
| Workflow ID | automation-orchestrator |
| Display name | Automation Orchestrator |
| Shared guidance | ../automation-guidelines.md |
| Lane index | ../workflow-index.md |

## Scope

This workflow inventories repository maintenance routes, selects eligible work across all lanes, dispatches bounded workers, consumes worker outcomes, and records durable GitHub memory. It may create or update validated PRs, GitHub issues, issue comments, PR comments, and review-thread replies when the relevant lane allows that output.

The orchestrator is dispatcher-only. It must not perform lane-specific implementation, review, triage, docs, digest, marketing, or debt work inline after selecting dispatchable work.

## Startup

- Apply `../automation-guidelines.md#startup` and `../automation-guidelines.md#git-and-worktrees` before dispatching work.
- Acquire the single-run lock at the repository-scoped `automation-orchestrator` run lock before GitHub or git writes, following [shared lock ownership and cleanup](../automation-guidelines.md#run-locks).
- Fetch the configured default branch, inspect the dispatcher checkout path, branch, HEAD SHA, and dirty state, and preserve unrelated changes. Apply the shared Git policy's current-checkout default for manual runs and isolated-worktree requirement for separately configured unattended runs.

## Durable Memory

- Central discussion title: `Automation Memory - Automation Orchestrator`.
- Central discussion body marker: `<!-- automation-memory:id=automation-orchestrator -->`.
- Use central memory to track queue state, active delegated worker IDs, selected work, worker branch/path details, lane cooldowns, blockers, skipped candidates, run summaries, PR links, issue links, and marker/comment follow-up that should not repeat on unchanged state.
- Dedicated lane discussions use `Automation Memory - <Lane Name>` and `<!-- automation-memory:id=<automation-id> -->` for standalone runs.
- Legacy GitHub Discussion posts are not required migration inputs and may have been deleted. Do not fetch `Codex Automation Memory ...` discussions for backward history.
- Before the first dispatch after the scheduler rename, reconcile live GitHub state into `Automation Memory - Automation Orchestrator`: current open automation PRs/issues, unresolved PR review threads, active blocker/status comments, automation-owned branches, and any current or legacy markers found on live GitHub artifacts. Treat that live-state reconciliation as the migration import boundary so already-visible work is not relaunched.
- After the live-state reconciliation is recorded, use `Automation Memory - Automation Orchestrator` as the durable dedupe source for new work. Treat legacy `codex-*` markers found on live PR comments, review comments, issues, or PR bodies as dedupe inputs during migration, but do not create new legacy markers.

## Delegation

- Apply `../automation-guidelines.md#delegation`; it owns worker isolation, host caps, missing-tool behavior, and model/reasoning requirements.
- Per run, perform at most 15 GitHub issue create/update operations across the orchestrator and delegated issue-writing lanes. Exhausting this budget blocks only issue-writing candidates; queue overflow with the candidate key, reason, and next eligible run, then continue evaluating unrelated PR review, docs, digest, Sentry read-only, and code-changing candidates when worker capacity remains.
- Pass each delegated worker a self-contained prompt containing the lane index path, resolved lane Markdown path, assigned work item, relevant live repo/GitHub/Sentry snapshot, central memory excerpt, lane memory excerpt when useful, exact output contract, validation and publishing limits, workspace instructions for the active run mode, and an explicit instruction not to inspect, modify, comment on, or publish unrelated work.
- Record each created worker's ID, agent/tool type, prompt title, assigned work item, lane, initial status, duplicate-prevention key, worker branch, and worktree path in central memory before launching additional duplicate-prone work.

## Route Coverage

- Every heartbeat must build one candidate inventory across urgent reliability, PR review/maintenance, merged PR comment follow-up, debt/simplification/decomposition, Code Health Scout cleanup discovery, feature/backlog, routine lane signals, daily digest, completed-worker outcome consumption, and issue/PR follow-up.
- Evaluate every lane workflow indexed in `../workflow-index.md`, even when the first route has work. Mark each route as dispatched, queued, skipped by cooldown, skipped by duplicate active worker, skipped by cap, or blocked by missing evidence/tooling.
- Priority controls dispatch order, not route coverage. Cadence is a backstop for opportunistic scans, not a hard gate: concrete live evidence, queued central-memory work, changed PR heads, new comments, failing checks, fresh Sentry signals, red default-branch/deploy workflows, or explicit maintainer requests route immediately.
- Exhausting a lane-specific budget blocks only that lane; continue evaluating unrelated lanes when scheduler state and worker capacity allow.

## Run Ordering

1. Bootstrap: read required guidance, verify GitHub auth, acquire the lock, fetch the configured default branch, inspect dispatcher checkout occupancy, reconcile current automation contracts, read central memory, read the host worker-cap config, inspect live repo health, consume completed worker outcomes, and start the all-route candidate inventory.
2. Urgent reliability: prioritize owned same-repo PRs with merge conflicts, [repairable Django migration graph failures](pr-guardian.md#migration-graph-repair), failed or missing expected validation, actionable unresolved review threads, stale blocker comments, or stale `ready-for-human` label state. Also prioritize red default-branch CI, red deploy workflows, deploy follow-up issues, and fresh P0/P1 Sentry groups when available.
3. Progress mandate: before ending, dispatch or write at least one progress action unless blocked by unsafe scheduler state or exhausted worker capacity. Progress means refining an issue, dispatching bounded tech-debt implementation, or dispatching implementation for a clearly scoped issue that passes the project readiness gate.
4. Debt path: prefer existing `tech-debt` issues and deduplicated Code Health Scout output. Legacy Code Quality issues may be consumed only as already-filed tech-debt context. Open ready-for-review PRs only for small, safe, validated simplifications; create or update issues for complex, unclear, broad, auth, billing, security, infrastructure, migration, deploy, or live-ops-sensitive work.
5. Code Health Scout: dispatch at most one combined scout worker per heartbeat for eligible complexity, Desloppify, and code hygiene discovery. Scout output creates or updates issues only; code cleanup happens later through bounded debt workers.
6. Feature/backlog: before selecting issue implementation, apply the repository's documented readiness/acceptance gate. Do not require a particular project field or status unless its owning guidance defines one; otherwise use explicit user-selected scope and concrete acceptance criteria.
7. Routine lanes: evaluate PR Reviewer, Merged PR Comment Sweep, Daily Bug Scan, Test Gap Detection, Docs Cohesion Keeper, Product Marketing Sync, Sentry Daily Triage, Code Health Scout, and Daily Changes Digest according to their lane contracts and fallback cadences.
8. Dispatch eligible work up to the active worker cap and applicable write budgets. Queue overflow in central memory with a reason and next eligible run.
9. Consume worker outcomes, apply memory updates through one ordered write queue, and stop launching new work if central memory writes fail.
10. End with a concise central-memory run summary covering route inventory, progress action, urgent items, lane decisions, PRs/issues touched, blockers, caps reached, and next queued work.

## Blockers

- If GitHub auth, central memory, worker tooling, Sentry access, validation, or live evidence is unavailable, record the blocker in central memory and update the relevant issue or PR marker comment only when useful.
- If an issue or PR already has the same blocker recorded for the same head SHA, Sentry group, issue state, or work item, do not repeat it.
- If work requires a human product decision, production mutation, destructive migration, billing/auth/security judgment, or unbounded refactor, create or refine an issue with concrete next steps instead of editing code.
- Never merge PRs, rebase, force-push, mutate production/live services, or make speculative repo edits.
