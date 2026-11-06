---
name: pr-review
description: "Perform an explicitly requested read-only review of a pull request, branch, or local diff for correctness, regressions, security, operational risk, and concrete test gaps."
---

# Pr Review

Read [PR workflow foundations](references/pr-workflows.md).

1. Resolve requested PR/diff and verified base; otherwise prefer local uncommitted changes or the branch comparison. Inspect relevant owning guidance, changed paths, callers, checks, and existing feedback.
2. Establish concrete triggers and consequences with the smallest non-mutating checks. Inspect helper prerequisites; do not run fixing hooks or infer remote health from local process state.
3. Prioritize correctness, security, regression, deployment failure, and meaningful missing tests. Respect project policy for intentional private configuration; review exposure rather than tracked status alone.
4. Return findings first with stable `REVIEW-NNN` IDs, severity/confidence, exact current-head file/lines, trigger/impact, and smallest repair direction. Include repo/PR/branch/head context, observed validation, duplicates, and residual gaps. Say explicitly when there are no findings.
5. No file edits or external mutations, including comments, reviews, Git, services, dashboards, or credentials. Use a separate authorized refine/comment action for follow-up; structural/docs/design-only issues belong to a focused audit.
