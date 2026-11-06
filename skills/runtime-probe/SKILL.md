---
name: runtime-probe
description: "Reproduce an uncertain runtime, command, configuration, validator, CI, or browser failure and trace evidence before choosing a fix."
---

# Runtime Probe

1. Read [repository context](references/repository-context.md). Resolve the failing command/input/route, working directory, runtime, host, artifact source, and expected outcome.
2. Choose the smallest non-mutating or isolated repro through approved validators/tests, exact CI logs, browser evidence, or bounded service reads. Inspect command prerequisites before calling status/log helpers.
3. Do not replay deploy, push, bootstrap, reload, or maintenance commands just to reproduce a symptom. Use an isolated fixture or inspect their implementation unless that operation is already authorized.
4. Trace owning entrypoints, callers, shared helpers, config, and relevant data shapes. Separate code/config defects, command environment failure, connectivity, and live-service failure.
5. Return observed result, supported cause or hypothesis, evidence, confidence, and a falsifying check. Keep secrets redacted. Use a focused change plan once the cause supports a repair; use bounded observability when the question needs broader telemetry correlation.
