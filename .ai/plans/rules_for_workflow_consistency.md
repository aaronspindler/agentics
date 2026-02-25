## Add Enforced Workflow Source Sync Rule to CLAUDE.md

  ### Summary

  Add a new explicit policy to CLAUDE.md requiring mirrored updates between workflows/ and .github/workflows/ whenever workflow source files are changed.
  Chosen policy: hard requirement (Always mirror both), not optional guidance.

  ### Planned Changes

  1. Update CLAUDE.md under Project Structure & Module Organization (or a nearby workflow-authoring section) with a new bullet that states:
      - Any add/edit/delete of workflow source files in workflows/ or .github/workflows/*.md must be applied to the corresponding file in the other location in the same
        change.
  2. Add a short enforcement note in Testing Guidelines (or Commit/PR section) requiring diff review to confirm both source locations were updated together before
     compile/commit.
  3. Keep existing compile and lockfile guidance unchanged (no change to .lock.yml handling).

  ### Public Interfaces / Contract Changes

  - Contributor policy contract change in CLAUDE.md:
      - New mandatory invariant: source workflow parity across both directories.
      - This changes contributor expectations for PR acceptance (documentation-level interface).

  ### Validation / Test Scenarios

  2. Edit an existing workflow source in .github/workflows/:
  3. Add a new workflow source:
      - Confirm counterpart file is removed in the other directory.
  5. Run existing validation flow:
      - gh aw compile --validate
      - gh aw compile
      - Diff review confirms intentional updates in both source locations and expected lock output.

  ### Assumptions and Defaults

  - Assumption: workflows in these two directories are intended to remain synchronized for published workflow usage.
  - Default wording style: imperative and explicit (“must”), aligned with current AGENTS conventions.
  - No exceptions are introduced in this first version; if exceptions are needed later, they should be explicitly documented.