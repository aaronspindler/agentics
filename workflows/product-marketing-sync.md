# Product marketing sync workflow

Read [repository context](../repository-context.md) and [shared maintenance rules](../automation-guidelines.md). Resolve the product name, allowed marketing paths/tests, copy owner, design/product docs, excluded implementation areas, validation and performance commands, and legacy workflow markers from the target repository guidance. If the allowed path set is unresolved, stop before editing.


Memory backends, readiness labels, PR-body policy, budgets, and output destinations follow repository guidance. Discussion names and marker schemas below are GitHub-adapter defaults only when that adapter is selected; retain local legacy aliases. A capability described as permitted by this lane still requires current user/host authorization.

## Scope and evidence

Keep public marketing copy, navigation, metadata, sitemap, FAQ, pricing/plan language, and canonical redirects aligned with shipped product truth. Inspect actual routes, user-visible labels, supported features, and product models read-only before choosing a claim. Do not advertise planned, partially implemented, manually enabled, or unsupported capabilities as generally available.

Use one bounded worker per drift group and inspect open PRs/issues and active workers first. Limit writes to configured marketing surfaces and their coupled tests. Do not change product implementation, agent capabilities, schedulers, dependencies, unrelated apps, or provider configuration to make marketing claims true.

## Memory and output

Use `Automation Memory - Product Marketing Sync` and `<!-- automation-memory:id=product-marketing-sync -->` for standalone memory unless the project guidance preserves an existing title/marker. Orchestrated runs return state to central memory. Search current and configured legacy issue/PR markers before creating another item; new issue keys use `<!-- product-marketing-sync:key=<normalized-key> -->`.

## Workflow

1. Compare canonical marketing copy, public navigation, metadata/social cards, sitemaps, canonical/redirect behavior, and narrow/mobile presentation with verified product behavior and app-local design.
2. Select at most one high-confidence drift group. Create or refine a deduplicated issue when product intent or shipped behavior is uncertain; do not guess pricing, legal, security, or product promises.
3. Within existing authorization, make the smallest complete copy/navigation/SEO change and meaningful tests. Preserve established branding, accessibility, canonical ownership, and product vocabulary.
4. Run configured targeted checks, route/navigation integration tests when relevant, and advisory performance checks without treating advisory output as a new hard gate.
5. Capture relevant before/after previews through the project adapter. Publish native attachments only when authorized, then separately refresh PR metadata with published URLs. Keep local captures ignored.
6. Publish a validated bounded PR only within current write authority, or return the local result/deduplicated issue and blocker. Report claims verified, exact validation, remaining unknowns, and outcome key. Do not monitor pending CI unless requested.
