# PR Commands — Shared Reference

> **Consumers**: `/review`, `/refine`, `/suggest`. Changes here affect all three commands. Test each after editing.

---

## Argument Parsing

Parse `$ARGUMENTS` to determine the target PR:

1. **Repo slug**: Extract `owner/repo` from `git remote -v` (use the `origin` fetch URL) as the default.
2. **Parse the argument**:
   - If a GitHub URL matching `https://github.com/<owner>/<repo>/pull/<number>`, extract the owner, repo, and PR number from the URL.
   - Else if `owner/repo#number` pattern, extract the repo slug and PR number.
   - Else if bare number, use the detected repo slug + number.
   - Else if empty/not provided: behavior is command-specific (see the calling command's instructions).
   - Else (invalid): STOP with error showing accepted formats.
3. **Validate PR exists**: Run `gh pr view <PR_NUMBER> --repo <OWNER>/<REPO> --json number,title,author,headRefName,baseRefName,state,headRefOid`. If not found or state is not `OPEN`, STOP with error.
4. **Store context**: Save `OWNER`, `REPO`, `PR_NUMBER`, `PR_TITLE`, `PR_AUTHOR`, `HEAD_REF`, `BASE_REF`, `HEAD_SHA` for use throughout.

---

## Sub-project CLAUDE.md Lookup

Look for a project-specific `CLAUDE.md`, `README.md`, or `.claude/CLAUDE.md` in the target sub-project directory. If found, read it for project-specific lint/test commands. Commands found here override the detection matrix.

---

## Project Type Detection Matrix

Check the target directory for marker files. First match wins:

| Marker | Type | Lint | Test | Install |
|--------|------|------|------|---------|
| `pants.toml` + `justfile` or `Justfile` | Pants | `just pre-commit` | `just test . -v` | skip |
| `pyproject.toml` + `poetry.lock` + `Makefile` with `test` target | Poetry+Make | `poetry run pre-commit run --all-files` | `make test` | `poetry install` |
| `pyproject.toml` + `poetry.lock` | Poetry | `poetry run pre-commit run --all-files` | `poetry run pytest` | `poetry install` |
| `package.json` + `pnpm-lock.yaml` | pnpm | `pnpm run lint` | `pnpm run test` | `pnpm install` |
| `package.json` + `yarn.lock` | Yarn | `yarn lint` | `yarn test` | `yarn install` |
| `package.json` | npm | `npm run lint` | `npm run test` | `npm install` |
| `.terragrunt-version` or `terragrunt.hcl` | Terragrunt | `pre-commit run --from-ref origin/main --to-ref HEAD` | skip | skip |
| `versions.tf` or `.terraform.lock.hcl` | Terraform | `pre-commit run -a` | `terraform test` | skip |
| `Makefile` with `lint` target | Make | `make lint` | `make test` | skip |
| Fallback: `pre-commit` available | pre-commit | `pre-commit run --all-files` | skip | skip |

Notes:
- The `Install` column is used by `/review` (worktree setup requires installing dependencies). `/refine` works in the user's existing environment and ignores this column.
- Sub-project CLAUDE.md commands (see above) override this matrix when found.
- If nothing matches, report "Could not detect project type" and skip lint/test steps.

---

## PR Comment Fetching

Fetch all existing review feedback in parallel:

1. **Review comments** (inline on code): `gh api repos/<OWNER>/<REPO>/pulls/<PR_NUMBER>/comments --paginate`
2. **Review-level comments** (top-level review bodies): `gh api repos/<OWNER>/<REPO>/pulls/<PR_NUMBER>/reviews --paginate`
3. **Conversation comments** (issue-style): `gh api repos/<OWNER>/<REPO>/issues/<PR_NUMBER>/comments --paginate`
4. **Review thread data** (for thread IDs and resolution status) — use the GraphQL query below.

---

## Review Thread GraphQL Query

```
gh api graphql -f query='
  query($owner: String!, $repo: String!, $pr: Int!) {
    repository(owner: $owner, name: $repo) {
      pullRequest(number: $pr) {
        reviewThreads(first: 100) {
          nodes {
            id
            isResolved
            isOutdated
            line
            path
            comments(first: 10) {
              nodes {
                id
                databaseId
                body
                author { login }
                createdAt
              }
            }
          }
        }
      }
    }
  }
' -f owner="<OWNER>" -f repo="<REPO>" -F pr=<PR_NUMBER>
```

Substitute `<OWNER>`, `<REPO>`, and `<PR_NUMBER>` with the stored context values.

---

## Comment Classification

Classify each comment author as **Human** or **Bot**:
- **Bot**: `user.type == "Bot"` OR username ends in `[bot]`
- **Human**: everything else

---

## Shared Constraints

These rules apply to all PR commands (`/review`, `/refine`, `/suggest`):

- **Always use `--repo <owner/repo>`** for every `gh` command.
- **No real data**: Never include real production data (secrets, credentials, PII, customer names, IDs, PHI) in any output, code, commits, or PR descriptions.
- **Lint before tests**: Lint auto-fixers modify files, so always run lint first and tests second (not in parallel).
- **Repo-structure awareness**: If the repo is a monorepo, always verify which sub-project is targeted. Use the detection matrix — do not assume tools.
