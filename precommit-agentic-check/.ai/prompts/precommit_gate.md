Review the staged changes for correctness, maintainability, and security risks.

Policy:
- Flag concrete defects or risky patterns.
- Avoid style-only feedback unless it causes real maintenance risk.
- Keep findings actionable and specific to changed code.

Output expectations:
- Return pass only when no meaningful risks are found.
- Return fail when at least one concrete issue is found.
- Provide precise recommendations that can be implemented quickly.
