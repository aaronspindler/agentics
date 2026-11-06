---
name: pr-refine
description: "Apply focused validated fixes to the current branch or a selected PR from actionable review feedback, local failures, or existing CI failures."
---

# Pr Refine

Read [PR workflow foundations](references/pr-workflows.md).

1. Resolve branch/PR/head/base and preserve unrelated changes. Stop before editing a protected/default branch unless the user explicitly selected that workflow.
2. Gather actionable review threads, local validation failures, and exact CI evidence. Separate questions, already-fixed items, environment noise, and product decisions from defects.
3. State triage before large edits. Clarify only scope choices not already established; continue independent preparation.
4. Fix confirmed in-scope defects, update meaningful regression tests and owning docs, and validate affected surfaces. Avoid broad cleanup or speculative rewrites.
5. Commit/push/PR updates only within existing authorization. Normalize target-repo metadata and never publish unvalidated changes. Reply/resolve addressed review threads only when that write is included.
6. Take one check snapshot for handoff; monitor CI only when requested or actively diagnosing a failed check. Return fixed items, remaining failures, exact evidence, and residual decisions.
