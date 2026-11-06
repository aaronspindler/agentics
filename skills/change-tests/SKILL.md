---
name: change-tests
description: "Add focused regression coverage for changed behavior or a concrete test gap, using the target repository's test framework."
---

# Change Tests

1. Read [repository context](references/repository-context.md). Start from the actual diff, trigger, and neighboring tests; identify the behavior or integration seam at risk.
2. Add the narrowest stable test that fails for the bug or protects the changed contract. Assert meaningful outcomes rather than implementation wording; preserve unique existing assertions even when setup resembles another test.
3. Use deterministic unit fixtures for remote APIs and transport. Use the repository's real full-stack policy for user-flow coverage; do not substitute mocked backends where the project requires integration evidence.
4. Configuration-only changes may need native validators instead of invented test scaffolding. Do not expand into unrelated coverage campaigns.
5. Run focused tests through the approved interpreter/container workflow. Explain targeted-test results separately from full-suite coverage; overridden coverage options do not establish the full gate. Broaden checks only for coupled paths or unresolved failures.
