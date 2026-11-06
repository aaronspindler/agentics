---
name: change-verify
description: "Choose and run the smallest repository-approved checks after implementation, tests, documentation, skills, configuration, or workflow changes."
---

# Change Verify

1. Read [repository context](references/repository-context.md), inspect changed files and owning manifests/targets, and classify docs, config, runtime, migration, frontend, and build effects.
2. Run required file-scoped lint and native validation. Hooks can rewrite files: respect the task's mutation boundary, inspect resulting changes, and rerun affected checks. Use all-file checks when shared lint configuration changed.
3. Follow project commands, execution location, environment, container, and full-stack rules. Use migration-graph/schema checks for migration edits and relevant asset builds when their inputs change.
4. Reuse green evidence only while checked files, config, dependencies, runtime, and other material inputs remain unchanged. Expand for new changes, failures, or unresolved concerns; avoid repeating unrelated green suites.
5. Report exact commands, context, pass/fail/skip results, and limits. Distinguish static validation, behavior, coverage, CI, deployed identity, and live health. Verification alone does not authorize deployment or Git/GitHub publication.
