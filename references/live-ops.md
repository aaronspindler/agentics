# Read-first operations

Read [repository context](repository-context.md), then the affected service's current deployment and operator contract. Verify service/host identity, artifact source, expected routing, and actual execution location. Use provider reads, deployment records, health checks, and bounded telemetry before proposing recovery.

Separate source expectations, timestamped live facts, and hypotheses. Return exact service/route identifiers and SHAs when useful, while redacting credentials, private payloads, upload URLs, signing keys, and unrelated personal data. A missing metric or unavailable provider read is an evidence gap, not proof of health or outage.

Inspect helper prerequisites: commands named status/logs may still change local permissions, sync config, or reconcile services. In a read-only investigation, use established non-mutating transport or report the blocked check.

Carry out live mutation only when covered by the user's instruction or active lane contract. Reuse existing authorization; finish concrete preparation before asking for a missing action. Prefer one narrow recovery, verify its result, and stop on failure before changing the mutation strategy. Do not add automatic redeploy, force-recreation, rollback, provisioning, maintenance, or reboot loops.

Separate operator recovery from source changes and rollout planning. Apply schema changes through the target project's compatibility and expand/contract rules; never treat transient restoration as proof that the code or deployment contract is repaired.
