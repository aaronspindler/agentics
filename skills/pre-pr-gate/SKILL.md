---
name: pre-pr-gate
description: "Run a focused final review, repair, and validation gate before authorized substantive branch publication or PR creation."
---

# Pre Pr Gate

Read [PR workflow foundations](references/pr-workflows.md).

1. Resolve authorized publication scope, branch/base/head, remote target, full diff, dirty state, and preview evidence. Stop for ambiguous unrelated changes, unsafe target, or missing base. Skip metadata-only edits, draft-only handoffs, trivial typo work, and explicit gate bypasses.
2. Reuse gate proof only under the shared proof contract. Otherwise run correctness review, adding exploration, structural/docs audit, test-gap, design/visual, CI, ops, or external-doc specialists only when the actual risk warrants them. Parent equivalent passes are valid when delegation is unavailable.
3. Triage concrete findings as fixable defect, already handled/not real, human judgment, or residual risk. Fix only confirmed scoped defects while preserving user work and required safeguards.
4. Add meaningful tests/docs and relevant previews, then run smallest required checks. Re-review only affected passes. Stop when clean, validation/access blocks, a product decision remains, or the same finding persists after a focused fix attempt.
5. Publish only validated final content under existing authorization. Do not force-push, rebase, or merge the base as part of this gate. Verify remote ref equals validated local HEAD after a normal push.
6. Record `pre-pr-gate: <final-head-sha>`, base ref/SHA, checked-input/result snapshot, and verified remote identity. Confirm no relevant dirty/untracked content remains, draft handoff/metadata, and state material residual risks. Do not poll pending CI without a monitoring request.
