# Teather agent instructions

These instructions apply to the entire repository. They exist so a future coding
session can resume without rebuilding the project context from chat history.

## Read before changing anything

Read, in order:

1. `README.md`
2. `docs/PROJECT_STATUS.md`
3. `docs/DECISIONS.md`
4. `docs/ARCHITECTURE.md`
5. The milestone-specific section of `docs/ROADMAP.md`
6. For P0 device work, `docs/P0_HANDOFF.md`
7. For current P1 validation, `docs/P1_HANDOFF.md` and
   `docs/P1_RECOVERY.md`

If those files disagree, stop and reconcile them. `docs/PROJECT_STATUS.md` is the
resume point, while accepted entries in `docs/DECISIONS.md` are authoritative for
technical choices.

## Fresh Codex session gate

On the first prompt of every new Codex conversation about Teather, including a
prompt that says only "continue" or "resume," perform the read order above and
then stop after advising the owner which reasoning level should be used. Treat a
context reset or imported conversation as a new conversation when it is not clear
that this gate already ran.

On that first prompt:

1. Use read-only inspection only. Do not edit files, run tests or builds, operate
   a phone or VM, change networking, or begin implementation.
2. Classify the requested work and recommend **GPT-5.6 Sol with Ultra** or
   **GPT-5.6 Sol with High**.
3. State the recommendation, the task boundaries that caused it, and whether the
   scope must be narrowed or divided.
4. Stop and wait for the owner to select or confirm that level and prompt again.
   Do not claim to know the active selector setting unless the environment
   actually exposes it.

Recommend **Ultra** for whole-repository processing, the first broad pass in a
new milestone, live-network/DNS design review, architecture or threat-model work,
security/privilege/recovery audits, milestone transitions, and changes spanning
several independently reviewable subsystems. Ultra is appropriate when useful
work can be delegated across Android, Linux networking, packaging, security,
testing, or documentation.

Recommend **High** for a focused task with an accepted design and a narrow
completion test: one component implementation, one bug, one test group, one
packaging fix, or a bounded documentation update. If a High task expands into
several independent workstreams or crosses an approval boundary, stop again and
recommend Ultra or ask the owner to narrow the task.

## Same-thread reasoning transition gate

Within an existing conversation, reassess the appropriate level when work reaches
a materially different phase, not at every file, command, or ordinary subtask.
Examples include design moving to implementation, a focused fix expanding into a
repository-wide audit, a broad review narrowing to one approved change,
implementation reaching live device or network validation, or a milestone
transition beginning.

If the best level changes in either direction, **High to Ultra or Ultra to High**:

1. Finish only the current safe unit of work; do not enter the new phase.
2. Tell the owner what phase finished, what phase is next, which level the next
   phase needs, and why.
3. Stop and wait for the owner to select or confirm the new level and prompt
   again.

If the next phase still fits the active recommendation, continue normally. Do not
interrupt merely because a different file or component is next. A level change
does not grant implementation, device, privilege, or live-test approval.

For the current P1 work, D-021 is accepted and implemented. Its disposable-VM
NetworkManager/DNS, privilege, recovery, packaging, and documentation matrix
remains Ultra because those workstreams are independently reviewable. Reassess
again before physical phone validation; a reasoning-level choice never satisfies
the separate operator phone gate.

These labels follow the current Codex distinction: High increases reasoning depth
for complex work; Ultra adds automatic task delegation for separable complex
work. Re-check the official Codex model guidance if those product definitions
change. This gate chooses an execution mode only. It does not grant approval,
weaken any safety constraint, or supersede a stop condition elsewhere in this
repository.

## Current priority

P0 and experiment E-001 are complete. The current milestone is P1 — Linux USB
Desktop validation. The Android control changes, focused Linux GUI/CLI/daemon,
privileged helper, recovery guide, Debian package, and pinned tunnel build are
implemented. Host checks and both disposable Debian 12 GNOME VM phases passed;
the VM is powered off. Do not rebuild the scaffold, rerun P0, or repeat the VM
matrix unless a regression requires isolated reproduction.

The owner accepted the local debug certificate for private P1 testing and deferred
a permanent release identity until distribution is being considered (D-019).
VersionCode 2 / `0.1.0-p1` and its debug signature are verified. The first
physical Phase 3 attempt on 2026-08-27 found and fixed the user-service
`NoNewPrivileges`/`pkexec` packaging conflict in Debian package `0.1.0-2`, then
failed safely at the required DNS gate: disabling Wi-Fi removed the only usable
non-loopback IPv4 nameserver. Cleanup restored routes, rules, resolver,
NetworkManager inventory, and firewall structure to baseline.

The owner approved D-021's bounded DNS design. Package `0.1.0-3` source work is
implemented: temporary per-device NetworkManager DNS, reserved sentinel
`198.19.0.1`, a non-overlapping `198.18.0.0/16` mapping pool, and virtual DNS over
UDP and TCP. Local tests, the aggregate build, two clean tunnel builds, and two
same-source package builds pass reproducibly. The next job is disposable-VM DNS
integration and cleanup validation; do not mutate the active host or query ADB.
Request explicit phone connection only after the VM gate passes. P1 remains active;
do not start P2 general UDP, IPv6, broader DNS, WireGuard, wireless transports,
multi-client support, cross-platform receivers, or P5 polish early.

## Hard constraints

- The baseline must remain unrooted.
- Do not require an unlocked bootloader, Magisk, a system application, hidden API
  access, or device-integrity workarounds.
- Do not make or document a promise that carrier accounting or classification is
  bypassed. Record observed behavior as an experiment.
- Do not add traffic-obfuscation, DPI-evasion, carrier fingerprint camouflage, or
  carrier-specific stealth presets.
- Do not commit secrets, ADB keys, WireGuard private keys, device serial numbers,
  phone numbers, subscriber data, packet captures, or provider account details.
- Linux route, DNS, and firewall changes must be bounded, reversible, and restored
  on normal exit, error, signal, and next-start recovery.
- Do not install wildcard or passwordless sudo rules.
- Android owns control state. Receiver implementations remain thin.

## Engineering rules

- Prefer a working vertical experiment over a large speculative abstraction.
- Keep transport, relay protocol, flow handling, routing, and UI as separate
  modules even in the prototype.
- Bind test services to loopback unless a test explicitly requires a local-link
  listener. Never expose an unauthenticated relay to arbitrary interfaces.
- Add timeouts, cancellation, and useful error categories at every I/O boundary.
- Logs should identify the failing layer without logging browsing destinations by
  default.
- Pin or record dependency versions once build files exist.
- New privileged behavior requires an update to `docs/THREAT_MODEL.md`.
- A changed architectural choice requires an update to `docs/DECISIONS.md`.
- A completed experiment requires an entry in `docs/EXPERIMENTS.md`.
- End each meaningful work session by updating `docs/PROJECT_STATUS.md`.

## Testing expectations

- Unit-test framing, state transitions, configuration parsing, and cleanup logic.
- Integration-test Android relay and Linux connector independently before the
  end-to-end test.
- Capture the receiver's routes and DNS state before and after integration tests.
- Treat cleanup failure as a test failure, even if Internet access worked.
- Do not use real credentials or identifying production captures as fixtures.
- Follow `docs/TEST_PLAN.md` for milestone exit criteria.

## Documentation style

- Use plain language and explain why a constraint exists.
- Mark unverified designs as **proposed** or **hypothesis**.
- Use exact dates for status snapshots and experiments.
- Preserve rejected alternatives in the decision log so they are not repeatedly
  rediscovered.
- Avoid claiming a feature exists until a runnable test demonstrates it.

## Change completion checklist

Before declaring work complete:

- Run the relevant tests and record the exact command and outcome.
- Verify no sensitive files are staged.
- Verify failure paths restore network state.
- Update documentation affected by the change.
- Update `docs/PROJECT_STATUS.md` with what changed and the next concrete action.
- Summarize unresolved risks rather than silently choosing around them.

## Milestone transition protocol

Completing any P# milestone requires a repository-wide resume-point transition,
not only an experiment entry. Before declaring a milestone complete or beginning
the next one:

1. Confirm every exit criterion in `docs/ROADMAP.md` and `docs/TEST_PLAN.md` has
   recorded evidence. A partial pass does not advance the active milestone.
2. Record the completed experiment(s) in `docs/EXPERIMENTS.md` with the exact date,
   commands, observations, failures, cleanup result, and inference limits.
3. Update `docs/ROADMAP.md` with the completed status/date and activate only the
   next approved milestone.
4. Update the header, objective, evidence, risks, and next exact action in
   `docs/PROJECT_STATUS.md`, then add a session closeout entry.
5. Update this file's read order and Current priority so a fresh thread cannot
   resume the completed milestone. Update README status and documentation links.
6. Create or refresh the next milestone's handoff and offline recovery document
   before it becomes the resume point. The handoff must separate completed
   evidence from pending gates and state whether a phone, VM, privilege, network
   mutation, or owner action is required.
7. Reconcile affected architecture, decisions, threat model, development, and test
   guidance. Preserve historical decisions and experiments, but label superseded
   instructions or add dated resolution notes.
8. Search the full documentation set for stale milestone names, blockers, service
   boundaries, and next-action language; run local-link validation and
   `git diff --check`.
9. Respect explicit approval stops. If the next milestone requires owner approval,
   leave it as the next discussion—not as authorized implementation work.

If these resume points disagree, the milestone is not complete even when its code
or device test passed.
