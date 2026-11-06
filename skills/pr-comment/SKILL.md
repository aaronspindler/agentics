---
name: pr-comment
description: "Publish selected findings from a prior review report to the matching GitHub PR head, after preparing exact outbound comments."
---

# Pr Comment

Read [PR workflow foundations](references/pr-workflows.md).

1. Require a prior review report with unambiguous finding IDs and reviewed SHA. Resolve the PR from that report and confirm its current head still matches; otherwise refresh review before publishing.
2. Skip findings already posted using stable review markers such as `<!-- review-001 -->`. Never manufacture new findings in this posting workflow.
3. Prepare exact comments. Use inline locations only when the line remains valid in the current diff; otherwise use a general comment. Use a suggestion block only for an exact valid replacement span.
4. Show the concrete outbound comments before posting. The source workflow requires explicit confirmation for publication; reuse explicit approval already supplied for those exact comments, otherwise wait for it before the write.
5. Recheck head and deduplication immediately before publishing. Do not edit code, alter review scope, or post duplicates. Report published links and any skipped/stale finding.
