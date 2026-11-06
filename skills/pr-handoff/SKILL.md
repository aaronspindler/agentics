---
name: pr-handoff
description: "Draft a concise PR title, final-change description, and factual operator handoff without publishing or changing Git state."
---

# Pr Handoff

Read [repository context](references/repository-context.md) and [PR metadata conventions](references/pr-metadata.md).

1. Gather final branch/base/head, actual diff, user/operator impact, clear issue links, observed checks, and published preview links. Use completed gate evidence only when it remains valid.
2. Produce a short title and description following the target project's template. Lead with concrete problem/result, then meaningful grouped changes and material limitations.
3. Provide exact validation outcomes in the operator handoff, distinguishing static checks, targeted tests, coverage, CI, deployment, and live verification. Place them in the PR body only if project policy permits.
4. Do not invent validation, repeat file churn, include private memory citations, or narrate abandoned approaches. Exclude local preview paths and unfinished placeholders.
5. Drafting does not authorize commit, push, PR creation/edit, comments, or deployment. Run a publication gate only when a substantive publication workflow is actually authorized.
