# Repository context

Read the active checkout's `AGENTS.md` and applicable scoped instructions. Follow their authoritative documentation links and owning repository documentation; this library does not require a particular docs directory, build system, or hosting stack. Reuse unchanged context already read in the session.

Identify the actual repository, branch, base, diff, runtime, working directory, and affected consumers. Read canonical service/host inventories separately when identity matters. Tracked desired state, passing static validation, deployed artifact identity, and live functional health establish different facts.

Discover commands from owning manifests, Make targets, task runners, and existing tests. Inspect prerequisites and side effects before running a purported read-only command. Follow the repository's interpreter, environment, container, full-stack testing, and lint policies; do not install ambient dependencies or substitute host commands for required containers.

User authorization and preferences persist. Carry out the authorized task without asking again at each skill boundary. Installing or reading a skill grants no additional permission. Preserve unrelated changes. Read-only roles do not edit files or mutate any external state, including through helper prerequisites. Planning, diagnosis, validation, draft handoffs, and local configuration work do not by themselves authorize deployment or publication.

Keep project-specific commands, paths, authors, timezone, labels, issue/PR templates, release targets, credentials references, and external project identifiers in the target repository's owning guidance. Missing configuration blocks only actions that depend on it. Complete independent preparation and describe the exact missing fact; do not guess deployment targets, broaden authors, or fall back to a different external system.

Never reproduce credentials, private records, raw secret-bearing logs, or historical private agent memory. Respect the target repository's public/private configuration policy rather than declaring every tracked environment file a defect. Preserve required authorization, provenance, retained originals, accessibility, resource bounds, and recoverable failures when applicable.

Named skills and specialist roles are optional routing aids unless the target task explicitly requires one. If a referenced capability is not installed, the parent may perform the equivalent scoped preparation, evidence gathering, or validation while preserving its read-only and authorization boundaries. Do not invent an unavailable tool or broaden the task to install it.
