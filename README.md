# Agentics

> CLI tools, slash commands, and workflows that put AI agents to work across the development lifecycle — from code review to workflow automation.

## Global Codex toolkit

Agentics is the source of truth for 26 reusable skills (25 extracted workflows plus a maintenance router), 13 custom agents, and ten maintenance playbooks. Project commands, product requirements, infrastructure details, and PR policies stay in each project's own guidance.

Install the Python 3.11+ command from a checkout:

```bash
uv tool install .
agentics validate
agentics install --all --dry-run
agentics install --all
```

Without uv, install into a dedicated virtual environment with `python3 -m venv .venv` and `.venv/bin/python -m pip install .`, then use `.venv/bin/agentics` for the commands below. Installing the package alone does not install skills or change Codex settings.

```bash
agentics list
agentics install --group core --group github
agentics install --skill stack-rollout --agent simplicity_reviewer
agentics status --json
agentics update --dry-run
agentics update
agentics uninstall --all --dry-run
```

| Group | Capabilities |
| --- | --- |
| `core` | Change planning, reproduction, cohesion, tests, verification, and final audit |
| `github` | PR review, refinement, conflicts, comments, drafts, metadata, previews, and gates |
| `docs` | Change documentation, documentation audits and maintenance, backlog work, and capability maintenance |
| `ops` | Deployment safety, Cloudflare, Dokploy, service integration, rollout, and observability |
| `maintenance` | Requested maintenance playbooks and coordination |

Selections include declared dependencies. Omit a selection for `status` to inspect the whole catalog; omit it for `update` or `uninstall` to operate on owned installations. `update --all` only updates already installed items. Removing one skill leaves its supporting roles installed; removing an agent still required by an installed skill is refused.

Skills are copied to `~/.agents/skills/`; agents go to `${CODEX_HOME:-~/.codex}/agents/`. Ownership and content hashes live in `${CODEX_HOME:-~/.codex}/agentics/installed.json`. `--home` and `--codex-home` allow isolated installations and tests. Pulling this repo changes no installed tools: upgrade the command with `uv tool upgrade agentics-toolkit --reinstall`, then run `agentics update`. For a local checkout, rerun `uv tool install --reinstall .` before updating.

The installer checks the complete operation before writing, preserves executable resources, and refuses unknown collisions or locally changed, missing, or additional bundle files. Keep custom edits outside managed copies. If rollback cannot finish, the installer retains its lock and reports recovery paths; restore the affected files before removing the lock and retrying. A stale installation lock otherwise requires inspecting the interrupted operation before removing it. Codex settings, MCP servers, permissions, and global instructions are not changed. Agents inherit model and reasoning settings; review-only instructions do not create a separate sandbox. Restart Codex if newly installed tools do not appear.

Public discovery and custom-agent locations follow the official [skills](https://learn.chatgpt.com/docs/build-skills) and [subagent](https://learn.chatgpt.com/docs/agent-configuration/subagents) documentation. Use the Agentics installer for the complete bundled resources and role dependencies.

### Using skills and maintenance workflows

Invoke skills as `$change-plan`, `$pr-review`, or another name from `agentics list`. Only load the skills needed for the request. PR review remains explicitly invoked. The collection follows the target repository's root and scoped `AGENTS.md`, templates, and owning documentation; it imposes no required project configuration schema.

```bash
agentics workflows list
agentics workflows show daily-bug-scan
```

Use `$maintenance-workflow` with a playbook ID to run a requested procedure. The playbooks include PR maintenance, error triage, bug scans, test gaps, documentation cohesion, product/marketing consistency, code health, and change digests. Installing or reading a playbook creates no schedules and grants no publication or deployment authority. Optional integrations must already be available and authorized.

### Portable GitHub helpers

```bash
agentics tools --repo-root /path/to/checkout pr-threads list-open-prs
agentics tools --repo-root /path/to/checkout pr-threads list-merged-prs
agentics tools --repo-root /path/to/checkout pr-threads list-unresolved-threads --pr 42
agentics tools --repo-root /path/to/checkout preview --help
agentics tools --repo-root /path/to/checkout preview-sync --help
```

Helpers discover the current checkout through Git when `--repo-root` is omitted. An explicit root takes precedence over ambient repository environment variables; `--repo` explicitly selects the GitHub repository. Author filters use `--author` or the authenticated GitHub identity. The merged-PR command discovers the repository's default branch unless `--base` is supplied. Git and authenticated GitHub CLI are required for GitHub operations; preview publication requires GitHub.com and GitHub CLI 2.99+.

Preview capture stays in the consuming project. Agentics owns artifact storage, capture provenance, hashes, native attachment publication, marked comments, and cleanup. Publishing requires the local and PR heads to match, and missing local captures leave published previews intact. Explicit deletion is separate from local cleanup.

### Developing and consuming the collection

Canonical sources are `skills/`, `agents/`, `workflows/`, and `references/`; `catalog.json` declares groups, dependencies, and resource assembly. The wheel bundles these sources, so installations work without the original checkout. Edit canonical sources and reinstall/update; do not edit installed copies.

Project migration keeps application commands, label/body policies, operational caveats, and historical output markers in existing project docs. A project that calls Python helpers must install the toolkit in its own development/CI environment, pinned to an immutable Git revision or a hash-locked wheel. It must never depend on a developer's global Codex directory. A generated dependency wheel is an installation artifact, not a separately maintained source fork.

```bash
python3 -m venv .venv
.venv/bin/python -m pip install '.[test]' build
.venv/bin/agentics validate
.venv/bin/python -m unittest discover -s tests -v
.venv/bin/python -m build
```

The toolkit CI validates Python 3.11 and 3.14, catalog resources, installer ownership, and isolated wheel installation. Existing Claude commands and the pre-commit package remain separate subprojects.

## Subprojects

### claude-commands

> Custom slash commands for Claude Code that automate code review, refinement, design, PR feedback, daily activity notes, and ticket authoring.

Six commands that handle multi-phase workflows end-to-end:

| Command | What it does |
|---------|-------------|
| `/review <PR>` | Checks out a PR into an isolated worktree, runs lint/tests, performs deep code analysis across 9 severity levels, validates findings against actual code, and produces a numbered findings report. Never commits or pushes. |
| `/refine` | Discovers issues on the current branch (lint, tests, CI failures, PR comments), fixes them in up to 3 rounds, commits, pushes, creates/updates the PR, and watches CI. |
| `/suggest <issues>` | Posts specific findings from a `/review` report as inline PR comments with `suggestion` blocks. Detects stale reviews and deduplicates against existing comments. |
| `/design <brief>` | Explores the codebase, produces a 1-pager design doc with alternatives and comparison matrix, then breaks the solution into sequenced implementation tickets. |
| `/daily [date]` | Synthesizes your GitHub activity for a single day into an Obsidian daily note (`## Activity` + `## Standup`), creating it from a template or updating in place. Local-write only. Needs a Configuration block (vault path, GitHub scope). |
| `/ticket [url\|desc]` | Creates or updates a ClickUp ticket with a structured 3-section body (Description, Acceptance Criteria, Gotchas), resolving private-doc links to public URLs or inlining them. Needs a Configuration block (internal-docs path). |

Commands share common reference files in `shared/`: `pr-commands.md` (argument parsing, project type detection, PR comment fetching), `review-rubrics.md` (security/architecture/test rubrics for `/review` and `/refine`), `checkpoint.md` (approval-gate protocol for `/daily` and `/ticket`), and `design-templates.md` (document structure).

**Install & usage:**

```bash
cd claude-commands && make deploy   # copies to ~/.claude/commands/ and ~/.claude/shared/

# Then in any Claude Code session:
/review 42
/refine
/suggest 1,3
/design "Add patient export API"
/daily                    # /daily and /ticket each read a Configuration block at the
/ticket "Fix flaky test"  # top of the command — set vault path / GitHub scope / internal-docs path first
```

| Make target | What it does |
|-------------|-------------|
| `make deploy` | Copy commands and shared files to `~/.claude/` |
| `make diff` | Show differences between repo and deployed files |
| `make status` | Check whether deployed files are in sync |

This repo is the source of truth — never edit files directly in `~/.claude/`.

---

### precommit-agentic-check

> LLM-powered pre-commit gate that reviews staged git changes against a policy prompt and returns a structured pass/fail verdict.

Reads your staged diff with surrounding context, sends it to an LLM with a policy prompt, and enforces a JSON response contract (pass/fail, findings with severity/file/line, optional suggested patch). Zero runtime dependencies — uses stdlib HTTP only.

**Install & usage:**

```yaml
# .pre-commit-config.yaml
repos:
  - repo: local
    hooks:
      - id: agentic-check
        name: Agentic Check
        entry: agentic-check
        language: python
        pass_filenames: false
        additional_dependencies:
          - precommit-agentic-check==0.1.0
        args:
          - --provider=anthropic       # or openai
          - --model=claude-sonnet-4-20250514
          - --prompt-file=.ai/prompts/precommit_gate.md
          - --strict=error             # or warn (continue on LLM failure)
```

Requires `ANTHROPIC_API_KEY` or `OPENAI_API_KEY` in the environment. Customize the policy prompt to match your project's standards.

Docs: [`precommit-agentic-check/README.md`](precommit-agentic-check/README.md)

## GitHub Agentic Workflows

AI-powered workflows authored as markdown with YAML frontmatter, compiled to GitHub Actions via [`gh aw`](https://github.com/github/gh-aw).

**Getting started:**

```bash
gh extension install github/gh-aw   # or: gh extension upgrade gh-aw
gh aw init                           # initialize a repo for agentic workflows
gh aw compile                        # compile .md sources into .lock.yml
```

**Available workflows:**

| Workflow | Summary | Install |
|----------|---------|---------|
| [Agents Doc Sync](#agents-doc-sync) | Keeps `CLAUDE.md` and `AGENTS.md` aligned; opens a PR only when sync changes are needed. | `gh aw add-wizard aaronspindler/agentics/agents-doc-sync` |

### Agents Doc Sync

Detects divergence between `CLAUDE.md` and `AGENTS.md`, updates the file missing information, and creates a PR only when edits are made.

- **Source**: `.github/workflows/agents-doc-sync.md`
- **Triggers**: daily schedule + manual (`workflow_dispatch`)
- **Engine**: Codex (15-minute timeout)
- **Safe outputs**: PRs prefixed with `[docs]`, labeled `documentation` + `automation`, auto-expire after 3 days

---

## Repository Layout

```
agentics/
├── skills/                      # Canonical portable Codex skills
├── agents/                      # Custom roles with inherited model settings
├── workflows/                   # Requested maintenance playbooks
├── references/                  # Canonical resources bundled per skill
├── catalog.json                 # Groups, dependencies, and resources
├── src/agentics_tools/           # Installer and portable helper runtime
├── tests/                       # Toolkit regression coverage
├── claude-commands/             # Claude Code slash commands (source of truth)
│   ├── commands/                #   /review, /refine, /suggest, /design, /daily, /ticket
│   ├── shared/                  #   Shared config and templates
│   └── Makefile                 #   deploy, diff, status
├── precommit-agentic-check/     # LLM-backed pre-commit gate (Python package)
│   ├── src/agentic_check/       #   CLI, providers, schema, git input
│   ├── tests/
│   └── .ai/prompts/             #   Policy prompt template
├── .github/
│   ├── workflows/               #   Agentic workflow sources (.md) + compiled (.lock.yml)
│   └── agents/                  #   GitHub Copilot agent dispatcher
├── CLAUDE.md                    # Guidance for Claude Code in this repo
├── AGENTS.md                    # Guidance for agentic coding assistants
└── LICENSE                      # MIT
```
