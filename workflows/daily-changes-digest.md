# Daily Change Summary Workflow

Read [repository context](../repository-context.md) and the project guidance before this lane. Commands, authors, default branch, timezone, integrations, path scopes, labels, discussion categories, readiness rules, and legacy marker aliases come from that guidance. This playbook creates no recurring job and grants no Git, GitHub, or live-system write permission by itself. Stop dependent actions when required configuration is missing.


Memory backends, readiness labels, PR-body policy, budgets, and output destinations follow repository guidance. Discussion names and marker schemas below are GitHub-adapter defaults only when that adapter is selected; retain local legacy aliases. A capability described as permitted by this lane still requires current user/host authorization.


TL;DR: Publish exactly one dated maintainer summary discussion for the previous project-local calendar day.

## Metadata

| Field | Value |
| --- | --- |
| Workflow ID | daily-changes-digest |
| Display name | Daily Change Summary |
| Shared guidance | ../automation-guidelines.md |

## Lane Contract

### Repository and external systems
- This automation is reporting-only. Never edit repo files, branches, pull requests, GitHub issues, GitHub issue comments, Dokploy state, or Sentry state.
- Use GitHub as the source of truth for pull requests, issues, workflow and deploy signals, and GitHub Discussions reads and writes.
- Discover the repository's configured read-only Sentry connector/API and verify access with a lightweight read. Managed connector access does not require a shell token.
- Post the report to the existing GitHub Discussions category with slug `daily` (the configured repository daily discussion category).
- The reporting window is the previous local calendar day in the project timezone as a half-open interval: `[00:00:00 for that date, 00:00:00 for the next local date)`. Convert both bounds to UTC when querying GitHub or Sentry APIs.

### Execution guardrails
- If no configured read-only Sentry access is available, continue with GitHub-only reporting and record the gap in `## Notes / Data Gaps`; do not request credentials or reconfigure access during the digest.
- Never create a second discussion for the same report date. Reuse the existing discussion when the exact title or the body marker already exists.
- If the matching discussion exists but cannot be updated safely because it is locked, missing required permissions, or otherwise non-editable, stop without creating a duplicate.
- Do not duplicate live deploy verification. Use GitHub workflow and deployment evidence plus any existing deploy follow-up issues.

### Discussion contract
- Title format: `Daily Change Summary - YYYY-MM-DD`, where the date is the previous local date in the project timezone.
- The discussion body must begin with `<!-- daily-changes-digest:date=YYYY-MM-DD -->`.
- The dated daily discussion is the standalone history and dedupe surface as well as the required report output. Under orchestrator dispatch, central orchestrator memory remains the active memory surface.
- The body must contain these sections in order:
  - `## TL;DR`
  - `## Needs Your Attention`
  - `## Merged / Shipped`
  - `## Tickets Created`
  - `## Tickets Closed`
  - `## New Bugs`
  - `## Deploys`
  - `## Notes / Data Gaps`
- Always emit every listed section header in that exact order. If a section has nothing to report, include the header and a single line containing `None`.
- Quiet days still create or update the dated discussion. On a quiet day, keep `## TL;DR` concise, make `## Needs Your Attention` explicitly state that nothing urgent needs review, and use `None` for any other section with no items.

### Per-run workflow
1. Determine the report date and exact UTC query window for the previous local day in the project timezone, using the half-open interval `[local 00:00:00, next local 00:00:00)`.
2. Resolve the `daily` discussion category id from the repository before any write.
3. Search existing repository discussions for either:
   - the exact title `Daily Change Summary - YYYY-MM-DD`, or
   - the body marker `<!-- daily-changes-digest:date=YYYY-MM-DD -->`.
4. Gather GitHub activity inside the window:
   - pull requests merged into the repository during the window
   - open pull requests that currently need attention because they have failing checks, requested review changes, merge conflicts, or other concrete blockers, but only include them when they changed during the window or the blocking signal first appeared during the window
   - GitHub issues created during the window
   - GitHub issues closed during the window
   - GitHub issues created during the window with the `bug` label
   - automation-created blocker issues created or updated during the window when they imply maintainer follow-up, including `deploy-verifier`, `sentry-daily-triage`, and similar reporting issues
   - `cd.yml` workflow runs or equivalent production deploy workflow results that completed during the window
5. Gather Sentry signals only when credentials are available:
   - newly seen or materially spiking issue groups whose first seen or high-signal activity falls inside the window
   - prefer high-signal groups only: production incidents, auth or payment blockers, deploy-correlated spikes, or groups with enough event volume to likely need human triage
   - if a matching GitHub issue from `sentry-daily-triage` already exists, prefer linking to that issue as the stable artifact instead of repeating raw event detail
6. Build `## Needs Your Attention` from actionable blockers only. Include:
   - open pull requests with failing checks, requested changes, merge conflicts, or other clear blockers
   - deploy outcomes that failed or need warning-level follow-up
   - new high-signal Sentry incidents or new GitHub bug issues that likely require maintainer triage
   - fresh automation-created blocker issues that point to real follow-up work
   - do not turn this section into a full activity dump
7. Build the remaining sections:
   - `## TL;DR`: a short dated summary of the day, including counts for merged pull requests, tickets created and closed, new bugs, deploy results, and whether attention items exist
   - `## Merged / Shipped`: merged pull requests from the window, plus shipped-to-production notes when GitHub deploy evidence clearly ties a deployed SHA back to a merged pull request
   - `## Tickets Created`: GitHub issues created in the window, excluding pull requests
   - `## Tickets Closed`: GitHub issues closed in the window, excluding pull requests
   - `## New Bugs`: newly opened GitHub bug issues and new high-signal Sentry issues first seen in the window
   - `## Deploys`: production deploy workflow results from the window and any linked deploy warning or failure issue that already exists
   - `## Notes / Data Gaps`: missing Sentry access, ambiguous deploy linkage, incomplete API reads, or a clear quiet-day note when activity was minimal
8. Keep the output concise and maintainer-facing:
   - use flat bullets
   - include direct GitHub or Sentry links where available
   - prefer one line per item with the most useful signal first
   - always emit every required section header in the fixed order above; when a section has nothing to report, include the header and a single line containing `None`
9. Write the discussion:
   - if a matching discussion already exists and remains editable, update its body in place
   - otherwise create exactly one new discussion in the `daily` category with the required title and body

### Blocked cases
- If GitHub discussion reads or writes fail, stop without partial retries and do not write or update any discussion, to avoid duplicates.
- If core GitHub activity reads fail, continue only when enough other successfully read evidence still exists to produce a useful report; in that case, write a partial report and mention the missing reads only inside `## Notes / Data Gaps`.
- If core GitHub activity reads fail and enough other evidence does not exist to produce a useful report, stop without writing.
- If all relevant data sources fail and the discussion would be mostly fabricated, stop without writing.
- If the dated discussion cannot be reused safely, stop instead of falling back to local memory.

### Execution norms
- One discussion maximum per report date.
- Prefer no-op over duplicate or low-confidence reporting.
- Do not create follow-up issues, pull requests, code changes, or comments from this automation.
