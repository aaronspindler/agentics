---
name: stack-rollout
description: "Apply an already-authorized deployment or bootstrap through the owning workflow, exact host set, and artifact source, then verify the actual target."
---

# Stack Rollout

1. Read [repository context](references/repository-context.md), [infrastructure contracts](references/infrastructure.md), and the target stack's deployment instructions.
2. Bind exact operation, hosts, runtime environment, artifact ref/source, and execution location. Resolve missing target/artifact decisions before dependent mutation; finish independent preparation meanwhile.
3. Prepare the concrete change and run native preflight. Explain unpublished local changes that a fetched-ref deployment cannot deliver; never silently substitute another ref or publish it.
4. Execute only the authorized operation through its native workflow. Deployment does not imply publication, provisioning, broad maintenance, reboots, rollback, force recreation, or fleet expansion. Reuse authorization already supplied.
5. Preserve native retries; stop on execution failure, collect read-only evidence, and report partial application before choosing a different mutation. Verify artifact identity and service-specific behavior on the actual target with bounded logs/protocol checks.
6. Report intended/observed hosts/artifacts, commands, outcomes, live checks, and remaining gaps. Local Compose or static validation is insufficient evidence for a remote rollout.
