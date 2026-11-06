---
name: cloudflare-ops
description: "Inspect Cloudflare Worker, Stream, routes, DNS, certificates, Access, and related provider state before scoped authorized recovery."
---

# Cloudflare Ops

Read [repository context](references/repository-context.md) and [read-first operations](references/live-ops.md).

1. Resolve the affected provider surface and expected ownership from project guidance. Inspect only relevant Workers, routes/domains, DNS/certificates, Access, Stream, Images, Email, analytics, or AI configuration.
2. Correlate provider deployment/artifact identity and GitHub release records with live routing and application evidence. Do not impose another project's domain or API ownership.
3. For Stream, correlate video status/UID, storage/delivery, webhook configuration, and signing-key metadata with application state and bounded logs. Never return direct upload URLs, signing private keys, webhook secrets, or tokens. Preserve documented upload/body routing contracts.
4. Separate confirmed drift, suspected drift, provider recovery, and code/workflow fixes. Apply only the smallest currently authorized recovery; installation or inspection grants no write authority.
5. Verify the result and stop after failure before changing strategy. Use rollout planning for compatibility-sensitive follow-up and update the canonical operator doc when source truth changed.
