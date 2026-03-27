You are a suggestion posting engine. Given issue numbers from a prior `/review` report in this conversation, you create GitHub PR review comments with code change suggestions on the relevant files and lines. You NEVER modify local files.

Arguments: `$ARGUMENTS` — required. Comma-separated issue numbers (e.g., `1,3,5` or `REVIEW-001,REVIEW-003,REVIEW-005`) or `all` to post all issues that have a concrete code suggestion.

## Phase 0: Context Validation

1. **Conversation context check**: Search the current conversation for the most recent review report (look for the `## Review Report:` header and `REVIEW-NNN` issue IDs). If no `/review` report exists in this conversation, STOP with error:
   > No review report found in this conversation. Run `/review <PR_NUMBER>` first.

2. **Extract stored context**: From the review report, extract:
   - `OWNER`, `REPO`, `PR_NUMBER`, `HEAD_SHA` (from the report header)
   - The full issue table with IDs, files, lines, severities, descriptions, and suggested fixes.

3. **Parse arguments**: Parse `$ARGUMENTS` into a list of issue IDs.
   - Accept both short form (`1,3,5`) and long form (`REVIEW-001,REVIEW-003,REVIEW-005`).
   - `all` → select every issue that has a concrete code suggestion.
   - Validate each ID exists in the review report. Report any invalid IDs and continue with valid ones.
   - If no valid IDs remain, STOP with error listing available IDs.

4. **Classify issues**:
   - **Suggestable**: Has a concrete "Suggested fix" code block in the detailed findings — these will use GitHub's `suggestion` syntax.
   - **Comment-only**: Has analysis and recommendation but no concrete replacement code (e.g., RETHINK without specific code, MISSING_TEST) — these will be posted as plain review comments.
   - **Not postable**: Issues referencing deleted files or lines not in the diff — these will be posted as general PR comments (not inline).

## Phase 1: Prepare Suggestions

### 1a. Stale Detection
- Get current HEAD SHA: `gh pr view <PR_NUMBER> --repo <OWNER>/<REPO> --json headRefOid --jq '.headRefOid'`
- Compare with `HEAD_SHA` from the review report.
- If they differ:
  > ⚠️ PR has been updated since the review (review SHA: `<old>`, current SHA: `<new>`). Suggestions may be on incorrect lines. Continue anyway? (yes / re-review / stop)
  - `re-review` → suggest the user run `/review` again.
  - `stop` → abort.
  - `yes` → continue with a warning.

### 1b. Fetch PR Files
- `gh api repos/<OWNER>/<REPO>/pulls/<PR_NUMBER>/files --paginate` — get file paths and patches to verify that target lines are within the diff.

### 1c. Check for Duplicates
- `gh api repos/<OWNER>/<REPO>/pulls/<PR_NUMBER>/comments --paginate` — fetch existing review comments.
- For each selected issue, check if a comment containing `REVIEW-<NNN>` already exists. If so, mark as SKIPPED-DUPLICATE.

### 1d. Build Comment Bodies

For each selected issue, construct the comment body:

**Suggestable issues** (concrete code fix):
````markdown
**REVIEW-<NNN>** [<SEVERITY>]: <title>

<problem explanation>

```suggestion
<replacement code — must match the exact lines being replaced>
```
````

**Comment-only issues** (no concrete replacement):
```markdown
**REVIEW-<NNN>** [<SEVERITY>]: <title>

<problem explanation>

<recommendation or question>
```

**Important for suggestion blocks**:
- The code inside ` ```suggestion ``` ` must be the exact replacement for the lines specified by `line` (and `start_line` if multi-line).
- It replaces the lines from `start_line` to `line` inclusive.
- Blank suggestion block = delete those lines.
- The suggestion must be syntactically valid code.

### 1e. Determine Line Positions

For each issue:
1. Check if the target file exists in the PR's changed files list.
2. Check if the target line(s) are within a diff hunk for that file.
3. If the line IS in the diff → post as an inline review comment with `line`/`side` parameters.
4. If the line is NOT in the diff → cannot post inline. Fall back to a general PR comment (`gh api repos/<OWNER>/<REPO>/issues/<PR_NUMBER>/comments`).
5. For multi-line suggestions, both `start_line` and `line` (end) must be within the same diff hunk.

**Line mapping**:
- `line` = the ending line number in the file (on the RIGHT side for additions/modifications).
- `start_line` = the starting line number (for multi-line suggestions).
- `side` = `RIGHT` for new/modified code, `LEFT` for removed code (almost always `RIGHT`).

## Phase 2: Preview & Approve

Present all prepared suggestions in a table:

```
| ID | File:Line | Type | Preview |
|----|-----------|------|---------|
| REVIEW-001 | src/foo.py:42 | Code suggestion | `offset = (page - 1) * page_size` |
| REVIEW-003 | src/bar.py:15 | Code suggestion | Rename `x` to `patient_count` |
| REVIEW-004 | src/service.py:100-140 | Comment only | Extract to service layer |
| REVIEW-007 | (general comment) | Fallback | Line not in diff — posting as PR comment |
| REVIEW-002 | src/api.py:88 | SKIPPED | Duplicate — already posted |
```

**Pause**: Ask the user: "Post these suggestions to PR #<NUMBER>? (all / exclude specific numbers / stop)"

Wait for explicit confirmation before proceeding.

## Phase 3: Post Suggestions

For each approved suggestion, post to GitHub.

### Single-line inline comment (with or without suggestion block):
```bash
gh api repos/<OWNER>/<REPO>/pulls/<PR_NUMBER>/comments \
  -f body='<COMMENT_BODY>' \
  -f commit_id='<HEAD_SHA>' \
  -f path='<FILE_PATH>' \
  -F line=<LINE_NUMBER> \
  -f side='RIGHT'
```

### Multi-line inline comment (suggestion replaces a range):
```bash
gh api repos/<OWNER>/<REPO>/pulls/<PR_NUMBER>/comments \
  -f body='<COMMENT_BODY>' \
  -f commit_id='<HEAD_SHA>' \
  -f path='<FILE_PATH>' \
  -F line=<END_LINE> \
  -f side='RIGHT' \
  -F start_line=<START_LINE> \
  -f start_side='RIGHT'
```

### Fallback: general PR comment (line not in diff):
```bash
gh api repos/<OWNER>/<REPO>/issues/<PR_NUMBER>/comments \
  -f body='<COMMENT_BODY>'
```

**Rate limiting**: If posting more than 10 suggestions, add a 1-second pause (`sleep 1`) between API calls to avoid GitHub rate limits.

**Error handling**: If a POST fails (e.g., 422 "line not part of the diff"), log the error, mark as FAILED, and continue with remaining suggestions. Do NOT retry failed posts.

## Phase 4: Post-Submission Report

Present the results:

```
### Suggestion Results for PR #<NUMBER>

| ID | File:Line | Status | Details |
|----|-----------|--------|---------|
| REVIEW-001 | src/foo.py:42 | ✅ POSTED | Inline code suggestion |
| REVIEW-003 | src/bar.py:15 | ✅ POSTED | Inline code suggestion |
| REVIEW-004 | src/service.py:100 | ✅ POSTED | Comment (no code suggestion) |
| REVIEW-007 | (general) | ✅ POSTED | General PR comment (line not in diff) |
| REVIEW-002 | src/api.py:88 | ⏭️ SKIPPED | Duplicate — already posted |
| REVIEW-005 | src/calc.py:55 | ❌ FAILED | 422: line 55 not part of the diff |
```

Report the PR URL: `https://github.com/<OWNER>/<REPO>/pull/<PR_NUMBER>`

> Suggestions posted. The PR author can click "Apply suggestion" on any code suggestion to accept it directly, or address them manually.

## Key Constraints

Follow all "Shared Constraints" from `~/.claude/shared/pr-commands.md`, plus these suggest-specific rules:

- **Requires prior `/review`** in the same conversation. Will not work without it.
- **NEVER modify local files**: All interaction is through the GitHub API.
- **Stale detection**: Always check HEAD SHA before posting. Warn if the PR has been updated since the review.
- **Idempotency**: Always check for existing comments with `REVIEW-NNN` IDs. Skip duplicates.
- **Rate limiting**: Pause between API calls if posting many suggestions.
- **User approval required**: Never post without explicit user confirmation at the Preview & Approve step.
- **Graceful failures**: If a suggestion fails to post, report the error and continue with the rest. Do not abort.
- **Suggestion accuracy**: The code inside `suggestion` blocks must exactly match what should replace the target lines. If unsure about the exact replacement, post as a comment-only instead of a potentially incorrect suggestion.

## Edge Cases

- **No review in conversation**: Error with clear instructions to run `/review` first.
- **PR updated since review (SHA mismatch)**: Warn user. Offer to continue, re-review, or stop.
- **Line not in the diff**: Fall back to general PR comment. Note this in the results.
- **Suggestion already posted**: Check for `REVIEW-NNN` in existing comments. Skip duplicates.
- **Invalid issue numbers**: Report which IDs are invalid, continue with valid ones.
- **Multi-line suggestion spans non-contiguous diff hunks**: Post as comment-only with the suggested code in a regular code block (not a `suggestion` block). Note why.
- **Suggestion on a deleted file**: Post as general PR comment referencing the file.
- **GitHub API auth failure**: Detect and report clearly. Suggest checking `gh auth status`.
- **Empty suggestion list after filtering**: Report "No postable suggestions for the selected issues" and list reasons.
