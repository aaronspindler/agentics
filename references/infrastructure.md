# Infrastructure integration and rollout

Resolve service identity, management-host identity, and physical-host inventory from their distinct canonical owners. Adding a service to an existing host does not imply provisioning a host. Tracked SSH configuration does not prove credentials or connectivity.

Trace applicable consumers: runtime config/Compose, host defaults and profiles, DNS, human-facing endpoint catalog, metrics discovery, log shipping, uptime checks, status pages, and docs. Do not invent a web UI or telemetry endpoint for a headless service. External public routing may have a separate owner. Retirement must preserve shared hosts and consumers still in use.

For rollout, bind the exact stack, host set, operation, environment overlay, and artifact source. Distinguish remote Git-ref deployment, local file sync, local transfer, and runtime overlays. Unpublished local edits are absent from a helper that fetches a remote Git ref; do not silently substitute another ref or publish them. Inspect reconciliation effects and the complete desired-state diff, including deletion behavior.

Run native preflight before mutation. Provisioning, bootstrap, reboots, broad fleet targets, forced recreation, rollback, and ordinary deployment are distinct operations. Preserve native transport retries without adding a new mutation loop. After failure, report partial application and gather read-only evidence before proposing another operation.

Verify the selected artifact and service behavior on the actual target. Workstation-local process/Compose state cannot verify a remote workload. Static validators, behavioral tests, coverage, hosted CI, artifact identity, and protocol-level health provide separate evidence; report each honestly.
