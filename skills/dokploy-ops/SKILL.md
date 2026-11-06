---
name: dokploy-ops
description: "Inspect Dokploy-managed application, routing, scaling, and managed-service state before narrowly scoped authorized recovery."
---

# Dokploy Ops

Read [repository context](references/repository-context.md) and [read-first operations](references/live-ops.md).

1. Discover available Dokploy read tools and inspect project/application state, monitoring, routing/certificates, and affected managed database/cache configuration.
2. Compare actual image/rollout, replicas/placement, domains, service arguments, protocol health, and fresh error evidence with the repository's owning deployment contract.
3. Separate confirmed drift, suspected drift, provider recovery, and source changes. Use exact timestamps/SHAs/service references without credentials or private payloads.
4. Only apply a recovery covered by current authorization, using the smallest redeploy, reload, or targeted configuration update. Inspect helper side effects and do not infer automatic reconciliation.
5. Stop on recovery failure and report partial state before another mutation strategy. Do not perform teardown unless explicit. Route compatibility planning and operator-doc repair to their owning workflow.
