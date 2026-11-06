# PR workflow foundations

Read [repository context](repository-context.md). Accept a full GitHub PR URL, `OWNER/REPO#NUMBER`, or a number resolved against the verified current repository. Without an argument, use the current branch's PR or the requested local diff. Do not guess the default branch or silently switch repositories.

Prefer connected GitHub tools for metadata, diffs, comments, and checks; use `gh` for exact Actions logs or connector gaps. The shared helper is `agentics tools --repo-root PATH pr-threads`: `list-open-prs`, `list-merged-prs`, `list-unresolved-threads`, and `reply-thread`. Supply configured author filters explicitly for author-scoped maintenance. Resolve safe checkout/worktree behavior from active repository guidance and the user's request.

Review, comment publication, branch fixes, conflict repair, metadata, and live operations have separate scopes. Carry forward authorization already supplied for the requested action; a worktree is isolation, not permission. Do not force-push or rebase. Base-into-head merging is limited to an explicitly authorized conflict-repair workflow after inspecting live refs and conflicts. Preserve unrelated changes and do not publish unvalidated fixes.

Use the relevant change skills when installed, or perform their equivalent focused preparation and validation. Named read-only specialists are optional: use a parent pass when delegation is unavailable. Shared agents inherit the caller's model and reasoning preferences; do not introduce a model pin through the delegated prompt.

## Gate proof

A `pre-pr-gate: <head-sha>` marker records a completed gate on committed content. Include the reviewed base ref/SHA and checked inputs/results: commands, config, dependency/runtime state, and material evidence. After an authorized push, record the remote repository, branch ref, and verified remote head SHA.

Before reusing proof, re-read remote branch and PR heads, resolve the current intended base, and compare local HEAD and checked inputs. Any missing evidence, changed base/input, relevant untracked/dirty content, or changed remote head invalidates affected evidence; the head SHA alone is insufficient. Refresh affected reviews/checks and reuse still-valid successful checks. Do not rerun the entire gate solely because another PR skill was invoked.

After publication, take one check snapshot for handoff. Monitor or poll CI only when requested or when diagnosing an existing failed check. Pending checks alone do not require keeping a worker active.
