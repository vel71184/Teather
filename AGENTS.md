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

If those files disagree, stop and reconcile them. `docs/PROJECT_STATUS.md` is the
resume point, while accepted entries in `docs/DECISIONS.md` are authoritative for
technical choices.

## Current priority

The current milestone is P0. The source path is implemented; the next job is to
run `make check` and the exact device sequence in `docs/P0_HANDOFF.md`, then record
E-001 evidence. Do not rebuild the scaffold or ask the user for values the helper
can discover.

Do not start the full GUI, WireGuard endpoint, Wi-Fi Direct, AOA, Bluetooth,
multi-client support, packaging, or cross-platform receivers until the relevant
roadmap entry becomes active.

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
