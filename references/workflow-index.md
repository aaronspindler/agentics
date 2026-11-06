# Maintenance workflow index

These playbooks support explicitly requested manual work. Installation creates no schedule and grants no outbound-write authority. Read [shared maintenance rules](automation-guidelines.md), then only the selected playbook; resolve project-specific policy from its owning documentation.

| Workflow | Use |
| --- | --- |
| [pr-guardian](workflows/pr-guardian.md) | Stabilize owned same-repository PRs: conflicts, existing CI failures, actionable feedback, readiness. |
| [pr-reviewer](workflows/pr-reviewer.md) | Review open PR heads with deduplicated findings; no code changes. |
| [merged-pr-comment-sweep](workflows/merged-pr-comment-sweep.md) | Convert unresolved merged-PR feedback into bounded fixes or deduplicated issues. |
| [sentry-daily-triage](workflows/sentry-daily-triage.md) | Group complete configured project scans into actionable GitHub issues. |
| [daily-bug-scan](workflows/daily-bug-scan.md) | Investigate high-confidence landed regressions outside active PR maintenance. |
| [test-gap-detection](workflows/test-gap-detection.md) | Add one focused regression-test opportunity outside active PR stabilization. |
| [docs-cohesion-keeper](workflows/docs-cohesion-keeper.md) | Maintain source-backed internal documentation in bounded docs changes. |
| [code-health-scout](workflows/code-health-scout.md) | Combine complexity, cleanup, and code-hygiene signals into deduplicated debt issues. |
| [daily-changes-digest](workflows/daily-changes-digest.md) | Summarize a configured calendar day into one dated discussion. |
| [orchestrator](workflows/orchestrator.md) | Optionally dispatch bounded work across configured lanes without executing fixes inline. |
| [product-marketing-sync](workflows/product-marketing-sync.md) | Align allowed marketing surfaces with verified shipped product behavior. |
