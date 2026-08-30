# Teather agent instructions

These exist so a new session can resume without rebuilding context from chat
history. Keep them short.

## Resuming

Read `docs/PROJECT_STATUS.md` — it is the resume point (current state, what
changed last, next action). For P1 work also read `docs/P1_HANDOFF.md` and
`docs/P1_RECOVERY.md`. `docs/DECISIONS.md` records *why* past technical choices
were made, so a rejected approach is not rediscovered. If a doc contradicts the
code, the code wins for what *is*; fix the doc.

You do not need to stop and ask permission to begin work, classify the task, or
pick a reasoning mode. Just start. Ask the owner only for the things listed under
**Safety gates**, or when a real decision genuinely can't be made from the repo.

## Current priority

P0 and E-001 are complete. Milestone: **P1 — Linux USB Desktop validation.**

D-022 is accepted, implemented (package `0.1.0-4`), and **validated end to end on
2026-08-30** in the disposable VM with the phone passed through over USB:
`teather connect` works, real traffic exits on the phone's cellular, additive
DNS keeps the physical resolver first while the VM's link is up, failover and
restore are automatic, and every teardown returns the host to exact baseline. 46
host unit tests + D-Bus smoke pass. NetworkManager owns `teather0` as an
in-memory `tun` connection (`tun.owner` so `tun2proxy` runs unprivileged, no
polkit prompt from the daemon's context); no setuid helper or polkit action.

Remaining for P1 sign-off: a two-hour session, the GUI/tray + package
upgrade/purge lifecycle against `0.1.0-4`, and the milestone closeout (roadmap,
`docs/PROJECT_STATUS.md`, README, E-002/E-003). Then **stop for the P2 design
discussion (D-018)** — do not start general UDP, IPv6, broader DNS, WireGuard,
wireless transports, multi-client, other platforms, or P5 polish.

## Safety gates — ask the owner first

- **The phone.** Do not connect, pass through USB, or run any ADB command
  against it without the owner saying to. Do not infer it is available from ADB
  state.
- **The active developer host.** Do not create `teather0`, change routes/DNS/
  firewall, or install the package on the machine this session runs on. Network
  changes get tested in a disposable VM first — the dev connection depends on
  this host staying up.
- Publishing anything outside the repo, or other hard-to-reverse outward actions.

## Hard constraints

- Baseline stays unrooted: no unlocked bootloader, Magisk, system app, hidden
  APIs, or device-integrity workarounds.
- No wildcard or passwordless sudo; no new setuid helper or polkit action; no
  NetworkManager scope beyond creating/activating/deleting the one `teather0`
  connection.
- Linux route/DNS/firewall changes must be bounded, reversible, and restored on
  normal exit, error, signal, and next-start recovery. Treat a cleanup mismatch
  as a failure even if traffic worked.
- Do not commit secrets, ADB keys, private keys, device serials, phone numbers,
  subscriber data, packet captures, or provider account details.
- Do not claim carrier accounting/classification is bypassed; record observed
  behaviour as an experiment. No stealth/DPI-evasion/fingerprint-camouflage
  features.
- Android owns control state; receiver implementations stay thin.

## Engineering rules

- Prefer a working vertical slice over a speculative abstraction, and the
  lightest mechanism that meets the requirement — the phone pays for CPU,
  battery, and heat. Justify a heavier design in `docs/EXPERIMENTS.md`.
- Keep transport, relay protocol, flow handling, routing, and UI as separate
  modules.
- Bind test services to loopback unless a test needs a local-link listener;
  never expose an unauthenticated relay to arbitrary interfaces.
- Timeouts, cancellation, and useful error categories at every I/O boundary.
- Logs identify the failing layer without recording browsing destinations by
  default.
- Pin or record dependency versions.

## Testing

- Unit-test framing, state transitions, config parsing, and cleanup logic.
- Test the Android relay and Linux connector independently before end-to-end.
- Capture receiver routes and DNS before and after integration tests.
- Don't use real credentials or production captures as fixtures.
- `docs/TEST_PLAN.md` has the milestone exit criteria.

## Finishing a change

Run the relevant tests and say the command and result. Check nothing sensitive
is staged. Update `docs/PROJECT_STATUS.md` (what changed, next action) and,
where affected, `docs/DECISIONS.md` (a changed technical choice),
`docs/THREAT_MODEL.md` (new privileged behaviour), and `docs/EXPERIMENTS.md` (a
finished experiment). Name unresolved risks instead of quietly working around
them. That's the whole checklist — one status file is the thing that must stay
current; the rest is "touch it if this change touched it."

## Documentation style

Plain language; say why a constraint exists. Mark unverified designs
**proposed** or **hypothesis** and don't claim a feature works before a test
shows it. Use exact dates in status and experiment entries. Keep rejected
alternatives in `docs/DECISIONS.md` (append, don't rewrite) so they aren't
rediscovered.
