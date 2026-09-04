# Teather agent instructions

These exist so a new session can resume without rebuilding context from chat
history. Keep them short.

## Resuming

`docs/PROJECT_STATUS.md` is the resume point — current state, what changed last,
open risks. Read it first. Everything else is reference, pulled in only when the
task needs it: `docs/DECISIONS.md` records *why* past technical choices were made
(so a rejected approach is not rediscovered), `docs/ARCHITECTURE.md` is how the
pieces fit, and the P1 handoff/recovery docs matter only when you are actually
running an acceptance or recovery procedure. If a doc contradicts the code, the
code wins for what *is*; fix the doc.

Just start. You do not need to stop and ask permission to begin work, classify
the task, or pick a reasoning mode. Ask the owner only for a **Safety gate**
below, or a genuinely irreversible fork the repo can't answer.

## Working autonomy

Work in whole arcs, not single steps. Design, implement, refactor, test,
package, update the docs the change touched, and commit to a branch on your own
judgement — then report what was done. Specifically:

- Record a technical choice that changed in `docs/DECISIONS.md` and move on. Do
  not wait for sign-off on it.
- Chain the work: finish the feature, run the tests, reconcile the docs, push
  the branch in one pass. Do not hand back after each file with a "next exact
  task" for a future session — that queue-of-instructions habit is retired.
- If something needs the owner, give a best-effort answer with your assumptions
  stated and keep going.
- Deferred scope (multi-client, other platforms, IPv6, WireGuard, P5 polish,
  release signing) is deprioritised, not fenced off. If a slice is clearly worth
  doing, say so and start it; the owner redirects if they disagree. The items
  that truly need the owner first are only those in **Safety gates** and
  **Hard constraints**.

The reason to stop is a real gate or a real fork — not a status check.

## Current priority

P0/E-001 and P1 acceptance are complete; P1 is the owner's daily connection.
D-022 has run live on the developer laptop since 2026-08-30. Current installed +
committed build: Debian `0.1.0-19` / Android `0.1.0-p1.6` (`versionCode 8`).
Deployed + live-tested through `0.1.0-11`: D-023 (upstream switch), D-024 (udpgw
UDP), D-025 (standalone connect), D-026 (abnormal-disconnect self-heal +
auto-reconnect + `teatherd.log` + toast notifications + single-instance GTK +
sole-path tracking; fault-injection tested 2026-08-31). **D-028/D-029/D-030
(`0.1.0-12` / Android `0.1.0-p1.3`, live-verified 2026-09-01):** D-028 — the
SOCKS relay requires RFC 1929 auth with a per-run secret the phone publishes
only in its `DUMP`-protected status (closes "any app on the phone can use the
loopback relay"; schema → 2). D-029 — the deb bundles the APK;
`teather device install` (or a GTK button) keeps the phone app in lockstep.
D-030 — release signing done; the release key lives at
`~/.teather/teather-release.jks` (`keystore.properties`, both gitignored). SDK
at `~/Android/Sdk`. **2026-09-03 (`0.1.0-13`..`0.1.0-17`, live-verified):** a
self-heal wedge fix (reconcile went dormant on a non-`recovery-pending` latched
error after a reboot with a stale DNS sentinel); a Light/Dark/Follow-system
Appearance setting on both halves; a state-driven GTK phone-app install button;
**D-031** — an advisory `teather.status.security` version (separate from the
pairing schema) with a GTK update prompt; and a GTK window that replaces a
stale instance on relaunch. **2026-09-03 (`0.1.0-18` / `0.1.0-p1.6`):** **D-032**
— a shared design language (`docs/DESIGN_LANGUAGE.md`): native clients, no
cross-platform toolkit; first pass gave the GTK window a HeaderBar, labelled
sections, and a status pill, and aligned the Android app's palette/headings/pill.
Cosmetic; schema unchanged. Deferred: the phone-reboot soak.

The owner **directed a focused post-P1 track** and rejected the roadmap's
assumption that all of P2 ("protocol completeness") and P4 (WireGuard) must
follow. Status:

1. Android status/text cleanup, Linux-matched icon, zero-gap upstream switch
   (`ACTION_RECONFIGURE`). **Done + live-tested** 2026-08-30.
2. **Lightweight UDP** (D-024): tun2proxy's `udpgw` feature +
   `--udpgw-server 240.0.0.1:1`; the phone's `UdpGatewayServer` terminates the
   framed stream over the existing SOCKS connection. No second ADB forward, no
   `VpnService`, no packet stack. **Done + live-tested** 2026-08-30 (STUN
   round-trip through `teather0`). The Debian build rebuilds tun2proxy with
   `--features udpgw` automatically.
3. **Primary-goal verification.** The re-origination that keeps cellular traffic
   from looking tethered is already built — the phone opens every socket itself,
   and the 2026-08-30 test confirmed the egress is genuinely the phone's cellular
   link. **Operational evidence (E-012):** on a prepaid Straight Talk plan where
   exceeding the tether allowance is a hard stop, sustained daily Teather use —
   including a ~4-hour heavy session — has drawn no tether hard-stop and no
   carrier notice. Recorded as observation, not proof (D-009). The controlled
   network-layer check (E-011: TTL / JA3 via a reflector + a cellular-bound
   request from the phone) is now **opportunistic** — run it when a reflector
   host is available; it is no longer blocking.
4. **Robustness** — D-026 (`0.1.0-11`) implements self-healing reconciliation,
   the wider `health_check()`, persistent logging, toast notifications, the
   single-instance GTK app, the standalone connectivity re-check, and sole-path
   tracking (punch items 4/5/6). Committed `071e2cc`; fault-injection tested
   2026-08-31 and passing. Remaining: the phone-reboot case and a real
   daily-use soak.

The 2026-08-30 live test also raised the relay concurrency ceiling 64 -> 256
(`0.1.0-7`) after a full-desktop failover exhausted the old limit, then tuned the
UDP gateway (`--udpgw-connections 16`, `--udp-timeout 30`, `0.1.0-8`). On
`0.1.0-8` **Shadow PC launched and was usable** through Teather (Wi-Fi off, whole
desktop on `teather0`); the owner confirmed it. Bitrate/latency were not
measured. P3 wireless stays deprioritised — it is the native-UDP path if a
future session needs better cloud-gaming quality, but Shadow works now.

**P3 wireless is deprioritised.** A local Wi-Fi receiver link does not advance
the not-classified-as-tethered goal — the carrier cannot see the receiver<->phone
link — and enabling any Android AP mode is one more device-side state change with
no benefit here. USB/ADB stays the transport while that goal dominates; revisit
P3 only as a cable-free convenience if the owner asks.

IPv6 and the broader "become a VPN" scope stay deferred. Do not add fingerprint
camouflage, DPI evasion, or carrier-stealth profiles (D-009) — deliberate
non-goal. Anything outside the current track (multi-client, other platforms, P5
polish) is lower priority, not off-limits — see **Working autonomy**. Release
signing is wired (D-030); the owner generates the key.

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
  connection (plus the non-mutating `CheckConnectivity` nudge, D-026).
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
is staged. Update `docs/PROJECT_STATUS.md` when you finish a work session or when
something ships — not after every edit — and touch `docs/DECISIONS.md` (a changed
technical choice), `docs/THREAT_MODEL.md` (new privileged behaviour), or
`docs/EXPERIMENTS.md` (a finished experiment) only if this change touched what
they cover. Name unresolved risks instead of quietly working around them.

`PROJECT_STATUS.md` records what *is* — current state and open risks. Do not
leave a "next exact task" in it unless you are genuinely stopping mid-arc with a
specific one to note. One status file is the thing that must stay current; the
rest is "touch it if this change touched it."

## Documentation style

Plain language; say why a constraint exists. Mark unverified designs
**proposed** or **hypothesis** and don't claim a feature works before a test
shows it. Use exact dates in status and experiment entries. Keep rejected
alternatives in `docs/DECISIONS.md` (append, don't rewrite) so they aren't
rediscovered.
