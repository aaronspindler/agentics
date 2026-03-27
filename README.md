# agentics

Personal Claude Code commands and shared reference files for AI-assisted development workflows.

## Commands

| Command | Description |
|---------|-------------|
| `/review` | Thorough code review engine -- checks out PR code, runs linters/tests, writes validation tests, produces a detailed report |
| `/refine` | Post-implementation refinement -- discovers issues, fixes them, updates PR, monitors CI |
| `/suggest` | Posts GitHub PR review comments with code suggestions from a prior `/review` report |
| `/design` | Generates design documents with 1-pager and numbered implementation tickets |

## Setup

Clone this repo and deploy to your Claude Code configuration:

```bash
git clone <repo-url>
cd agentics
make deploy
```

## Usage

After deploying, the commands are available as Claude Code slash commands in any project:

```
/review 123           # Review PR #123
/refine               # Refine current branch's PR
/suggest 1,3,5        # Post suggestions from a review
/design <description> # Generate a design document
```

## Development

Edit commands in this repo, then sync to `~/.claude/`:

```bash
make deploy   # Copy files to ~/.claude/
make diff     # See what changed
make status   # Check sync status
```

See [CLAUDE.md](CLAUDE.md) for detailed editing guidelines.

## License

MIT
