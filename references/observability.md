# Bounded observability

Identify service/host and absolute time range/timezone. Start with the last hour for an unspecified active incident, or the last 24 hours for an unspecified daily review. Narrow as evidence allows.

Discover available read-only telemetry tools and datasource identity. Do not install tools or reconfigure MCP, credentials, dashboards, datasources, alerts, or monitors to obtain evidence without separate authorization. Internal service ports do not imply workstation reachability; use established read-only transport when necessary.

Check telemetry freshness, label coverage, query scope, and configured ingestion before inferring health. Bound queries by service/host, time interval, result limit, and sample step. Missing series, stale samples, or absent logs do not establish health. Separate application availability, exporter scrape health, and log ingestion.

Test the failing protocol directly: HTTP uptime does not establish DNS resolution or another protocol's functionality. Correlate relevant metrics and bounded logs only where configured. Distinguish desired source wiring, observed facts, hypotheses, impact, confidence, competing causes, and the next discriminating probe. Redact credentials and private payloads.
