# CHECKPOINT Protocol

A CHECKPOINT is a mandatory approval gate before any external write (disk, GitHub, ClickUp). Every command that modifies state must pause here.

## Gate

Present a rendered preview of the proposed changes inside a fenced box, then display:

```
Proceed? (yes / adjust / skip)
```

**Wait for explicit user input** before writing. Never interpret silence or ambiguity as `yes`.

## Option Semantics

- **`yes`** — Proceed to the write phase without changes.
- **`adjust`** — Ask the user what to change. Apply the adjustment, re-render the full proposal, and ask again. See per-command section for specializations (some commands distinguish display-level adjustments from data-level adjustments that require a subagent re-run).
- **`skip`** — Stop. Do **not** write, post, or modify anything — no files on disk, no GitHub comments, no ClickUp updates. Per-command sections document any exceptions where earlier writes have already occurred and are preserved regardless.

## Display Convention

```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  {COMMAND} — {descriptor}
  Target: {path or URL}
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

{stats / counts}

{proposed content in ─ sub-boxes as needed}

Proceed? (yes / adjust / skip)
```

## Invariants

1. Always wait for explicit input — never auto-advance past a CHECKPOINT.
2. After every `adjust`, re-render the full proposal before asking again.
3. `skip` leaves no side effects by default.
