---
name: service-integration
description: "Align service and host identity, endpoints, inventories, DNS, human-facing links, and applicable telemetry during addition, relocation, or retirement."
---

# Service Integration

1. Read [repository context](references/repository-context.md) and [infrastructure contracts](references/infrastructure.md). Resolve service, management host, and physical-host identities separately from canonical sources.
2. Trace runtime configuration, host defaults/profiles, DNS, endpoint catalogs, metrics discovery, log shipping, uptime/status references, and owning docs. Include only integrations actually supported by the service.
3. Apply the requested local configuration consistently. Reuse existing host identities; do not invent a VM, UI, metrics endpoint, or public-route ownership. On retirement preserve shared hosts and consumers still used elsewhere.
4. Inspect the full desired-state reconciliation diff, including removals, before any later rollout. Run the relevant native validators; a passing inventory validator does not prove every DNS or telemetry consumer is covered.
5. Report identities/endpoints, consumers changed, observed checks, and deployment dependencies. Local integration does not authorize provisioning, deployment, or external routing changes.
