You are a post-implementation refinement engine. Discover all issues on the current branch, fix them, ship the fixes, update the PR, and monitor CI. Run the full cycle from discovery through merge-readiness.

Arguments: `$ARGUMENTS` — optional. Can be empty (uses current branch's PR), a PR number (e.g., `123`), or a full reference (e.g., `owner/repo#123`).

## Phase 0: Context Detection

> **Shared reference**: Read `~/.claude/shared/pr-commands.md` at the start. Use its sections as referenced below.

1. **Branch**: `git branch --show-current`.
2. **Branch guard**: If on `main` or `master`, STOP with an error: "You are on the main/master branch. Switch to a feature branch before running refine."
3. **PR lookup**: Follow the "Argument Parsing" section of `~/.claude/shared/pr-commands.md` to parse `$ARGUMENTS`. Arguments are **optional** — if empty, run `gh pr list --head <branch> --repo <owner/repo> --json number,url --limit 1` to find the current branch's PR. If no PR found, note "no PR" and continue (one will be created at Phase 4).
5. **Sub-project CLAUDE.md**: Follow the "Sub-project CLAUDE.md Lookup" section of `~/.claude/shared/pr-commands.md`, targeting the current working directory.
6. **Project type detection**: Follow the "Project Type Detection Matrix" in `~/.claude/shared/pr-commands.md`. Check the working directory for marker files. First match wins. Ignore the `Install` column (dependencies are already present in the working environment). If nothing detected, report "Could not detect project type" and skip that step.

Report the detected context (repo, branch, PR status, project type, lint command, test command) before proceeding.

## Phase 1: Discovery

**Parallelization**: Launch 2 subagents IN PARALLEL (single message, multiple Agent tool calls) to maximize throughput. Do NOT use `run_in_background` — all subagents must run in foreground so their results are available for the Post-Subagent Synthesis step. Skip PR-dependent tasks if no PR exists.

### Subagent 1: PR Data Collection (general-purpose agent) — skip entirely if no PR

Spawn a general-purpose agent with these instructions and context:
- **Provide**: OWNER, REPO, PR_NUMBER, the "PR Comment Fetching", "Review Thread GraphQL Query", and "Comment Classification" sections from `~/.claude/shared/pr-commands.md`.
- **Tasks**:
  - **1c. CI Status**: Run `gh pr checks --repo <owner/repo> <PR_NUMBER>`. For any failed checks, get logs: `gh run view <RUN_ID> --repo <owner/repo> --log-failed`. Collect: check name, failure summary, relevant log lines.
  - **1d. PR Comments**: Fetch all comment data using the provided PR Comment Fetching instructions (includes the Review Thread GraphQL Query). Filter out resolved threads (discard any where `isResolved` is `true`). Classify each comment author as Human or Bot.
  - **1e. PR Diff**: Run `gh pr diff <PR_NUMBER> --repo <OWNER>/<REPO>`.
- **Return**: CI status results, classified unresolved comments, and the full PR diff.

### Subagent 2: Local Validation (general-purpose agent)

Spawn a general-purpose agent with these instructions and context:
- **Provide**: The current working directory, the detected lint command and test command from Phase 0, whether a PR exists, and the OWNER/REPO/PR_NUMBER (if applicable).
- **Tasks**:
  - **1a. Lint Issues**: Run the detected lint command. Collect: file, line, rule/hook, message for each issue.
  - **1b. Test Failures**: After lint completes, run the detected test command. Collect: test name, file, assertion error or traceback summary.
  - **1f. Test Value Analysis**: After tests complete, evaluate tests added or modified on this branch:
    - **Scoping**: If a PR exists, run `gh pr diff <PR_NUMBER> --repo <OWNER>/<REPO>` to get the diff and extract test file paths. If no PR, run `git diff --name-only origin/main...HEAD`. Filter to test files: `test_*.py`, `*_test.py`, files under `tests/` directories, plus JS/TS equivalents (`*.test.ts`, `*.spec.ts`, `__tests__/`). Within those files, only analyze new or modified test functions (use diff hunks). Exclude already-failing tests from 1b.
    - **Evaluation criteria** — flag a test as low-value if it matches any of:
      1. **Framework-only**: Only exercises framework/ORM/router behavior with no project-defined logic.
      2. **Trivially true**: Asserts something always true regardless of code correctness.
      3. **Stdlib/third-party only**: Only calls stdlib/third-party functions without involving project-defined code.
      4. **Exact duplicate**: Identical assertions to another test without adding a new scenario.
      5. **Over-mocked**: Every dependency is mocked, test only verifies mock wiring.
    - **Conservative by default**: When in doubt, keep the test.
    - **Collect**: test function name, file path, line number, reason for flagging, and which criterion (1–5) was matched.
- **Important**: Lint MUST run before tests (auto-fixers modify files). Test value analysis runs after tests. All three tasks are sequential within this agent.
- **Return**: Lint results, test results, and test value analysis findings.

### Post-Subagent Synthesis

After both subagents complete:
1. **Merge results** from both subagents into a unified view.
2. Proceed to Post-Discovery Processing with the combined data.

### Post-Discovery Processing

1. **Classify comments**: Use the "Comment Classification" rules from `~/.claude/shared/pr-commands.md`.

2. **Categorize** each comment:

   | Category | Description |
   |----------|-------------|
   | **Actionable** | Requests a code change (fix, refactor, add test, rename, etc.) |
   | **Question** | Asks for clarification or rationale |
   | **Informational** | Praise, acknowledgment, FYI, or general discussion |
   | **Outdated** | References code/lines that no longer exist in the current diff |

3. **Build unified triage table** with priority:

   | Priority | Type | Source |
   |----------|------|--------|
   | 1 | LINT | Local lint |
   | 2 | TEST | Local tests |
   | 2 | TEST_QUALITY | Test value analysis |
   | 3 | HUMAN_ACTIONABLE | Human reviewer — actionable |
   | 3 | HUMAN_QUESTION | Human reviewer — question |
   | 4 | BOT_ACTIONABLE | Bot — actionable |
   | 5 | CI | CI failures |

   Within priority 2, address `TEST` (failures) before `TEST_QUALITY` (removals).

4. **Deduplicate**: If a lint issue and a bot comment flag the same file+line, keep as LINT (higher priority).

5. If **zero issues found across all sources**, report "All clean — no issues found!" and skip directly to Phase 4 (PR description update).

## CHECKPOINT 1: Review & Approve Fix Plan

Present the full triage table:

```
| # | Priority     | Type             | Source         | File:Line            | Summary                                              |
|---|--------------|------------------|----------------|----------------------|------------------------------------------------------|
| 1 | LINT         | Lint             | Local          | src/foo.py:42        | Unused import `os`                                   |
| 2 | TEST         | Test             | Local          | tests/test_x.py      | AssertionError: 3 != 4                               |
| 3 | TEST_QUALITY | Low-Value Test   | Test Analysis  | tests/test_m.py:15   | Tests ORM save() — no project logic exercised        |
| 4 | TEST_QUALITY | Low-Value Test   | Test Analysis  | tests/test_m.py:30   | Asserts `True` — trivially true                      |
| 5 | HUMAN        | Actionable       | @reviewer1     | src/bar.py:99        | "Use a dataclass instead of dict"                    |
| 6 | HUMAN        | Question         | @reviewer2     | src/baz.py:15        | "Why not use the existing helper?"                   |
| 7 | BOT          | Actionable       | @coderabbit    | src/qux.py:88        | "Missing null check on response"                     |
| 8 | CI           | CI Failure       | GH Actions     | deploy step          | Missing AWS credentials                              |
```

For each PR comment, show the full comment text, author, human/bot classification, and a brief analysis of what the fix would entail.

For each `TEST_QUALITY` item, show the full test function body and explain why it was flagged, referencing the specific criterion (1–5) it matched.

> **Low-Value Tests Detected**: If any `TEST_QUALITY` items appear, note: "N tests were flagged as not adding value — they test framework behavior, assert trivially true things, or mock so extensively that no project code is exercised. The proposed fix is to **remove** these tests. Exclude by number if you disagree with any flagging."

Propose a fix plan: which items will be fixed, which will be skipped (with reason — e.g., HUMAN_QUESTION items are flagged for user attention, CI items may be environment-specific).

**Pause here**: Ask the user: "Which items should I fix? (all / exclude specific numbers / stop)"

Wait for user input before proceeding.

## Phase 2: Fix Loop (max 3 rounds)

For each round (up to 3):

1. **Fix issues in priority order** (LINT → TEST → TEST_QUALITY → HUMAN_ACTIONABLE → BOT_ACTIONABLE → CI):
   - **LINT**: Re-run the detected lint command (many pre-commit hooks auto-fix on first run). Then re-run to verify. Manually edit anything auto-fix didn't resolve.
   - **TEST**: Read the failing test and the code under test. Fix the source code or the test as appropriate.
   - **TEST_QUALITY**: Remove the flagged test function. If all tests in a class are flagged, remove the entire class. If all tests in a file are flagged, delete the file. After removal, clean up any imports that become unused and any file-local fixtures that are no longer referenced. Do NOT touch shared fixtures in `conftest.py` files. Re-run tests after removal to confirm no other tests break. If removal causes a test failure (e.g., due to shared state or ordering dependencies), mark as **STUCK** and restore the test.
   - **HUMAN_ACTIONABLE**: Read the comment and surrounding code (at least 20 lines of context above and below). Validate against current file state and project conventions (reference sub-project CLAUDE.md). Apply the fix with ripple effect analysis (imports, tests, callers).
   - **HUMAN_QUESTION**: Skip — flag for user attention in the report.
   - **BOT_ACTIONABLE**: Read the comment, understand the suggestion, and apply the fix if clear and correct.
   - **CI**: Attempt to reproduce and fix locally. If the failure is environment-specific (e.g., missing secret, deployment issue), mark as "CANNOT FIX LOCALLY".

2. **Verify** — re-run lint (first) then tests (second) after fixes.

3. **Evaluate**:
   - If all issues are resolved → exit loop early.
   - If an issue persists across 2 consecutive rounds → mark it as **STUCK** and stop trying to fix it.
   - If round 3 completes with remaining issues → exit loop.

## Phase 3: Pre-Ship Report

Present results:

```
| # | Type             | Source        | File:Line          | Issue                                    | Status             |
|---|------------------|---------------|--------------------|------------------------------------------|--------------------|
| 1 | LINT             | Local         | src/foo.py:42      | Unused import `os`                       | FIXED              |
| 2 | TEST             | Local         | tests/test_x.py    | AssertionError: 3 != 4                   | FIXED              |
| 3 | TEST_QUALITY     | Test Analysis | tests/test_m.py:15 | Tests ORM save() — no project logic      | REMOVED            |
| 4 | HUMAN_ACTIONABLE | @reviewer1    | src/bar.py:99      | "Use a dataclass"                        | FIXED              |
| 5 | HUMAN_QUESTION   | @reviewer2    | src/baz.py:15      | "Why not use the helper?"                | NEEDS ATTENTION    |
| 6 | BOT_ACTIONABLE   | @coderabbit   | src/qux.py:88      | "Missing null check"                     | FIXED              |
| 7 | CI               | GH Actions    | deploy step        | Missing AWS credentials                  | CANNOT FIX LOCALLY |

Lint: PASS | Tests: PASS
Files modified: src/foo.py, src/bar.py, src/qux.py
Files deleted: (none, or list test files fully removed)
```

### Removed Tests

If any `TEST_QUALITY` items were addressed, include this section:

```
| Test Function              | File               | Reason                                           |
|----------------------------|--------------------|--------------------------------------------------|
| test_save_creates_record   | tests/test_m.py    | Tests ORM save() — no project logic exercised    |

Total: N tests removed from M files.
```

### Status Legend
- **FIXED** — Issue resolved in local files
- **REMOVED** — Low-value test removed from codebase
- **NEEDS ATTENTION** — Requires human judgment or clarification (questions, ambiguous requests)
- **CANNOT FIX LOCALLY** — Environment-specific or external issue
- **STUCK** — Attempted fix but issue persists after multiple rounds

## CHECKPOINT 2: Approve Ship

Present everything the user needs to approve before shipping:

1. **Results report** from Phase 3
2. **Proposed commit message** — descriptive, covering all fixes (e.g., "Address PR review feedback and fix lint/test issues")
3. **Proposed replies** — For each human comment with FIXED status where there is a **strong case** (the comment explicitly requested a specific change AND the fix implements that exact change), draft a brief reply (e.g., "Good catch — refactored to use a dataclass as suggested"). Show each proposed reply. These will NOT be posted unless the user explicitly approves each one.
   - Vague comments ("consider...") or partial fixes → no reply drafted, silent resolve only.
4. **Bot resolution note** — For bot comments with FIXED status: note these will be silently resolved (no replies).
5. **Removed tests** — If any tests were removed (REMOVED status), list each one with its file and reason. The user must explicitly see and approve all test removals before shipping.
6. **PR status** — Whether a PR exists (will be updated) or will be created new.

**Pause here**: Ask the user: "Approve ship? You can also: modify commit message / approve or reject individual replies / stop"

Wait for explicit user confirmation before proceeding.

## Phase 4: Ship

Execute all shipping operations in sequence:

### 4a. Commit & Push
1. Stage modified files: `git add <specific files>` (only files that were changed during fixing).
2. Commit with the approved message.
3. Push: `git push -u origin <branch>`.

### 4b. Resolve Comment Threads
For each fixed comment thread:
- **Human + FIXED + strong case + user approved the reply**: Post the reply via `gh api repos/<OWNER>/<REPO>/pulls/<PR_NUMBER>/comments/<COMMENT_ID>/replies -f body="<REPLY_TEXT>"`, then resolve via GraphQL `resolveReviewThread`.
- **Human + FIXED + strong case + user declined the reply**: Resolve silently via GraphQL only.
- **Human + FIXED + weak case**: Resolve silently via GraphQL only.
- **Bot + FIXED**: Resolve silently via GraphQL only.
- **Not fixed**: Do NOT resolve.

GraphQL resolution:
```
gh api graphql -f query='
  mutation($threadId: ID!) {
    resolveReviewThread(input: {threadId: $threadId}) {
      thread { isResolved }
    }
  }
' -f threadId="<THREAD_NODE_ID>"
```

### 4c. Create or Update PR
1. Generate the PR description by analyzing all commits on the branch (`git log <BASE_REF>..HEAD`), the diff (`git diff <BASE_REF>...HEAD`), and the fix report from Phase 3. Write a clear, concise description covering: what changed, why, and any notable implementation details. Do NOT include a test plan section unless the changes are unusually complex or uncommon.
2. **If no PR exists**: Create via `gh pr create --repo <OWNER>/<REPO> --title "<title>" --body "<body>"`.
3. **If PR exists**: Update via `gh pr edit <PR_NUMBER> --repo <OWNER>/<REPO> --title "<title>" --body "<body>"`.
4. Report the PR URL.

## Phase 5: CI Watch

Monitor GitHub Actions after the push.

1. **Record push timestamp**: `PUSH_TIMESTAMP=$(date -u +%Y-%m-%dT%H:%M:%SZ)`
2. **Poll CI status** every 30 seconds (max 30 polls = 15 minutes):

   Each poll:
   - Run `gh pr checks <PR_NUMBER> --repo <OWNER>/<REPO> --json name,state,conclusion`
   - Count: total, passing, failing, pending
   - Display: `CI: X/Y passing, Z failing, W pending (poll N/30)`

3. **Exit conditions**:
   - **All checks pass** → Proceed to Phase 6.
   - **Any check fails** → Fetch failed check logs via `gh run view <RUN_ID> --repo <OWNER>/<REPO> --log-failed`. Report failure details. Ask: "CI failed. Run another fix round? (yes/no)"
     - If yes → Re-enter Phase 1 scoped to CI failures only (skip re-fetching old comments, skip re-reading already-resolved threads).
     - If no → Stop with the failure report.
   - **Timeout (30 polls)** → Report: "CI polling timed out after 15 minutes. X checks still pending." Stop.

## Phase 6: Post-CI Comment Scan

After CI passes, check for new automated reviewer comments.

1. **Re-fetch PR comments** using the same API calls as Phase 1d.
2. **Filter** to comments where:
   - `createdAt` is after `PUSH_TIMESTAMP`
   - Author is a bot (per "Comment Classification" in `~/.claude/shared/pr-commands.md`)
3. **Exclude** threads that existed before the push (compare thread IDs against the set from Phase 1d).
4. **If new bot comments found**: Display them in a table:
   ```
   New automated review comments detected after push:
   | # | Bot           | File:Line       | Comment                           |
   |---|---------------|-----------------|-----------------------------------|
   | 1 | coderabbit    | src/foo.py:15   | "Consider extracting this method" |
   ```
   Ask: "Address these new automated comments? (yes / no / done for now)"
   - If yes → Re-enter Phase 1 scoped to these new comments only. Re-run lint + tests after fixes.
   - If no → Report them and stop.
5. **If no new comments**: Report "No new automated review comments. PR is ready for human review." and stop.

## Comment Resolution Rules

- **Strong case replies**: For human comments where the fix directly implements what was explicitly requested, draft a brief reply. Show it to the user at Checkpoint 2. Do NOT auto-post. The user decides whether each reply gets posted.
- **User approves reply**: Post it, then resolve the thread via GraphQL.
- **User declines reply**: Resolve silently via GraphQL only.
- **Weak case / bot / all other fixed comments**: Resolve silently via GraphQL `resolveReviewThread`.
- **Unfixed comments**: Never resolve.
- **Never auto-post**: All replies must be shown to the user and explicitly approved before posting.

## Key Constraints

Follow all "Shared Constraints" from `~/.claude/shared/pr-commands.md`, plus these refine-specific rules:

- **Edit locally only**: Use the Edit tool for all file modifications. NEVER use GitHub MCP tools (`push_files`, `create_or_update_file`) to modify files.
- **Never auto-post replies**: Show proposed reply text to the user; only post if they explicitly approve each one.
- **Max 3 fix rounds** per entry into Phase 2.
- **Be surgical**: Only edit files with identified issues. Do not refactor or "improve" surrounding code.
- **Branch guard**: Refuse to run on main/master.
- **Omit test plan**: Do not include a test plan section in PR descriptions unless the changes are unusually complex or uncommon.
- **Human over bot**: Prioritize human reviewer comments over bot-generated feedback.
- **Graceful edge cases**: Handle no comments, all resolved, comments on deleted files, no PR, and pagination correctly.
