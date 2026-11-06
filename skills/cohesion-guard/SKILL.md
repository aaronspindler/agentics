---
name: cohesion-guard
description: "Keep feature, interface, and reusable component changes cohesive with the target application's established behavior and design."
---

# Cohesion Guard

1. Read [repository context](references/repository-context.md), resolve touched apps/routes/components/APIs and meaningful user states, and inspect relevant design guidance plus nearby implementations.
2. Trace existing shared helpers/components before adding another path. Reuse established patterns where they fit; do not introduce a general abstraction without current consumers.
3. Keep loading, empty, error, permission, success, and narrow-viewport states consistent across coupled surfaces. Check naming, validation, navigation, accessible interaction, and product copy together.
4. Preserve each app's own design system rather than enforcing visual uniformity across unrelated products. Keep implementation commentary out of user-facing product copy unless it helps a product decision.
5. Maintain one complete implementation path and update consumers together. For trivial non-interface edits, skip this guard. Use a read-only final audit for substantial changes instead of broadening implementation scope.
