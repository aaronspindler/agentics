# PR handoff and metadata

Use the target repository's PR template and documented title/body/label conventions. Keep personal or product-specific formatting policy in its owning documentation. If no format is specified, lead with the concrete problem and resulting behavior, then concise relevant validation and material limitations. Use a short sentence-case title; scale detail to the change.

Gather the final branch/base/head, actual diff, operator/user impact, exact issue links, observed validation, and published preview links. Describe the final implementation for a reviewer without conversation context. Omit private memory citations, secret values, abandoned approaches, speculative claims, and local artifact paths.

Use closing keywords only when the change completes an issue; otherwise reference it, preserving cross-repository qualification. Use existing repository labels only, with path/product mappings only when the target project defines them. Do not create a new label taxonomy during metadata normalization or imply auto-merge permission.

Include preview links only after native attachments or the marked preview comment exist. Create a new PR without placeholders, then update its metadata after authorized preview publication. Preview synchronization itself does not edit the PR body.

Prepare exact title, body, and labels before an authorized metadata write. Keep validation in the operator handoff when the project's PR-body policy excludes it. Drafting a handoff does not authorize Git/GitHub writes.
