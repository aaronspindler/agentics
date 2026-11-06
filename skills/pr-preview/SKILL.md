---
name: pr-preview
description: "Capture relevant before/after frontend screenshots through a repository adapter and publish native GitHub attachments with provenance and one owned preview comment."
---

# Pr Preview

Read [PR workflow foundations](references/pr-workflows.md) and the [preview contract](references/preview.md).

1. Confirm a visible UI change or explicit preview request. Discover the target repository's route registry and capture adapter; do not assume a particular app or test harness. The shared helpers manage files, provenance, and publication; they do not capture screenshots. If a capture adapter or browser access is unavailable, finish feasible preparation and report capture unavailable without inventing PNGs.
2. Select relevant desktop/mobile before/after states when feasible. Use `agentics tools --repo-root PATH preview` to resolve branch paths and take a source snapshot before rendering; record provenance after both targeted/full-page PNGs exist.
3. Keep PNGs and metadata ignored and untracked. Verify actual artifacts before claiming capture. Follow repository real-stack/test/environment policy.
4. Publish only within existing authorization using `agentics tools --repo-root PATH preview-sync`. Enforce matching PR head, account ownership, native-upload prerequisites, unchanged-content cache, duplicate prevention, and capture provenance.
5. Fetch published URLs for a separate authorized metadata update. `preview clean` removes only local artifacts; `preview-sync --delete` requires an explicit comment-deletion request. Missing captures never imply deletion.
