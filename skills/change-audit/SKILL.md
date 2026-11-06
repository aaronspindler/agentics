---
name: change-audit
description: "Audit substantial changes read-only for cohesion, duplicated abstractions, documentation drift, and fidelity to the touched app's patterns."
---

# Change Audit

1. Read [repository context](references/repository-context.md), resolve the requested final diff/file set, and avoid unrelated existing work. Skip this audit when the change has no meaningful structural or interface surface.
2. Inspect relevant architecture and design owners and nearby components. Check partial pattern shifts, duplicate helpers, speculative frameworks, dead scaffolding, placement/naming, docs drift, and app-local frontend fidelity.
3. Preserve required security, authorization, retained data/provenance, accessibility, bounds, recovery, and meaningful tests; these safeguards are not bloat. Judge maintenance cost and behavior, not line count.
4. Return findings first with stable `AUDIT-NNN` IDs, severity/confidence, exact file/line, cost/impact, and smallest follow-up. Separate material defects from optional simplifications; say when no actionable issue exists.
5. Stay read-only across files, Git/GitHub, services, dashboards, and credentials. Do not run fixing hooks or drift into correctness-first review or implementation.
