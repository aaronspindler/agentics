---
name: observability-diagnosis
description: "Diagnose observed service health using bounded metrics, logs, application checks, and host evidence without changing monitoring or services."
---

# Observability Diagnosis

Read [repository context](references/repository-context.md) and [bounded observability](references/observability.md).

1. Resolve symptom, service/host, observation interval, and expected telemetry from owning inventories/configuration.
2. Discover available read-only provider/Grafana tools and datasource labels; otherwise use established non-mutating API/SSH checks after inspecting prerequisites. Do not install/reconfigure access to manufacture evidence.
3. Check freshness/coverage before interpreting results. Bound queries and distinguish application health, scrape health, ingestion, resource pressure, and externally managed routing.
4. Test the failing protocol directly and correlate only configured signals. Empty/stale evidence is a gap, not proof of health.
5. Return timestamps/timezone, source/query identity, impact, supported diagnosis/confidence, alternatives, gaps, and next discriminating check. Stay read-only, including dashboards, alerts, issues, credentials, and services. Use local runtime investigation for a narrow command/config failure.
