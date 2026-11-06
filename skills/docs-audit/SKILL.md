---
name: docs-audit
description: "Audit repository documentation read-only for factual drift, duplicated guidance, stale commands, and missing ownership."
---

# Docs Audit

1. Read [repository context](references/repository-context.md), discover canonical routers/inventories and requested docs, and trace claims to owning config, code, Make targets, tests, and capability definitions.
2. Check path/link validity, command execution location, prerequisites/side effects, local versus remote behavior, removed automation, and overstated validation or live-health guarantees.
3. Prefer one owning explanation with concise pointers over duplicated policy. Distinguish durable docs from issue-owned backlog and transient notes according to project policy.
4. Return stable `DOC-NNN` IDs with target-doc and supporting-source lines, impact/confidence, and proposed owning correction. Say when no actionable drift exists and state reviewed scope/limits.
5. Stay read-only; do not edit files, run rewriting hooks, publish findings, probe live APIs merely to validate prose, or recreate missing automation. Assign requested repairs to a separate maintenance action.
