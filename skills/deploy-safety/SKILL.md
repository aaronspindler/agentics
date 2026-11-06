---
name: deploy-safety
description: "Plan compatible rollout, migration, startup, infrastructure, and live-service boundaries before deployment-sensitive work."
---

# Deploy Safety

1. Read [repository context](references/repository-context.md) and [infrastructure contracts](references/infrastructure.md), then the target project's actual deployment contract.
2. Identify old/new runtime compatibility, destructive schema or serialized-state changes, startup/migration owners, artifact provenance, rollout ordering, pause/force controls, routes, replicas, and service dependencies.
3. Choose one compatible release, staged expand/contract releases, or source change plus explicit operator follow-up. Do not combine destructive removal with runtime removal when old processes may still observe the schema.
4. State the exact implementation/rollout boundary, native preflight, postdeploy evidence, manual actions, and recovery limitations. Do not assume provider reconciliation covers every manifest field.
5. This skill plans rather than applies the rollout. Continue independent preparation; pause only a dependent operation missing a concrete compatibility/product choice or authorization.
