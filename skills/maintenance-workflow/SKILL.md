---
name: maintenance-workflow
description: "Select and run an explicitly requested repository maintenance playbook, or plan a separately authorized scheduler, without enabling recurring work implicitly."
---

# Maintenance Workflow

Read [repository context](references/repository-context.md), [workflow index](references/workflow-index.md), and [shared maintenance rules](references/automation-guidelines.md), then only the selected lane.

Resolve repository, author scope, validation commands, labels, discussion memory, timezone, integration coverage, and readiness rules from its repository guidance. Generic playbooks do not import another project's policy or authorize outbound writes. Missing required context blocks only dependent work.

Run one bounded work item per delegated worker when the selected playbook uses a dispatcher. Preserve lane markers, head/snapshot deduplication, source evidence, explicit write authority, lock ownership, and observed validation. Keep legacy deduplication aliases in the project guidance.

The [orchestrator](references/workflows/orchestrator.md) is an optional manual dispatcher contract. Installing these resources creates no scheduler, background job, memory discussion, label, issue, or PR. Configure recurring work only when requested through the host's supported automation tools. Preserve notification intent and stay quiet on unchanged non-actionable state for heartbeat monitors.
