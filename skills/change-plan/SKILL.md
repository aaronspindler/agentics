---
name: change-plan
description: "Choose a complete implementation boundary before changing behavior, interfaces, persisted state, service wiring, or operator workflows."
---

# Change Plan

1. Read [repository context](references/repository-context.md) and trace entrypoints, callers, configuration consumers, and owning guidance before editing.
2. Classify the compatibility surface: internal helper, public API/route, template and browser code, serialized state/schema, deployment, or workflow. Update coupled layers and references together.
3. Prefer the simplest complete change over speculative frameworks, duplicate helpers, aliases, or shims. Preserve real released contracts, data, required safeguards, and rollback/recovery needs; use compatibility stages where they are necessary.
4. For infrastructure identity changes, include existing DNS, endpoint, telemetry, and host consumers. For destructive migrations, separate runtime removal from incompatible schema removal across releases when older code can still run.
5. State the selected boundary, coupled edits, compatibility/rollout impact, and smallest meaningful validation. Planning does not authorize publication or deployment. Use runtime investigation first when the failure path is uncertain.
