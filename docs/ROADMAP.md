# Roadmap

The roadmap is organized around evidence gates. Dates are intentionally omitted;
the project advances when the previous milestone works and is documented.

## P0 — Relay Proof

**Status:** Passed on 2026-08-25. See E-001.

**Question:** Can one TCP connection enter an unrooted Android application through
ADB and exit through the selected upstream reliably?

Deliverables:

- Minimal Android project.
- Foreground relay service.
- Upstream discovery and explicit socket binding.
- SOCKS5 CONNECT support for IPv4 and domain targets.
- ADB forwarding instructions or helper.
- One reproducible Linux browser/curl test.
- Experiment E-001 results.

Exit criteria:

- At least ten consecutive requests succeed.
- A continuous transfer runs for at least thirty minutes.
- Stopping the Android service closes connections cleanly.
- Switching the intended upstream produces a clear success or failure result.
- Observed provider behavior is recorded without making a generalized claim.

Not included: TUN, UDP, graphical polish, Wi-Fi, or permanent packaging.

## P1 — Linux USB Desktop

**Status:** Host-only checks passed on 2026-08-25 and both disposable-VM phases
passed on 2026-08-26. Debug-APK verification passed on 2026-08-27. The first
physical run that day connected the bounded tunnel but failed safely when Wi-Fi
removal left no usable nameserver. D-021's `Reapply` DNS mechanism was disproven
on 2026-08-29 (externally-assumed connection). **D-022 is accepted, implemented
(package `0.1.0-4`), and validated end-to-end on 2026-08-30** in the disposable
VM with the owner's phone passed through over USB: `teather connect` works,
traffic exits on the phone's cellular, DNS and routing fail over automatically
when the VM's link drops and restore cleanly, and every teardown returns the
host to exact baseline. Package lifecycle and the GTK GUI pass against
`0.1.0-4`. The synthetic two-hour soak is deliberately skipped — the owner's
real daily use is the sustained/live-data validation. **P1 acceptance is met and
Teather is the owner's daily connection.** Release signing is wired (D-030,
supersedes D-019) — the key is the owner's to generate. Detail in
`docs/P1_HANDOFF.md`.

**Question:** Can an installable Debian desktop client provide understandable,
recoverable system-wide TCP and DNS through the existing Android relay?
**Answered — yes.** D-018's "stop for a P2 discussion" happened; the owner then
directed the focused post-P1 track below instead of the full P2/P4 sequence.

Entry gate (D-013, satisfied 2026-08-25): the owner reviewed and approved the
Linux networking design before P1 code was written. Live host mutation is limited
to the physical acceptance sequence, after isolated VM tests pass.

Accepted operating model (D-014 as amended by D-022):

- NetworkManager creates and owns a non-persistent, in-memory `teather0` `tun`
  connection over ADB.
- Every existing Wi-Fi/Ethernet connection and default route is untouched and
  stays preferred while present; Teather's DNS is additive (positive,
  non-exclusive priority) so the physical resolver stays first.
- Automatic failover is the default: once the physical link's route and resolver
  are gone, the kernel and glibc fall through to Teather. `teather failover off`
  keeps Teather dormant until armed, for metered upstreams.
- No persistent NetworkManager profile, no direct `/etc/resolv.conf` edit, no
  firewall change, no change to any physical link.

Deliverables (delivered as Android `0.1.0-p1` / `versionCode 2`, Debian
`0.1.0-4`, iterated to Android `0.1.0-p1.5` / `versionCode 7`, Debian `0.1.0-17`):

- Android with DUMP-protected `START` / `STOP` / `RECONFIGURE` actions and
  versioned machine-readable `dumpsys` status.
- Per-user `teatherd` with one typed D-Bus manager API, device trust, one-active-
  device selection, state/metric signals, redacted diagnostics, and a mode-0600
  ownership journal.
- Focused GTK 3 window, optional Ayatana tray, and CLI parity for status, devices,
  connect/disconnect, device approval/rename/forget, auto-connect, diagnose, and
  recover. Status-oriented commands support JSON.
- An in-memory NetworkManager `tun` connection for `teather0`,
  created and activated by the unprivileged daemon, with `192.0.2.1/32`, MTU
  1500, `198.18.0.0/15`, a metric-32000 backup default (armed only when failover
  is on), and `tun.owner` delegation to the desktop user (D-022). No privileged
  helper.
- Reproducibly pinned tun2proxy 0.8.3 with virtual DNS, IPv4-only behavior, 64
  sessions, 300-second TCP timeout, destination logging disabled, run as
  `--tun teather0`.
- Resolver integration: advertise reserved sentinel `198.19.0.1` through the
  NetworkManager connection at a positive, non-exclusive `ipv4.dns-priority`
  (additive — the physical resolver stays first), and verify virtual DNS over
  UDP and TCP before ready.
- Debian 12 amd64 package with desktop/icon, D-Bus activation, optional systemd
  user watcher, tunnel binary, recovery guide, and licenses.

Exit criteria:

- Browser, Git, SSH, and package metadata lookup succeed.
- With Wi-Fi enabled, its existing default and resolver stay preferred and
  fully working; when Wi-Fi is lost, traffic and DNS fail over to Teather
  automatically (failover armed) without restarting Teather; restoring Wi-Fi
  makes it preferred again.
- Every physical NetworkManager connection/profile is byte-for-byte unchanged
  across start, Wi-Fi loss/restore, stop, crash, and cable removal; the only new
  connection is the in-memory `teather0`, which disappears on teardown.
- Hostname-based workloads succeed after Wi-Fi is lost, and every tested failure
  restores the exact pre-test resolver state without writing `/etc/resolv.conf`
  directly.
- Two-hour session completes without unbounded resource growth.
- SIGINT, SIGTERM, Android service stop, and cable removal restore prior routes and
  DNS.
- Re-running stop is safe.
- Startup detects and repairs an intentionally simulated stale state.
- Release ADB shell can start/query/stop Android; an ordinary application cannot.
- Attaching to a compatible manual relay does not restart it, and disconnect
  stops only a Linux-started relay.
- GUI remains functional without tray integration; package install, upgrade,
  uninstall, and purge semantics pass.
- No raw ADB serial or browsing destination appears in files, D-Bus, or logs.

Exit (met): the P1 physical experiment is recorded, `docs/PROJECT_STATUS.md` is
current, and the D-018 stop-for-discussion happened — see below.

## Post-P1 direction (2026-08-30, updated 2026-09-01)

After P1 acceptance the owner redirected work away from completing P2/P3/P4 as
written. The linear phase plan below is kept for reference; the active order is
in `AGENTS.md`. Done so far:

- **D-024** — lightweight general UDP over tun2proxy's `udpgw` stream, phone-side
  `UdpGatewayServer`. Live-tested; Shadow PC cloud gaming works (`0.1.0-8`).
- **D-025** — Teather can be the *only* internet path when armed and no other
  link exists. Live-tested (`0.1.0-9`).
- **D-026** — abnormal-disconnect self-heal + auto-reconnect, persistent
  `teatherd.log`, toast notifications, single-instance GTK, sole-path tracking.
  Fault-injection tested (`0.1.0-11`).
- **D-028/D-029/D-030** — SOCKS relay authentication (per-run secret, schema 2),
  the `.deb` bundling and installing the matching APK, and release signing.
  Live-verified (`0.1.0-12` / `0.1.0-p1.3`, 2026-09-01).
- **D-031** — an advisory security-version layer (separate from the pairing
  schema) with a GTK update prompt; plus a Light/Dark Appearance setting on
  both halves, a state-driven phone-app install button, and a GTK window that
  replaces a stale instance on relaunch. Live-verified (`0.1.0-17` /
  `0.1.0-p1.5`, 2026-09-03).
- **E-012** — operational carrier evidence recorded (no tether hard-stop on a
  hard-stop prepaid plan under heavy daily use).

Remaining in this track:

- **E-011** — the controlled TTL / JA3 network-layer comparison, now
  opportunistic (needs a reflector reachable from the phone's cellular).
- A phone-reboot fault case and a longer daily-use soak.

**P3 (Wireless Relay) is deprioritised** — a local receiver link is invisible to
the carrier and does not serve the primary goal. IPv6, WireGuard, and the
broader "protocol completeness" scope are deferred, not scheduled.

## P2 — Protocol Completeness

**Question:** Is the relay compatible enough for daily Linux use?

Deliverables:

- UDP ASSOCIATE or another documented UDP relay path. *(A udpgw path is
  implemented — D-024 — ahead of this phase.)*
- Explicit IPv6 policy and tests.
- DNS A/AAAA behavior tests.
- Keepalive, timeout, cancellation, and backpressure behavior.
- Suspend/resume and phone-screen-off tests.
- Structured metrics and redacted diagnostics bundle.

Exit criteria:

- TCP and representative UDP workloads pass the test plan.
- Overnight idle and multi-hour active tests complete.
- No route or DNS residue remains after every tested failure mode.
- Battery and thermal observations are recorded.

## P3 — Wireless Relay

**Question:** Can the same relay operate wirelessly without using Android's stock
Internet hotspot path?

Deliverables:

- Local-only hotspot lifecycle.
- Permission and user-consent flow.
- Authenticated Teather session over the local link.
- Discovery or QR-based endpoint configuration.
- Linux companion transport selection.
- Shared-link threat-model review.

Exit criteria:

- Linux can move between USB and Wi-Fi without changing relay semantics.
- An unauthorized local peer cannot use the relay.
- Reconnection after Wi-Fi interruption is predictable.
- Performance and battery results are compared with USB.

## P4 — WireGuard Compatibility

**Question:** Can Teather provide a standard full-IP receiver interface while
remaining unrooted?

Deliverables:

- Small userspace WireGuard endpoint prototype.
- Userspace TCP/UDP flow termination into Android sockets.
- Generated Linux and mobile client configurations.
- QR pairing prototype.
- Comparative benchmark against SOCKS/tun2socks.
- Decision record accepting or rejecting the architecture.

Exit criteria:

- Linux and one mobile receiver carry TCP, UDP, and DNS.
- Flow cleanup and memory bounds are acceptable.
- Throughput, latency, battery, and thermal behavior are measured.
- Failure behavior is at least as understandable as the private relay.

If rejected, proceed with thin Teather receivers rather than repeatedly rebuilding
the same WireGuard experiment.

## P5 — Daily-Driver Experience

**Question:** Can the owner use Teather without consulting development notes?

Deliverables:

- Android connection dashboard.
- Receiver identity management and revocation.
- Transport selection and fallback.
- Session data, latency, and health indicators.
- Actionable error messages.
- Emergency receiver-network restoration control.
- Minimal Linux desktop integration if still useful.
- Rich desktop history, visual polish, onboarding, and broader remembered-device
  management beyond P1's focused operational interface.

Exit criteria:

- Cold-start connection succeeds through a documented short flow.
- Every visible state corresponds to measured daemon state.
- Diagnostic export excludes secrets and browsing history by default.
- The owner can recover from common failures without a shell.

## P6 — Transport Expansion

Add one transport at a time, in this order unless evidence changes it:

1. ADB USB hardening and automation.
2. Existing LAN discovery.
3. Android Open Accessory USB.
4. Bluetooth Classic/RFCOMM.
5. Wi-Fi Direct if local-only hotspot is insufficient.

Each transport requires authentication, recovery tests, performance results, and
an updated threat-model entry before it is considered supported.

## P7 — Platform Expansion

Suggested order:

1. Windows
2. macOS
3. Android receiver
4. iOS receiver

If WireGuard compatibility succeeds, these milestones focus on onboarding and
profiles rather than custom packet-capture clients. If it fails, each platform
requires a feasibility decision before implementation.

## Before making the repository public

- Select and add an explicit license (D-010, still open).
- Remove private device/provider details and captures from history, not merely the
  current tree.
- Add reproducible build instructions.
- Pin dependencies and run vulnerability/license checks.
- Establish a vulnerability-reporting channel (`SECURITY.md`).
- Generate the release signing key and cut a first tagged release with the APK +
  deb attached, so the app's "Get the desktop client" link and `teather device
  install` have something to point at (D-029, D-030 — wiring done).
- State supported and unsupported devices honestly.
- Document provider/accounting uncertainty without advertising guaranteed evasion.
- Relay authentication is done (D-028); the loopback SOCKS listener is no longer
  an open proxy for other apps on the phone.
- Decide whether binaries or only source will be published.

## Parking lot

These ideas are deliberately deferred:

- Multi-client access
- Bandwidth limits and per-receiver policy
- Connection bonding or multipath
- Reverse tethering
- Remote relay or mesh networking
- Television/console support
- Traffic capture UI
- Carrier-specific profiles
- Root-enhanced mode

Move an item out of the parking lot only by adding a decision entry and placing it
behind the current milestone.
