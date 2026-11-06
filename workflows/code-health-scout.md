# Code Health Scout Workflow

Read [repository context](../repository-context.md) and the project guidance before this lane. Commands, authors, default branch, timezone, integrations, path scopes, labels, discussion categories, readiness rules, and legacy marker aliases come from that guidance. This playbook creates no recurring job and grants no Git, GitHub, or live-system write permission by itself. Stop dependent actions when required configuration is missing.


Memory backends, readiness labels, PR-body policy, budgets, and output destinations follow repository guidance. Discussion names and marker schemas below are GitHub-adapter defaults only when that adapter is selected; retain local legacy aliases. A capability described as permitted by this lane still requires current user/host authorization.


TL;DR: Run the repository cleanup scouts as one issue-triage workflow: complexity hotspots, Desloppify review, and code hygiene reports feed one deduplicated tech-debt issue queue.

## Metadata

| Field | Value |
| --- | --- |
| Workflow ID | code-health-scout |
| Display name | Code Health Scout |
| Supersedes | complexity-ticket-scout, desloppify-scan, code-hygiene-scout |
| Shared guidance | ../automation-guidelines.md |

## Scope

This Markdown file is the single scout workflow contract used by the orchestrator for repo cleanup issue discovery. Shared unattended automation rules live in `../automation-guidelines.md`; this file owns the combined scout scope, output contracts, validation expectations, and blocker behavior.

This lane is issue-triage only. It may gather evidence, write ignored report outputs through the documented scan commands, dedupe findings, create or update GitHub issues, update allowed memory, and return queued follow-up. It must not edit tracked repo files, create branches, push commits, open pull requests, mutate production/live services, or perform cleanup fixes inline.

## Outputs And Markers

Preserve the active issue markers and title prefixes so existing issues, closed regressions, active PRs, and historical lane memory keep deduping correctly.

| Family | Issue title prefix | Hidden marker | Required issue sections |
| --- | --- | --- | --- |
| Complexity | `[Complexity]` | `<!-- complexity-ticket-scout:key=<normalized-key> -->` | `### Summary`, `### Complexity Evidence`, `### Suggested Cleanup`, `### Acceptance Criteria`, `### Validation Notes` |
| Desloppify | `[Desloppify]` | `<!-- desloppify-scan:key=<normalized-key> -->` | `### Summary`, `### Priority`, `### Where`, `### Why It Matters`, `### Recommended Change`, `### Timing`, `### Evidence`, `### Acceptance Criteria`, `### Validation Notes` |
| Code Hygiene | `[Code Hygiene]` | `<!-- code-hygiene-scout:key=<normalized-key> -->` | `### Summary`, `### Evidence`, `### Suggested Cleanup`, `### Acceptance Criteria`, `### Validation Notes` |

Use the repository's existing automation/debt labels and product mappings when its guidance defines them; do not invent missing labels.


## Memory

- Dedicated discussion title for standalone runs: `Automation Memory - Code Health Scout`.
- Dedicated discussion body marker for standalone runs: `<!-- automation-memory:id=code-health-scout -->`.
- Historical dedicated discussions for Code Quality Scout, Complexity Ticket Scout, Desloppify Scan, and Code Hygiene Scout are read-only dedupe inputs; Code Quality is no longer an active scout family.
- Memory updates must record the project-local date, scanned default-branch SHA, eligible families, skipped families, report paths, source snapshots, candidate counts, issues created or updated, blockers, queued overflow candidates, completed family snapshots, and next eligible times.

## Workflow

Follow the lane contract below from startup through evidence gathering, dedupe, issue selection, and outcome handling. When the orchestrator dispatches this lane, use this Markdown file as the lane-specific prompt source and run all eligible scout families inside this one worker.

## Validation

Use `../automation-guidelines.md` plus the family-specific validation commands and gates named below. Do not publish issues, comments, discussions, or memory updates unless the evidence and output rules allow it.

## Blockers

Use the blocked-case and unclear-case rules below. Prefer a no-op, queued follow-up, active-memory blocker, or concise GitHub blocker over speculative writes.

## Lane Contract

### Repository and ownership scope

- Treat GitHub Issues as the canonical backlog and the primary report artifact.
- Run one combined issue-triage pass across complexity, Desloppify, and code hygiene evidence instead of dispatching separate scout workers.
- Treat all findings as issue-scout evidence, not automatic permission to refactor. Code-changing cleanup happens later through bounded debt workers assigned to concrete issues.
- Respect the orchestrator's per-run GitHub issue create/update budget. Standalone runs should also cap writes at 15 total issues/comments across all families.
- Prefer no-op over speculative cleanup tickets. Create or update an issue only when the finding cluster is bounded, high-confidence, and not already covered.
- Do not paste long source excerpts, secrets, tokens, private customer data, unnecessary raw logs, IP addresses, emails, session identifiers, or full stack traces into issues or memory.

### Eligibility and cadence

Use cadence as a fallback for background discovery only. Explicit maintainer requests, queued active-memory follow-up, changed tool evidence, completed selected cleanup tasks that need backlog redisplay, and materially changed source snapshots can run immediately.

| Family | Background cadence | Run when |
| --- | --- | --- |
| Complexity | One completed scout per project-local calendar date | No same-date completed run exists, queued follow-up exists, new complexity evidence justifies a rerun, or an explicit request asks for complexity discovery. |
| Desloppify | One completed whole-repo scan per project-local calendar week | No same-scope scan covers the current default-branch SHA within cadence, the active memory surface queues a refresh, a selected Desloppify issue completes and remaining backlog should be redisplayed, or an explicit request asks for a Desloppify scan. |
| Code Hygiene | One completed scout per default-branch head SHA and tool snapshot; weekly fallback | No same-scope scout covers the current default-branch head SHA within the week, the active memory surface queues hygiene follow-up or overflow, tool output materially changes, or an explicit request asks for a code hygiene scan. |

If no family is eligible after memory, live-state, and explicit-request checks, return a no-op summary that names the next eligible family and time.

### Evidence families

#### Complexity

- Run the configured complexity-report command.
- Write reports to ignored paths such as `.tmp/complexity-hotspots.md` or `/tmp/automation-complexity-hotspots-YYYY-MM-DD.md`. Do not commit report artifacts.
- Build candidates from top functions and files first. Use top systems only to guide grouping; do not create broad system-wide tickets unless the report points to one coherent bounded area.
- Complexity alone is not enough. Inspect enough nearby code, churn, and open PR/issue state to confirm the cleanup target is real and bounded.

#### Desloppify

- Review maintainability, duplication, naming and structure consistency, fragile assumptions, missing error handling, UI/UX rough edges, security or validation issues, dead code, unused files, confusing architecture, and painful future maintenance risks.
- Inspect representative repository structure, recent churn, open issues/PRs, tests, templates, app docs, Code Health Scout report outputs, and existing automation outcomes to avoid stale, duplicated, or already-covered findings.
- Prefer concrete, file-backed items over broad impressions. Each issue must name repo-relative paths, functions, components, workflows, docs surfaces, or issue/PR links that make the cleanup actionable.
- Priorities are `Critical`, `Medium Cleanup`, and `Nice-To-Have Polish`.
- Timing values are `Safe to fix now`, `Fix after <dependency>`, or `Wait for human decision`.

#### Code Hygiene

- Run the configured code-hygiene-report command.
- Inspect the fresh report paths emitted by the configured native command. Do not assume another project's artifact layout or commit report artifacts.
- Build candidates from high-confidence clusters first:
  - dead code or unused file/export/dependency findings from Vulture, Deptry, or Knip
  - duplicated local source modules from jscpd
  - repeated broad Ruff smell-rule findings in the same file or cohesive area
  - diff-cover coverage cliffs only when Cobertura artifacts are present
  - repository-specific static-analysis findings when its report configuration includes them
- Treat absent coverage artifacts as a non-blocking skipped section. Missing tools or configuration required by the selected native report block issue creation from stale data; optional report sections may be explicitly skipped.

### Dedupe and issue writes

1. Determine the current date in the project timezone, the fetched configured default-branch ref commit SHA, current tool/source snapshots, queued follow-up, and explicit request scope.
2. Read the active memory surface and useful historical lane memory before writing. Historical family discussions are dedupe inputs, not new write targets.
3. Build one candidate inventory across all eligible families before creating or updating any issues.
4. Search GitHub issues in `OWNER/REPO` across all states before each write, in this order:
   - the family-specific hidden marker from the Outputs And Markers table
   - for jscpd report findings only, use `identity_paths` for an all-state file-pair search before any title fallback; search each exact repo-relative path and accept a candidate only when its body or evidence identifies the same unordered pair, never from a primary-path-only title match
   - when one exact-pair issue still has a legacy line-derived marker, replace that marker with the finding's canonical `key` during the same update
   - when multiple exact-pair issues collapse to one canonical key, keep the lowest-numbered open issue as canonical; if none are open, apply the closed-regression rule below to the lowest-numbered closed issue; link and close the extras as duplicates or superseded before writing the canonical marker to only the retained issue
   - a close title match for the same file, dependency, rule ID, function, component, route, workflow, or cohesive area
   - open `tech-debt` issues and active PRs that already cover the same path or cleanup scope
5. Before treating the jscpd key migration as complete, independently inventory all-state issues containing the legacy marker prefix `<!-- code-hygiene-scout:key=code-hygiene:jscpd:duplicate:`. Reconcile every issue by exact file-pair evidence even when its duplicate is absent from the current report; a current-report no-match is not migration-completion evidence.
6. Select issue writes across the combined queue, subject to the remaining issue-write budget. Prefer high-confidence complexity plus churn hotspots, Critical Desloppify items, dead-code or dependency-removal hygiene items, and then concrete medium cleanup/polish items.
7. For an existing open matching issue, add one concise update comment only when the new evidence materially changes finding count, scanned SHA, affected paths, priority, rank, scope, or recommended cleanup. Do not spam unchanged issues.
8. For an existing closed matching issue where the problem is present again, either reopen it with current evidence or create a fresh linked issue when reopening would be misleading.
9. If more deduped high-confidence candidates remain after the issue-write budget is exhausted, queue their family, normalized keys, source SHA, priority reason, counts, and next eligible run date in memory. Do not mark that family snapshot complete until the queue is empty or all remaining candidates have recorded skip reasons.
10. If all candidates are already covered, low-confidence, too broad, generated, vendor-like, test-only, intentionally excluded, or blocked by active PR overlap, create no issues for that family and record the no-op reason.
11. Include a final prioritized issue backlog grouped by family and priority, with issue links, plus blockers and next eligible times.

### Blocked or unclear cases

- If GitHub auth, the active memory surface, issue search, issue creation/update, or issue dedupe is unavailable, record the blocker and do not create duplicate or speculative issues.
- If the configured complexity-report command fails, record the command and failure summary and do not create Complexity issues from stale or partial report data.
- If the configured code-hygiene-report command fails before writing a report, record the command and failure summary and do not create Code Hygiene issues from stale report data.
- If the Desloppify scan cannot inspect enough representative code to make useful recommendations, record a partial-scan blocker rather than creating broad issues.
- If a candidate would need product, auth, billing, security, infrastructure, deploy, live-ops, destructive-migration, or human architecture judgment before the cleanup target can be scoped, create or update a higher-level issue only when the concrete decision needed can be stated; otherwise record a blocker and skip it.
- If a selected cleanup issue was completed in another PR, refresh the backlog from the fetched configured default-branch ref, mark that issue completed or superseded in memory when useful, and display the remaining open cleanup issues for the next task selection.
