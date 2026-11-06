---
name: pr-metadata
description: "Prepare and normalize GitHub PR titles, descriptions, issue/preview links, and existing labels using the target repository's conventions."
---

# Pr Metadata

Read [PR workflow foundations](references/pr-workflows.md) and [metadata conventions](references/pr-metadata.md).

1. Gather current branch/base/head, PR state, final diff/impact, project PR template, observed limitations, issue relationships, published previews, and existing labels.
2. Prepare exact title/body/labels before any write. Follow project formatting and path-label mappings; otherwise use a short outcome-focused description and only clearly supported labels.
3. Preserve intentional user-authored context and valid issue qualifiers. Use closing keywords only for completed work. Add preview links only after native attachments or the stable marker comment exist.
4. Keep labels, placeholders, raw output, private memory citations, and unsupported success claims out of the body. Respect project rules separating validation from PR prose.
5. Perform only the already-authorized metadata write. Metadata-only edits do not invoke a mutating branch publication gate or grant auto-merge permission.
