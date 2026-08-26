# Roadmap

The roadmap is organized around evidence gates. Dates are intentionally omitted;
the project advances when the previous milestone works and is documented.

## P0 — Prove Android application relay

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

## P1 — Viable system-wide Linux TCP

**Question:** Can normal Linux TCP applications use Teather without per-application
proxy configuration?

Mandatory entry gate:

- Stop after P0 cleanup and evidence recording. A successful P0 run does not
  authorize P1 implementation.
- Before writing P1 code or running a command that can affect Linux networking,
  review the exact TUN, route, policy-rule, DNS, firewall, recursion-prevention,
  saved-state, and rollback design with the owner.
- Supply an offline recovery procedure for normal stop, errors, signals, Android
  service loss, and cable removal, then obtain the owner's explicit approval.

This gate is accepted in D-013 and must carry across sessions.

Accepted operating model (D-014):

- Create a non-persistent `teather0` virtual backup interface over ADB.
- Keep every existing Wi-Fi/Ethernet connection and default route untouched and
  preferred while it is present.
- Let the owner manually disable Wi-Fi to make Teather the remaining default and
  manually restore Wi-Fi to recover or switch back.
- Do not perform NetworkManager writes, create persistent connection profiles,
  overwrite `/etc/resolv.conf`, or flush firewall state.

Deliverables:

- Non-persistent `teather0` creation and teardown.
- Pinned `tun2socks` integration.
- A lower-preference Teather default route that never deletes or replaces an
  existing physical default and avoids tunnel recursion.
- Teather-owned scoped DNS through the relay, with no mutation of existing-link
  DNS configuration.
- A documented resolution of the P1 DNS gap: Wi-Fi removal must not leave the
  host with no resolver or an unreachable LAN-only resolver, and P0's
  proxy-specific `socks5h` behavior must not be mistaken for system-wide DNS.
- Preflight diagnostics and postflight cleanup verification.
- CLI commands for start, status, diagnose, and stop.

Exit criteria:

- Browser, Git, SSH, and package metadata lookup succeed.
- With Wi-Fi enabled, its existing default remains preferred; after the owner
  disables Wi-Fi, Teather becomes the selected Internet path; restoring Wi-Fi
  makes it preferred again without restarting Teather.
- NetworkManager connection/profile state is byte-for-byte or semantically
  unchanged across start, manual Wi-Fi toggles, stop, crash, and cable removal.
- Hostname-based workloads succeed after Wi-Fi is disabled, and every tested
  failure restores the exact pre-test resolver state without writing
  `/etc/resolv.conf` directly.
- Two-hour session completes without unbounded resource growth.
- SIGINT, SIGTERM, Android service stop, and cable removal restore prior routes and
  DNS.
- Re-running stop is safe.
- Startup detects and repairs an intentionally simulated stale state.

## P2 — Protocol completeness and resilience

**Question:** Is the relay compatible enough for daily Linux use?

Deliverables:

- UDP ASSOCIATE or another documented UDP relay path.
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

## P3 — Local-only Wi-Fi transport

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

## P4 — WireGuard compatibility experiment

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

## P5 — Daily-driver interface

**Question:** Can the owner use Teather without consulting development notes?

Deliverables:

- Android connection dashboard.
- Receiver identity management and revocation.
- Transport selection and fallback.
- Session data, latency, and health indicators.
- Actionable error messages.
- Emergency receiver-network restoration control.
- Minimal Linux desktop integration if still useful.

Exit criteria:

- Cold-start connection succeeds through a documented short flow.
- Every visible state corresponds to measured daemon state.
- Diagnostic export excludes secrets and browsing history by default.
- The owner can recover from common failures without a shell.

## P6 — Additional transports

Add one transport at a time, in this order unless evidence changes it:

1. ADB USB hardening and automation.
2. Existing LAN discovery.
3. Android Open Accessory USB.
4. Bluetooth Classic/RFCOMM.
5. Wi-Fi Direct if local-only hotspot is insufficient.

Each transport requires authentication, recovery tests, performance results, and
an updated threat-model entry before it is considered supported.

## P7 — Additional receiver platforms

Suggested order:

1. Windows
2. macOS
3. Android receiver
4. iOS receiver

If WireGuard compatibility succeeds, these milestones focus on onboarding and
profiles rather than custom packet-capture clients. If it fails, each platform
requires a feasibility decision before implementation.

## Before making the repository public

- Select and add an explicit license.
- Remove private device/provider details and captures from history, not merely the
  current tree.
- Add reproducible build instructions.
- Pin dependencies and run vulnerability/license checks.
- Establish a vulnerability-reporting channel.
- State supported and unsupported devices honestly.
- Document provider/accounting uncertainty without advertising guaranteed evasion.
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
