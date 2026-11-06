---
name: pr-conflicts
description: "Repair an explicitly requested same-repository PR merge conflict with one inspected base-into-head merge, validation, and authorized publication."
---

# Pr Conflicts

Read [PR workflow foundations](references/pr-workflows.md).

1. Read live head/base refs and SHAs, changed files, mergeability, and push target. Verify this is a same-repository PR; do not assume fork publication authority.
2. Fetch authorized refs and inspect the real conflict set with `git merge-tree` or equivalent non-mutating inspection. Resolve missing product/deployment judgments before dependent mutation.
3. Follow the user's and repository's checkout/worktree strategy. Verify branch ownership and dirty state before repair, preserve unrelated work, and use isolation only when selected or needed for safety. Perform exactly one base-into-head conflict-repair merge within the requested scope; never rebase or force-push.
4. Preserve newer base fixes while porting the PR intent onto current implementation. Update directly coupled callers/tests; avoid ordinary CI, review-thread cleanup, or unrelated refactoring.
5. Run appropriate compatibility preparation and smallest required validation. If confidence or checks fail, leave the concrete repair for review and do not push.
6. When publication is authorized, create the intentional merge-resolution commit, push normally to the existing head, verify remote head and GitHub mergeability, and hand remaining ordinary PR cleanup to its own task.
