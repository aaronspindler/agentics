# Design Document Templates

> **Consumers**: `/design`. Changes here affect the output format of all generated design documents.

---

## 1-Pager Template

Use this structure when generating a design 1-pager. All sections are required unless marked optional. Sections should appear in this order.

```markdown
# <Project Title>

**Date**: <YYYY-MM-DD>
**Author**: <author name>
**Status**: Proposal

---

## Problem Statement

Describe the business or technical problem. Include:
- What exists today (current state)
- What's wrong or missing
- Why it matters now

If helpful, use a Current State / Future State table:

| Current State | Future State |
|:---|:---|
| ... | ... |

Or a component summary table:

| Component | Details |
|-----------|---------|
| ... | ... |

**Goals:** Bullet list of specific, measurable objectives.

---

## Proposed Solution

Narrative explanation of the recommended approach. Include:
- **Why this approach** — architectural principles, idiomatic patterns
- Architecture diagram (ASCII art showing data flow, components, and relationships)

```
[ASCII architecture diagram here]
```

---

## Alternatives Considered

### Option N: <Name>

#### How It Works
Narrative explanation.

#### Level of Effort
**~X-Y days**

| Work Item | Effort |
|-----------|--------|
| ... | ... |

#### Application Code Changes
What code changes are needed (or "None").

#### Pros
- Bullet list

#### Cons
- Bullet list

(Repeat for each alternative. Minimum 2 options.)

---

## Comparison Matrix

| Criteria | Option 1: <Name> | Option 2: <Name> |
|----------|-------------------|-------------------|
| **Effort** | ... | ... |
| **Code changes** | ... | ... |
| **Solves core problem** | ... | ... |
| **Throwaway work** | ... | ... |
| **Additional infra cost** | ... | ... |

---

## Recommendation: <Option Name>

### Why <Option Name>
Concise rationale referencing the comparison matrix.

### Why <Sub-Decision> (if applicable)
For architectural sub-decisions within the recommended option.

### Why the Effort Is Low / Manageable (if applicable)
Bullet list explaining effort drivers.

### Phased Approach

| Phase | Action | Effort | Outcome |
|-------|--------|--------|---------|
| **Phase 1** | ... | ... | ... |
| **Phase 2** | ... | ... | ... |

---

## In Scope / Out of Scope

### In Scope
- Bullet list

### Out of Scope
- Bullet list

---

## Key Design Decisions

Document decisions and their rationale. Use either narrative subsections or a table:

| # | Decision | Rationale |
|---|----------|-----------|
| 1 | ... | ... |
| 2 | ... | ... |

---

## Implementation Breakdown (added after ticket generation)

### Ticket Summary

| # | Title | Component | Effort | Dependencies |
|---|-------|-----------|--------|--------------|
| 001 | ... | ... | X-Y days | None |
| 002 | ... | ... | X-Y days | Blocked by 001 |

**Total Estimated Effort: X-Y days**

### Dependency Graph

```
[ASCII dependency diagram]
```

### Recommended Execution Order
1. Ticket NNN — reason for ordering
2. ...

---

## Files Modified/Created

### New Files

```
project/
└── path/to/
    └── new_file.py
```

### Modified Files

```
project/
└── path/to/
    └── existing_file.py    (description of change)
```

---

## Risks & Considerations

| Risk | Mitigation |
|:---|:---|
| ... | ... |

---

## Open Questions

- [ ] Question 1
  - **Resolved**: Answer (if resolved)
- [ ] Question 2

---

## Success Criteria

- [ ] Criterion 1
- [ ] Criterion 2
- [ ] All unit tests pass
- [ ] E2E validation complete
```

### 1-Pager Content Guidelines

- **Architecture diagrams**: Use ASCII art with box-drawing characters and arrows. Label components with ticket numbers where applicable.
- **Code examples**: Include inline code showing exact file paths, function signatures, type hints, and docstrings. Mark with `# File: <path>` comments.
- **Tables**: Use markdown tables for structured comparisons. Align columns with `:---` for left, `:---:` for center.
- **Specificity**: Include exact enum values, configuration keys, default values, column types, batch sizes, and edge cases. Never use vague placeholders.
- **Cost estimates**: When infrastructure changes are involved, include a monthly cost table with component breakdown.
- **LOE format**: Always express as ranges (e.g., "2-3 days", "~1 developer-week"). Include a work item breakdown table.

---

## Ticket Template

Use this structure when generating implementation tickets. All sections are required unless marked optional.

```markdown
# Ticket <NNN>: <Title>

**Estimated effort**: X-Y days
**Component**: <sub-project name>

---

## Description

Natural language explanation of what needs to be built. Reference the parent 1-pager:
> See [one-pager.md](../one-pager.md) for full context.

---

## Acceptance Criteria

- [ ] AC1: <specific, testable criterion>
- [ ] AC2: <specific, testable criterion>
- [ ] AC3: <specific, testable criterion>

---

## Technical Details

### AC1: <Title>

**File:** `<exact path from repo root>`

<Implementation details with code examples>

```python
# File: <path>
<code with type hints, docstrings, and comments>
```

**Tests:**
- Test description 1
- Test description 2

### AC2: <Title>
(repeat for each AC)

---

## Files to Create/Modify

### New Files

```
project/
└── path/to/
    └── new_file.py
    └── tests/test_new_file.py
```

### Modified Files

```
project/
└── path/to/
    └── existing_file.py    (description of change)
```

---

## Dependencies

- **BLOCKED BY**: Ticket NNN (reason)
- **Required on Main**: <list of PRs/features that must be merged first>

Or "None" if no dependencies.

---

## Testing

- Unit tests: <what to test, where>
- Integration tests: <if applicable>
- Edge cases: <specific scenarios to cover>
```

### Ticket Content Guidelines

- **Numbering**: Sequential (001, 002, ...) reflecting recommended execution order.
- **Filenames**: `<NNN>-<kebab-case-title>.md` (e.g., `001-add-user-auth-endpoint.md`).
- **Acceptance criteria**: Each must be independently testable. Use checkbox format `- [ ]`.
- **Code examples**: Show the exact implementation — function signatures with type hints, class structures, SQL queries, config changes. Include file path comments.
- **Dependencies**: Distinguish between hard blocks (BLOCKED BY — cannot start until dependency completes) and soft dependencies (Required on Main — must be merged before this can merge).
- **Effort**: Express as ranges. Include both implementation and testing time.
- **Test coverage**: Every AC should have corresponding test descriptions. Reference test file paths.
- **Edge cases**: Call out explicitly — NULL handling, empty collections, sentinel values, timezone issues, constraint collisions.
