# Shared maintenance rules

These rules apply to explicitly requested manual playbooks or a separately enabled scheduler. Installation creates no recurring job, permission grant, memory store, labels, or external artifacts. Read [repository context](repository-context.md), then only the selected lane.

## Startup

- Resolve repository, authorized identity/author scope, exact work item, owning docs, validation commands, target branches, and external integration coverage from the current project and request. Follow its shell/environment policies.
- Reuse user authorization already supplied; a lane's permitted operation describes its capability, not authority to perform it. Establish which file/Git/GitHub/memory/live operations are actually authorized before dependent writes.
- Manual runs use the current checkout unless the user requests isolation or the operation requires a safe worktree. Explicitly enabled unattended code changes use isolated branches/worktrees under their host contract.
- Verify authentication and intended repository before GitHub operations. Discover the repository's backlog owner, not a universal issue policy. Missing configuration/access blocks only dependent work.

## Run Locks

- Keep a JSON ownership record at the lane's lock path across the entire protected run. Before acquisition, obtain a unique run token and a host-verifiable owner identity: the specific scheduler run/turn ID, or a dedicated agent PID plus process-start identity. A recurring task ID, shared app-server PID, transient tool-shell PID, or lock age is not sufficient owner evidence. If lifecycle verification is unavailable, report a blocker before acquiring.
- Serialize ownership checks, acquisition, recovery, and release with a short-lived Python `fcntl.flock(LOCK_EX | LOCK_NB)` on `<lock-path>.guard`. Keep that guard file in place; never unlink or replace its inode. Release the advisory guard after each ownership operation; the JSON record retains ownership between agent tool calls.
- Under the guard, read the current record and publish a complete new record only when the path is absent or the exact previous owner is proven terminated with its protected calls drained. Write a unique temporary sibling file, then publish it with atomic `os.replace`; never create an empty lock directory or partially write the published record. Begin protected work only after publication succeeds. A crash before publication leaves no new owner; a crash afterward leaves a complete record that the next run can reclaim.
- A busy guard or a confirmed active owner means another run holds the lock: stop without error. Reclaim a terminated owner's record automatically under the same guard, distinguishing PID reuse by process-start identity. Unknown lifecycle state, legacy directories, malformed records, and permission errors are blockers; leave them untouched and report the missing evidence. Age alone must never authorize reclamation.
- Before each protected operation, verify the record still matches this run's token and owner identity; stop protected work if ownership is lost. At completion, acquire the guard, re-read the record, and remove it only if both still match this run. This prevents delayed cleanup or competing recovery attempts from deleting a successor's lock.


Scope every lock by canonical repository identity and lane; unrelated repositories must not share a global lane lock. Use a host-equivalent advisory-lock primitive if `fcntl` is unavailable, preserving ownership and atomic publication semantics. If lifecycle ownership cannot be verified, report the limitation rather than weakening reclamation rules.

## Durable Memory

- Use the durable deduplication/state backend established by repository guidance or the active scheduler contract. Do not choose or create an external memory store or silently switch backends. If the selected lane requires persistent deduplication and none is configured, finish read-only preparation and report that blocker before duplicate-prone writes.
- GitHub Discussions is one supported adapter, not a universal requirement. When selected, resolve repository/category/title/marker from owning guidance. The lane's suggested discussion names/markers are defaults only after that adapter is explicitly chosen. Preserve existing compatibility and legacy aliases locally.
- Read the active state and relevant historical input before selecting work. For standalone runs use the configured lane state; for orchestrated runs central state is the sole active write surface and historical lane state is read-only input.
- Record work item key, head/base or source snapshot, active worker ID, branch/worktree, observed outcome/no-op, blockers, artifact links, cooldown, and next eligible run. Preserve enough information to suppress repeats on unchanged evidence.
- Dispatcher owns one ordered state-write queue. Workers return outcomes for their assigned item; do not rewrite unrelated state or central memory. Required external output artifacts remain separate from orchestration state.
- Stop duplicate-prone dispatch/writes when required state cannot be read or updated safely. Do not substitute local files, another account, or a new discussion unless that backend change is explicitly authorized.

## Delegation

- Dispatcher playbooks dispatch work rather than implementing lane-specific fixes/reviews inline. Use one bounded worker per PR, issue, incident group, drift, test gap, digest date, or debt item. Helpers stay inside their assigned item.
- Read the active host's actual worker cap; fail closed to one worker if no cap is available. Do not invent a model/reasoning pin. Shared agents inherit caller preferences.
- Verify worker tooling before dispatch. If a dispatcher requires separate workers and tooling is absent, report the blocker instead of silently substituting inline execution.
- Record each worker's ID, lane, assigned scope/key, source snapshot, branch/path, and state before launching duplicate-prone work. Pass a self-contained prompt with permitted outputs, validation, ownership, and authorization boundaries.
- Budgets/cadences in lane descriptions are defaults for a separately configured run; use repository/user overrides. Exhausting one lane budget blocks that lane, not unrelated eligible work.

## Git And Worktrees

- Carry forward the user/host contract's specific write authority. A manual playbook invocation is not blanket permission for every operation the lane can perform; isolation does not grant publication authority.
- Preserve unrelated checkout content. Unattended code workers start from the selected current default-branch ref; PR workers use their assigned PR head. The dispatcher checkout is not their implementation workspace.
- Never merge a PR, force-push, rebase, or mutate live systems under a maintenance playbook. A single inspected base-into-head merge is limited to explicitly authorized PR-conflict repair.
- Publish only scoped, validated changes to the verified target. When evidence, product intent, compatibility, or validation is unclear, return a concrete blocker or prepare a deduplicated issue under existing issue-write authority.

## Validation And Output

- Use the target repository's approved checks/environment; preserve real-stack, native validator, interpreter, and coverage requirements. Distinguish static checks, behavior, coverage, hosted CI, artifact identity, and live health.
- Follow repository PR metadata/body policy, existing labels, readiness gates, and issue templates. This library imposes no universal validation-section policy, readiness label, or product-label taxonomy.
- Preserve configured hidden markers, memory identity, output prefixes, and date keys as compatibility contracts. Update existing artifacts when evidence changes rather than creating duplicates. Project guidance may select the lane's suggested output schema.
- After publication take one check snapshot and hand off pending CI. Poll only when monitoring is requested or investigating an existing failure.
- Keep external output concise, source-backed, and redacted. Never expose credentials, private customer data, unnecessary raw logs, request/session identifiers, or full stack traces.

## Orchestrator Overlay

Use the optional [orchestrator](workflows/orchestrator.md) for route coverage, priorities, worker dispatch, budgets, and central state only when that dispatcher is requested/configured. Enable only lanes with the required project policy, integrations, and write authority. The [workflow index](workflow-index.md) is a catalog, not a scheduler.

Readiness labels are optional repository policy. If one is configured, [PR Guardian's readiness gate](workflows/pr-guardian.md#ready-for-human-label-gate) defines the evidence needed for its compatible GitHub adapter; preserve any existing local contract.
