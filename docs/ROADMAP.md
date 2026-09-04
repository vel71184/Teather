# Roadmap

Teather is **feature-complete for the owner's use**: P0 and P1 passed their
gates, and the owner-directed post-P1 track (D-024…D-033) is done. What remains
is the pre-public checklist and a set of optional future directions. None of the
latter is scheduled; each would advance only when it is worth doing and can be
backed by evidence. `docs/PROJECT_STATUS.md` is the live state; this file is the
forward view.

## Done

### P0 — Relay Proof

**Passed 2026-08-25 (E-001).** One TCP connection enters an unrooted Android app
through ADB and exits through the explicitly selected upstream: ten-request and
30-minute-transfer gates met, clean service-stop teardown, provider behaviour
recorded without a generalized claim.

### P1 — Linux USB Desktop

**Complete and the owner's daily connection.** An installable Debian client
provides understandable, recoverable system-wide TCP and DNS through the Android
relay. Delivered as Android `0.1.0-p1` → `0.1.0-p1.6` and Debian `0.1.0-4` →
`0.1.0-20`. Acceptance detail and the VM/physical procedure are in
`docs/P1_HANDOFF.md`; the test matrix is in `docs/TEST_PLAN.md`.

Accepted operating model (D-014 as amended by D-022) — still authoritative:

- NetworkManager creates and owns a non-persistent, in-memory `teather0` `tun`
  connection over ADB, with `tun.owner` delegation to the desktop user. No
  privileged helper, no polkit action.
- Every existing Wi-Fi/Ethernet connection and default route is untouched and
  stays preferred while present; Teather's DNS is additive (positive,
  non-exclusive `ipv4.dns-priority`) so the physical resolver stays first.
- Automatic failover is the default: once the physical link's route and resolver
  are gone, the kernel and glibc fall through to Teather. `teather failover off`
  keeps Teather dormant until armed, for metered upstreams.
- No persistent NetworkManager profile, no direct `/etc/resolv.conf` edit, no
  firewall change, no change to any physical link.

### Post-P1 track (owner-directed, 2026-08-30 onward)

The owner redirected away from the linear P2/P3/P4 plan (discharging D-018) to a
focused track, now complete:

- **D-023 / D-024 / D-025** — zero-gap upstream switch; general UDP over
  tun2proxy's `udpgw` stream terminated by a phone-side `UdpGatewayServer` (no
  VpnService, no second forward — Shadow PC cloud gaming works); Teather as the
  sole internet path when armed with no other link.
- **D-026** — abnormal-disconnect self-heal + auto-reconnect, persistent
  `teatherd.log`, toast notifications, single-instance GTK.
- **D-028 / D-029 / D-030** — per-run SOCKS secret (status schema 2); the `.deb`
  bundles and installs the matching APK; release signing.
- **D-031** — advisory security-version layer with a GTK update prompt.
- **D-032** — shared design language (`docs/DESIGN_LANGUAGE.md`): native clients,
  no cross-platform toolkit.
- **D-033** — daemon-side connection-session history (`teather sessions`, a GTK
  menu table), plus human-readable GTK byte units.
- **E-012** — operational carrier evidence recorded (no tether hard-stop on a
  hard-stop prepaid plan under heavy daily use).

Still open in this track: **E-011** (the controlled TTL/JA3 comparison, now
opportunistic — needs a reflector reachable from the phone's cellular), a
phone-reboot fault case, and a longer daily-use soak.

## Before making the repository public

- ~~Select and add an explicit license~~ — **done: GPL-3.0-or-later (D-010).**
- ~~Remove private device/provider details from history, not merely the current
  tree~~ — **done: the pilot phone's egress IPs were replaced with RFC 5737
  documentation addresses across the working tree and all git history.** No
  serials, keys, credentials, or subscriber data were ever committed.
- ~~Pin dependencies; run vulnerability and license checks~~ — **done:**
  `cargo audit` on the vendored `tun2proxy` lockfile reports 0 vulnerabilities
  (3 low-severity "unmaintained/yanked" advisories on transitive crates, none
  reachable); the Android app has no runtime dependencies and the Python client
  has no pip dependencies. Reproducible-build notes are in
  `third_party/tun2proxy/README.md` and `docs/DEVELOPMENT.md`.
- Establish a vulnerability-reporting channel (`SECURITY.md`) — enable GitHub
  private vulnerability reporting once the repo exists.
- Cut a first tagged release with the APK + `.deb` attached, so the app's "Get
  the desktop client" link and `teather device install` have a target (D-029,
  D-030 wiring is done). **Publishing model: source + the current `.deb` and
  `.apk` as release assets.**
- State supported and unsupported devices honestly; document provider/accounting
  uncertainty without advertising guaranteed evasion (D-009).

## Possible future directions (not a committed sequence)

Optional. Order is not fixed; each needs its own evidence and, where it changes
architecture, a decision record. Every new client's UI is written natively for
its platform and follows `docs/DESIGN_LANGUAGE.md` (D-032) — no cross-platform
UI toolkit.

- **Protocol completeness.** Explicit IPv6 policy and tests; A/AAAA DNS
  behaviour; keepalive / timeout / backpressure hardening; suspend-resume and
  screen-off tests; a structured redacted diagnostics bundle. (A udpgw UDP path
  already exists — D-024.)
- **Wireless receiver link.** The same relay over a local Wi-Fi link instead of
  USB, without Android's stock hotspot path. **Deprioritised** — the carrier
  cannot see the receiver↔phone link, so it does not serve the primary goal, and
  any Android AP mode adds a device-side signal for no benefit. Revisit only as
  a cable-free convenience if the owner asks.
- **WireGuard compatibility.** A small userspace WireGuard endpoint in the
  Android app so standard clients on any platform can attach, removing the need
  for a custom receiver per platform. A major evolutionary step, not the
  destination (see README "Next major evolution"). Needs a prototype,
  benchmarks against SOCKS/tun2socks, and a decision record accepting or
  rejecting it. If rejected, ship thin Teather receivers instead.
- **Other platform clients.** Windows, macOS, and iOS receivers. A second
  desktop platform would get a thin native shell over the existing daemon; the
  shared design spec makes that mostly a layout exercise. Whether a single Qt
  client for all desktops is worth it is a decision for when a second desktop
  platform is actually real.
- **Daily-driver polish.** Richer desktop history and onboarding, an Android
  connection dashboard, receiver identity management and revocation — beyond
  P1's focused operational interface.
- **Additional transports.** ADB automation hardening, existing-LAN discovery,
  Android Open Accessory USB, Bluetooth RFCOMM — one at a time, each with its
  own authentication, recovery tests, and threat-model entry.
- **Owner's fork ideas.** Separate experiments the owner has floated; each would
  branch from the current baseline rather than reshape it.

## Parking lot

Deliberately deferred; move an item out only by adding a decision entry:

- Multi-client access
- Bandwidth limits and per-receiver policy
- Connection bonding or multipath
- Reverse tethering
- Remote relay or mesh networking
- Television/console support
- Traffic capture UI
- Carrier-specific profiles
- Root-enhanced mode
