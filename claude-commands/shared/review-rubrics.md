# Review Rubrics — Shared Reference

> Consumers: `/review` (Deep Code Analysis, Exploratory Test Writing) and `/refine` (Fix Loop).
> These rubrics add DEPTH to existing finding categories and fix reasoning. They do NOT
> define new severities, phases, or output formats. Severity mappings below are fixed and
> use only labels from the `/review` Severity Legend (BUG, SECURITY, RETHINK, HYGIENE,
> MISSING_TEST, NITPICK).

<!-- RE-SYNC: the content below is borrowed (copied) from installed marketplace plugin
     agents — it is a one-time source library, not a runtime dependency. To re-sync after a
     plugin update: for each section, re-read the cited source file at the new highest-version
     dir under ~/.claude/plugins/cache/claude-code-workflows/<plugin>/, re-check each item
     against the current review.md / refine.md text (drop anything that has since become
     redundant), and bump the @version + synced: date in that section's provenance tag.
     Re-syncing never requires editing review.md or refine.md. -->

## Security Audit Checklist
<!-- source: claude-code-workflows/comprehensive-review@1.3.1 agents/security-auditor.md
     synced: 2026-06-22 -->

Severity: **SECURITY**. Applies to `/review` category 2 (Security). These EXTEND — they do
not replace — the category-2 checks already in `review.md` (SQL injection, unvalidated
input, hardcoded secrets, PII exposure, improper auth checks, OWASP Top 10):

- **Security headers**: missing or weak CSP, HSTS, X-Frame-Options, SameSite cookies, CORP/COEP.
- **Token & session**: JWT/token validation (signature, expiry, audience), key management,
  session fixation.
- **Output encoding**: contextual output encoding/escaping at sinks, treated as distinct
  from input validation (an input-validated value can still be unsafe at an unescaped sink).
- **Broken access control**: object-level authorization / ownership checks on every access
  (covers IDOR — missing per-object authorization).
- **Cryptographic failures**: weak/deprecated algorithms, hardcoded keys, missing key
  rotation, sensitive data stored in plaintext.

## Architecture Review Checklist
<!-- source: claude-code-workflows/comprehensive-review@1.3.1 agents/architect-review.md
     synced: 2026-06-22 -->

Severity: **RETHINK**. Applies to `/review` category 7 (Architecture). Extends the existing
checks (separation of concerns, coupling, layer violations, dependency direction, SRP):

- **Boundary violations**: changes that cross or blur module / service / bounded-context
  boundaries, or leak domain concepts across them.
- **Missing anti-corruption layer**: external-system or third-party integrations wired
  directly into domain code without an adapter / translation seam.
- **Impact rating**: for each architectural finding, state the architectural impact
  (High / Medium / Low) in the rationale.

## Exploratory Test Quality
<!-- source: claude-code-workflows/unit-testing@1.2.1 agents/test-automator.md
     synced: 2026-06-22 -->

Guidance for `/review` step 2g (writing temporary exploratory tests). Coverage gaps you
surface remain severity **MISSING_TEST**; this only improves the tests you write:

- **Fail for the right reason**: for any exploratory test that passes, confirm it would
  actually fail if the behavior under test were broken (guard against false-positive tests).
- **Behavior over implementation**: assert observable behavior / outputs, not internal call
  sequences or private structure, so the test survives safe refactors.
- **Risk-based**: prioritize by the test pyramid and risk — cover the highest-risk changed
  paths first rather than maximizing raw test count.

## Debugging Methodology
<!-- source: claude-code-workflows/error-debugging@1.2.1 agents/debugger.md
     synced: 2026-06-22 -->

Method for `/refine` Phase 2 when fixing **TEST** or **CI** items. This is HOW to derive a
fix; it does NOT add a phase, change the priority order, or introduce a severity:

1. Capture the error message and full stack trace.
2. Identify reliable reproduction steps.
3. Isolate the failure location.
4. Implement the **minimal** fix at the root cause (not the symptom).
5. Verify the fix resolves the failure.

State the root cause + supporting evidence + the fix + a prevention note.

## Error Correlation
<!-- source: claude-code-workflows/error-debugging@1.2.1 agents/error-detective.md
     synced: 2026-06-22 -->

For `/refine` CI-failure triage:

- Start from the symptom and work backward to the cause.
- Correlate the failure with recent changes on the branch (what landed just before it broke).
- Check for cascading failures (one root failure producing many downstream errors).

## Test Value Criteria (optional)
<!-- source: claude-code-workflows/unit-testing@1.2.1 agents/test-automator.md
     synced: 2026-06-22 -->

Optional extension to `/refine` task 1f (Test Value Analysis) — wire in only if desired
(adds criterion 6). Stays within 1f's "Conservative by default" rule:

6. **Implementation-detail assertion**: asserts a private/internal detail (exact call
   sequence, internal data shape) rather than observable behavior, so it breaks on safe
   refactors without catching real regressions.
