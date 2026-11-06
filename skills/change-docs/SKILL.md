---
name: change-docs
description: "Update canonical documentation when the current implementation changes behavior, architecture, operator commands, or agent workflows."
---

# Change Docs

1. Read [repository context](references/repository-context.md) and decide whether the change makes existing instructions misleading. Routine internal fixes may need no documentation.
2. Discover the existing owner: root/scoped instructions, user overview, architecture, app/stack operator guide, or capability definition. Edit the owner in place and keep routers concise.
3. Verify commands against their Make/task/script implementation, including working directory, interpreter, local/remote execution, artifact source, prerequisites, side effects, and actual automatic hooks.
4. Remove contradictory or unsupported claims rather than layering caveats. Do not change implementation, recreate removed automation, or deploy simply to match stale prose. Keep mutable inventory facts in their canonical owner.
5. Validate changed docs/metadata as appropriate and report corrected behavior and evidence. Broader documentation audits/maintenance remain separate from branch-local documentation sync.
