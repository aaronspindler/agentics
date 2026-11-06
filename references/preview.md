# PR preview contract

Capture uses the target repository's deterministic browser/full-stack adapter, route registry, setup, and validation policy. Do not copy another project's seeds or test harness. Select relevant before/after desktop/mobile states when feasible; a single current-state preview is valid when that is all the task supports.

Use `agentics tools --repo-root PATH preview` for `id`, `path`, `dir`, `list`, `snapshot`, `record`, and `clean`. Take `snapshot` before rendering and pass it as `--source-snapshot` to `record` after the PNGs exist. The helper must reject source changes during capture. Keep artifacts, `captures.json`, and `attachments.json` under the helper-resolved ignored branch directory. Never commit preview PNGs.

Publish with `agentics tools --repo-root PATH preview-sync --repo OWNER/REPO --pr NUMBER`, adding `--branch` when needed. Native publication supports GitHub.com, requires supported user authentication, repository write access, GitHub CLI 2.99.0+, and regular PNG files at most 10 MiB each. Inspect prerequisites without exposing tokens.

Local HEAD must match the PR head before publication and remain unchanged through writes. Use one `<!-- codex-pr-preview -->` comment owned by the active account; block foreign-owned markers and consolidate owned duplicates. Cache unchanged uploads by content hash and repository numeric identity, retain partial upload progress, and bind each published image to verified capture provenance or explicitly report unavailable provenance.

Fetch published attachment/comment URLs before updating PR metadata. Do not publish repository blob/raw PNG URLs. Local `preview clean` preserves uploaded attachments and comments. Missing captures are not a deletion request. Only explicit `preview-sync --delete` removes the active account's marked comment; attachments remain.
