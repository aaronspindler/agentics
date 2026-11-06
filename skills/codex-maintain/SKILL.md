---
name: codex-maintain
description: "Maintain shared or repository-local Codex skills, roles, workflow playbooks, installation metadata, and capability routing consistently."
---

# Codex Maintain

1. Read [repository context](references/repository-context.md), identify the owning source catalog/installer or local capability directory, and inspect consumers before editing shared resources.
2. Keep reusable behavior in its canonical skill/reference/role/workflow, and project paths/commands/IDs in target-repo guidance. Preserve installed provenance, managed-file ownership, and explicit update behavior; never edit generated managed copies as source.
3. Keep skill folder/frontmatter names, UI prompts/policies, resource mappings, catalog dependencies, and routers consistent. Preserve invocation policies; do not infer explicit-only selection from sensitive operations.
4. Shared read-only agents inherit caller model/reasoning and permissions while their instructions preserve read-only behavior. Do not import another machine's sandbox roots, MCP endpoints, credentials, or model pins.
5. Validate YAML/TOML/JSON, links, installed-resource closure, catalog selection, and relevant installer behavior. Removed schedulers stay removed: installation and playbook maintenance do not enable recurring jobs or outbound writes.
