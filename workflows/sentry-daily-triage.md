# Sentry Daily Triage Workflow

Read [repository context](../repository-context.md) and the project guidance before this lane. Commands, authors, default branch, timezone, integrations, path scopes, labels, discussion categories, readiness rules, and legacy marker aliases come from that guidance. This playbook creates no recurring job and grants no Git, GitHub, or live-system write permission by itself. Stop dependent actions when required configuration is missing.


Memory backends, readiness labels, PR-body policy, budgets, and output destinations follow repository guidance. Discussion names and marker schemas below are GitHub-adapter defaults only when that adapter is selected; retain local legacy aliases. A capability described as permitted by this lane still requires current user/host authorization.


TL;DR: Group recent Sentry issues into actionable GitHub issues without mutating Sentry or production state.

## Metadata

| Field | Value |
| --- | --- |
| Workflow ID | sentry-daily-triage |
| Display name | Sentry Daily Triage |
| Shared guidance | ../automation-guidelines.md |

## Lane Contract

### Repository and external systems
- Use the Sentry MCP tools directly for all Sentry reads. Prefer `search_issues` for grouped issue discovery, `get_sentry_resource` for issue detail, and `search_issue_events` or `get_issue_tag_values` only when extra scope evidence is needed. Do not use guessed data, cached results, plugin links, or installed Sentry fallbacks for this automation.
- Query every entry in the configured Sentry project list across all environments for the trailing 24 hours. Treat the project slug as part of every candidate's identity and evidence.
- Do not invoke installed `pr-*`, `change-*`, or `runtime-*` skills for this run; this automation performs Sentry reads and GitHub issue triage only.

### Configured Sentry projects

Load the complete project list from the target repository guidance; an empty or unresolved list blocks this lane.

This configured list is the required full-scan set. A run must query every configured project, including projects that return zero candidates, before it can make any GitHub or memory write. A partial project scan is a blocker, not a successful no-op.

### Discussion memory
- Discussion title: `Automation Memory - Sentry Daily Triage`.
- Discussion body must begin with `<!-- automation-memory:id=sentry-daily-triage -->`.
- Use it to track the last completed scan window, recent non-actionable skip reasons worth remembering, and the latest created or updated GitHub issue links.
- Record the scan window, summary counts, and any issue links.

### Execution guardrails
- Verify Sentry MCP access before any Sentry work with a lightweight read against every configured project. This unattended run must never ask for Sentry credentials interactively or attempt any interactive auth flow. If any configured project is unavailable or unauthorized, stop immediately, name the affected project in a blocker summary, and make no GitHub or memory writes.
- Never create or update pull requests for this automation. This run only creates or updates GitHub issues plus the active memory state.
- Never close GitHub issues automatically.
- Never include auth tokens, PII, IP addresses, email addresses, session identifiers, or full raw stack traces in issue bodies or comments.
- Keep labels minimal. Use GitHub Project fields, issue body metadata, or the hidden automation state for priority and similar classification.

### Per-run workflow
1. Read the active memory surface, then iterate the configured Sentry project list and fetch unresolved issues from the last 24 hours across all environments for each project with the Sentry MCP `search_issues` tool. Record a scan result for projects with zero matches. Before grouping or writing anything, verify that the queried-project set exactly matches the configured-project set; otherwise return a blocker without writes.
2. For each candidate issue, enrich with detail and recent events only when needed to extract:
   - project slug
   - error type or primary exception signature
   - title
   - culprit
   - route or transaction
   - release
   - count
   - first seen
   - last seen
   - top tags or dimensions that help explain scope
3. Normalize a grouping tuple of `category + error signature + culprit_or_route`:
   - lowercase the values
   - trim whitespace
   - collapse repeated whitespace and punctuation into single hyphens
   - remove obviously transient numeric-only ids, UUID-like fragments, and hex-only request identifiers when they would fragment the same root cause
   - if both culprit and route exist, prefer the route when it is a stable user-facing path; otherwise use culprit
4. Categorize each issue into exactly one bucket:
   - `background-job`: worker, cron, queue, Celery, async task, or management command failures
   - `database-cache`: database, ORM, Redis, cache, lock, migration, or connection-pool failures
   - `auth-permissions`: login, session, CSRF, auth, permission, 401, or 403 failures
   - `integration`: third-party API, webhook, payment provider, email provider, or external service failures
   - `performance`: timeout, latency, memory-pressure, or degraded-performance incidents without a clearer bucket above
   - `client-error`: browser or frontend exceptions where the primary failure is client-side
   - `server-error`: server-side request failures or unhandled backend exceptions on user-facing paths
   - `unknown`: anything that does not fit cleanly
5. Form groups only when project slug, category, normalized error signature, and normalized culprit_or_route all align. Keep the group keys and counts project-scoped even when separate backend and frontend groups appear to share a root cause. Those groups may update the same existing GitHub issue only when their category, normalized signature, normalized route or culprit, Sentry short ids, and issue-body evidence genuinely align.
6. Mark a group as non-actionable only when the evidence clearly indicates one of:
   - bot or crawler noise
   - browser-extension pollution
   - expected 4xx misuse or obviously invalid probing traffic
   - a single occurrence with too little context to act on safely
7. Prioritize every actionable group:
   - `p0`: prod outage, login-blocking, payment-blocking, data-loss-looking behavior, or `count >= 50` on a user-facing request path
   - `p1`: any other user-facing prod exception, or `count >= 10`
   - `p2`: all remaining actionable groups
8. Build a deterministic project-scoped group key as `<project-slug>|<category>|<normalized-signature>|<normalized-culprit-or-route>`.
9. Search GitHub issues in `OWNER/REPO` across all states for an existing match in this order:
   - the hidden marker `<!-- sentry-daily-triage:key=<group-key> -->`
   - only for the explicitly configured legacy-marker project, the legacy backend-only marker `<!-- sentry-daily-triage:key=<category>|<normalized-signature>|<normalized-culprit-or-route> -->`; never use this fallback for another project
   - referenced Sentry short ids from the grouped issues
   - a close title and category match supported by the issue body evidence
10. If a match exists, preserve every existing triage marker in the issue body and add the current project-scoped marker when it is absent; this promotes legacy matches and gives each aligned project-scoped group a stable future lookup without discarding history. Then add one concise update comment containing the participating project slugs, fresh 24-hour count, last seen timestamp, release spread, affected Sentry short ids, and any changed priority signal. If the matched issue is closed, prefer commenting on that existing issue rather than creating a duplicate; only reopen it when explicitly desired.
11. If no match exists in any issue state, create one new GitHub issue with:
   - title: `[Sentry][category] concise root-cause summary`
   - labels: `bug` and `automation`
   - body records the priority as `Priority: p0`, `Priority: p1`, or `Priority: p2`; set the GitHub Project `Priority` field when that surface is available
   - body starting with `<!-- sentry-daily-triage:key=<group-key> -->`
   - visible sections using `### Summary`, `### Impact`, `### Sentry Evidence`, `### Representative Events`, `### Recommended Next Step`, and `### References`
   - `<details><summary><b>...</b></summary>` blocks for per-issue or per-event detail
12. When writing the issue body or update comment:
   - summarize participating project slugs, grouped counts, first seen, last seen, release spread, and affected routes or culprits
   - include Sentry short ids and direct Sentry links when available
   - redact or paraphrase sensitive payloads and stack details
   - keep the recommended next step concrete and minimal
13. Compare each project's previously recorded lane-memory groups with the current scan. Count a group as `stale/fixed` for that project only when the referenced Sentry group is resolved or had no activity in the current window, and record which condition applies. This is reporting evidence only; never close the matching GitHub issue automatically.
14. End the run with a concise overall summary plus one row per configured project. The overall summary states:
   - total Sentry issues scanned
   - actionable groups formed
   - GitHub issues created
   - GitHub issues updated
   - groups skipped, with the skip reason

   Each project row records scanned issues, actionable groups, GitHub issues created, GitHub issues updated, groups skipped, and stale/fixed groups. If aligned project-scoped groups update the same GitHub issue, count one update in the overall GitHub action totals and one in each participating project's row; actionable-group totals remain project-scoped.
15. Record the scan window, overall and per-project summary counts, issue links, and any blocker or no-op note through the active memory surface.

### Quality bar
- Prefer merging noisy duplicates into a single GitHub issue when the root cause is genuinely the same.
- Do not merge unrelated failures just because the titles look similar.
- If matching an existing GitHub issue is ambiguous, prefer updating only when the hidden marker or Sentry short ids confirm the relationship; otherwise create a new issue.
- Keep GitHub output concise, readable, and aligned with the repository reporting format.
