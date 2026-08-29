# Experiment log

Teather depends on behavior that varies across Android versions, phone vendors,
Linux networking stacks, and mobile providers. This log separates measurements
from assumptions.

Do not commit phone numbers, subscriber/account identifiers, device serials, ADB
keys, private keys, precise location, credentials, browsing history, or raw packet
captures containing personal traffic.

## Experiment rules

1. State one question.
2. Record the non-sensitive environment precisely enough to reproduce it.
3. Define success and failure before running the test.
4. Change one meaningful variable at a time.
5. Record exact commands when safe.
6. Preserve failures and surprising results.
7. Distinguish observation from inference.
8. Never generalize one provider/device result into a universal claim.

## Experiment template

```markdown
## E-NNN — Title

**Date:** YYYY-MM-DD
**Status:** planned | running | passed | failed | inconclusive
**Question:**

### Environment

- Phone model:
- Android version/build family:
- Teather commit:
- Linux distribution/version:
- Network manager:
- ADB version:
- Upstream type:
- Provider context (non-sensitive):

### Preconditions

-

### Procedure

1.

### Predetermined success criteria

-

### Results

-

### Observation vs. inference

- Observed:
- Inferred:

### Artifacts

- Redacted log:
- Metrics summary:

### Follow-up

-
```

## E-001 — TCP relay through Android over ADB

**Date:** 2026-08-24--2026-08-25 · **Status:** passed
**Question:** Can a Linux TCP client reach the Internet through an unrooted Android
application relay reached over USB/ADB, using an explicitly selected Android
upstream?

### Environment

- Phone model: Samsung SM-S266V, stock and unrooted
- Android version/build family: Android 16, API 36
- Teather commit: `eae4169`, plus the uncommitted helper hardening described
  below
- Linux distribution/version: Debian GNU/Linux 12, Linux 6.1.0-52-amd64
- Desktop/network manager: GNOME/Wayland, NetworkManager 1.42.4
- ADB/Java: Android Debug Bridge 1.0.41; OpenJDK 17.0.20
- Upstream type: explicit cellular; tested both with Wi-Fi disabled and with
  validated Wi-Fi as Android's default network
- Provider context: ordinary consumer cellular service; identifying account and
  subscriber details deliberately omitted

### Preconditions

- Phone is stock and unrooted.
- USB debugging is enabled and the Linux host is explicitly authorized.
- Android stock hotspot and USB tethering are off.
- Linux has another known-good path available for setup, or required dependencies
  are already installed.
- Baseline stock-tethering behavior and visible provider accounting are noted if
  it is safe and permitted to test them.

### Procedure

1. Run `make check`.
2. Run `./desktop/linux/teather-p0 doctor` and retain only its redacted output.
3. Confirm stock hotspot and stock USB tethering are off.
4. Run `./desktop/linux/teather-p0 all`.
5. Confirm the helper completes ten proxied HTTPS requests.
6. Run `./desktop/linux/teather-p0 soak` for the 1,800-second gate.
7. Compare helper output with the counters shown in the Android app.
8. Run `./desktop/linux/teather-p0 stop` and then `status`.
9. Disconnect USB and verify no Linux global network state was changed.

### Predetermined success criteria

- Ten consecutive requests succeed.
- Continuous transfer completes without relay crash or unbounded memory growth.
- Traffic counters are directionally consistent on both sides.
- Stopping the service closes the session cleanly.
- No stock tethering mode is activated.
- Logs identify the chosen Android upstream and failure layer without containing
  payloads or private destination history.

### Results

The physical relay and closeout gates passed. The Android UI selected-upstream
and counter evidence, active-session service stop, and USB-removal cleanup were
completed on 2026-08-25.

- `make check` passed before installation: JVM tests, Android lint, and debug APK
  assembly completed successfully (49 tasks).
- The first physical `all` run exposed a startup race: the helper tested
  immediately after requesting the foreground service and its first curl failed,
  while a manual request seconds later passed. The helper now waits up to 30
  seconds for a successful readiness request and removes the forward/service on
  readiness or smoke failure. Fresh runs then passed readiness and ten
  consecutive HTTPS requests.
- Two early paced-transfer runs appeared to fail after 119--136 seconds. The same
  curl low-speed failure reproduced without Teather against the public endpoint
  and twice against a loopback-only HTTP stream. The cause was the helper combining
  `--speed-limit`/`--speed-time` with intentional `--limit-rate` pacing, not an
  observed Android, Samsung, carrier, ADB, or Teather failure. The helper now uses
  a 25 MB Cloudflare speed-test response, checks elapsed time, byte floor, and
  connection count, and does not enable the conflicting low-speed watchdog.
- The corrected 180-second diagnostic passed with 1,547,506 bytes at 8,597 B/s,
  one connection, zero redirects, and the expected curl time-limit exit.
- The full gate passed with 15,334,016 bytes over 1,800.0 seconds at 8,518 B/s,
  one connection, zero redirects, and the expected curl time-limit exit.
- The display was awake for the first five minutes and locked/dozing afterward.
  Just before minute 19, a normal third-party notification illuminated the locked
  display. The developer stay-awake-while-USB setting kept it awake, so the display
  was manually returned to sleep about a minute later. The same SOCKS connection
  survived the wake/sleep disturbance.
- Teather memory did not grow monotonically: total PSS was 31,171 KiB at the full
  run's start, 18,089 KiB at midpoint (with 15,591 KiB swapped), and 26,275 KiB at
  completion. This is no evidence of unbounded growth in a 30-minute run.
- A focused system-wide logcat review found no Teather process kill, crash, ANR,
  thermal-critical event, data stall, or validation failure. One coarse Teather
  timeout was logged for another/stale session while the measured connection
  continued to completion. One system kill event did not involve Teather. Raw
  system logs and device/network identifiers were not retained.
- With the existing cellular-selected relay running, Wi-Fi was enabled and
  verified as Android's default; ten more requests passed. Teather was then
  stopped, freshly installed/started with explicit cellular selection while
  Wi-Fi remained default, and readiness plus ten requests passed again. A final
  180-second single-session transfer passed with 1,547,506 bytes at 8,597 B/s,
  one connection, and zero redirects.
- Final cleanup reported zero matching ADB forwards and no Android relay service.
  Privacy-safe before/after hashes of Linux routes, policy rules, and
  `/etc/resolv.conf` were identical. Firewall comparison was unavailable without
  host privilege; P0 did not issue any firewall mutation. Wi-Fi was left enabled.
- A fresh closeout session at repository commit `f420466` started an explicit
  cellular relay and passed ten more requests. The Android status screen reported
  `cellular (validated)`. One additional short request increased established
  sessions from 10 to 11, client-to-Internet bytes from 7.5 KiB to 8.3 KiB, and
  Internet-to-client bytes from 52.0 KiB to 57.2 KiB. This directionally confirms
  that the live UI counters follow host traffic without retaining a destination.
- An idle SOCKS connection with no buffered payload was confirmed as one active
  Android session. `adb shell am stopservice` moved the UI to stopped, removed the
  service, and the host client observed EOF by the first poll after the stop
  command returned.
- During a separate paced transfer, physical USB removal was detected as ADB
  disconnection. The paced curl could temporarily drain bytes already queued on
  the host, so this run is not evidence of immediate application-level EOF on
  cable removal; the client was canceled locally. Privacy-safe route, policy-rule,
  and resolver hashes were identical before removal and after it. After USB
  reconnection, final cleanup reported no Android relay service, zero matching
  Teather forwards, and zero nonblank ADB forwarding rules.
- `make check` had passed before the unchanged Android APK was originally
  installed on 2026-08-24. A 2026-08-25 rerun reached Gradle but could not start
  Android tasks because this shell had no API 37 SDK location; no Android source
  or APK change was made, so the prior successful source-level evidence remains
  the applicable build result.

### Observation vs. inference

- Observed: the physical phone completed the ten-request and 30-minute
  cellular-only gates, survived locked/dozing state plus a notification wake, and
  completed fresh smoke and three-minute gates while Wi-Fi was Android's default.
  The closeout UI identified the selected upstream as validated cellular, its
  counters advanced with a host request, stopping the service closed an unbuffered
  active session, and cleanup removed Teather service/forward state without
  changing measured Linux network state.
- Inferred: the successful requests used the displayed validated cellular Android
  `Network`, consistent with the connector rejecting non-cellular candidates and
  performing DNS/socket creation on the selected network.
- Not established: provider accounting/classification behavior, behavior on other
  Samsung/Android/carrier combinations, or long-duration Wi-Fi/cellular
  coexistence.

### Follow-up

- P0 is complete. Stop at the P0/P1 boundary. D-013 requires an owner-reviewed
  Linux network design, offline recovery procedure, and explicit owner approval
  before E-002 or any P1 implementation or live host-network mutation begins.
- Resolution on 2026-08-25: D-015 records that approval and the P1 source is now
  implemented. Continue with `docs/P1_HANDOFF.md`; E-002/E-003 remain pending.

## E-002 — System-wide TCP/DNS through the P1 backup interface

**Date:** 2026-08-27 · **Status:** failed at original DNS gate — replacement retest pending

The disposable-VM portion passed without a phone. In a Debian 12.15 GNOME guest,
the real helper created only the approved `teather0` address and routes. QEMU's
metric-100 physical default remained preferred over Teather's metric-32000
default. A controlled DNS query returned `198.18.0.0`; connecting to that address
produced a SOCKS5 domain request for the original synthetic name and received the
controlled HTTP response. Final routes, resolver, NetworkManager inventory,
policy rules, and firewall matched the baseline exactly.

The 2026-08-27 physical run verified the debug APK, Android/ADB control,
compatible attach, exact temporary interface/routes, physical-default preference,
and unprivileged packet engine. The first PolicyKit launch exposed package
`0.1.0-1` setting `NoNewPrivileges=yes`; it failed before mutation. Package
`0.1.0-2` corrected that conflict under D-020 and connected successfully.

After the owner manually disabled Wi-Fi, the host had no usable non-loopback IPv4
nameserver. Teather reported `resolver-unavailable` and disconnected without
changing DNS. The owner's OpenAI session also lost connectivity until Wi-Fi was
restored. Because the mandatory resolver gate failed, browser/Git/SSH/package
workloads and the two-hour session were not attempted. Do not infer that the TUN
data path failed; this run stopped before those tests. The current DNS design is
unsupported on this host and returns to owner review. D-019 continues to defer
permanent release signing until distribution is considered.

**Resolution:** D-021 was accepted and package `0.1.0-3` implements temporary
per-device NetworkManager sentinel DNS plus UDP/TCP virtual DNS. E-002 remains
incomplete until that replacement passes the fresh disposable-VM matrix and the
physical workload/session gate; the failed 2026-08-27 observation is not erased.

On 2026-08-28 a fresh guest installed the reproducible `0.1.0-3` artifact and
reported status API 2. The first integration process ran under SSH, which
PolicyKit classifies as remote; NetworkManager denied `network-control` before
DNS mutation. Manager cleanup removed its TUN/routes, tunnel process, sentinel,
and journal. This is useful failure-path evidence, not a verdict on the active
GNOME product path. The replacement retest must run from the active desktop with
packaged authorization and no permissive test rule.

On 2026-08-29 the replacement retest ran from the guest's real active GNOME
session (confirmed via `loginctl`: `Type=x11 Remote=no Active=yes`), driven
through the actual GDM desktop rather than SSH. Two environment problems were
found and fixed first, unrelated to Teather: the disposable-VM launcher used
`-accel tcg`; under software emulation GNOME Shell segfaulted on an AVX2
gather instruction roughly every 15-25 seconds (a QEMU TCG bug, confirmed via
`dmesg`), and `auth_admin_keep` polkit authorizations expire after a few
minutes, requiring a fresh graphical prompt per attempt (confirmed by
catching the actual "Authentication Required" dialog). Switching the launcher
to `-accel kvm -cpu host` fixed the crash-loop; `/dev/kvm` is available on
this host contrary to the stale 2026-08-26 status note.

With both fixed, `network-control` authorization from the active session
succeeded (NetworkManager's own audit log recorded
`op="device-reapply" ... result="success"`), confirming the original SSH/remote
gate is resolved. The DNS gate still failed at the same
`_wait_nameservers` timeout. A step-by-step manual reproduction (bypassing the
5-second auto-cleanup so state could be inspected) showed `Reapply()` accepts
`ipv4.dns-data=['198.19.0.1']`, `ipv4.dns-priority=-32768`, and
`ipv4.ignore-auto-dns=true` without error, but `/etc/resolv.conf` never
reflects the change even when the interface is held up for 25 seconds, and a
manual `Reload(DNS)` call afterward times out rather than fixing it. The
NetworkManager audit line for the successful `Reapply` itself only lists
`ipv4.dns-priority,ipv4.ignore-auto-dns` as changed args, never `ipv4.dns` or
`ipv4.dns-data`.

**Inference, not yet fully proven:** `teather0` is a NetworkManager
*externally-assumed* connection (`sys-iface-state: 'external'` in the NM
log), because Teather's helper creates the interface with raw `ip` commands
outside NM's connection API. `Reapply()` on an assumed connection appears to
update the stored connection profile without regenerating the live
`IP4Config` object that NM's DNS manager reads — a semantic gap specific to
externally-assumed devices, not a timing or VM-speed problem (reproduced
identically under both TCG and KVM). See D-022 for the proposed replacement
mechanism (NetworkManager-native `tun` connection ownership instead of an
externally-assumed one) and `archive/d021-reapply-dns-approach` for the
preserved working tree of the current implementation before any change.

## E-003 — P1 failure-path restoration

**Date:** 2026-08-26 · **Status:** running

The disposable-VM cleanup portion passed. SIGTERM, SIGINT, forced tunnel death,
and invoking-parent death removed `teather0` and its attached routes. Invalid
input, unavailable proxy, unsafe tunnel mode, interface/address/route collision,
nonstandard policy rules, split default, and VPN-like default refused before
mutation. Repeated disconnect/recover calls were idempotent, while an ambiguous
manually created `teather0` was deliberately preserved.

The matrix exposed normal-route and policy-rule parsing defects, an incorrect
split-default literal comparison, and a tun2proxy `IFF_NO_PI` framing mismatch.
The failures and fixes are retained in the Phase 2 work log and D-015. The final
matrix passed and its baseline/final network snapshots matched.

The 2026-08-27 physical run added two safe-cleanup results. The blocked `pkexec`
launch left no interface, route, forward, or journal. The missing-resolver gate
removed the TUN, routes, forward, helper/tunnel processes, journal, and
NetworkManager's temporary externally observed entry. After Wi-Fi restoration,
routes, rules, resolver, and NetworkManager inventory exactly matched baseline;
nftables rule structure matched after normalizing live packet/byte counters.
Android was stopped explicitly because this case intentionally attached to a
manually started compatible relay.

E-003 remains running because the DNS stop prevented physical USB removal,
daemon/helper/tunnel death, and the rest of the cable/service matrix. D-021
resolves the design decision, but do not resume those physical cases until its
fresh disposable-VM DNS and cleanup gate passes.

## Planned experiment queue

| ID | Question | Milestone |
|---|---|---|
| E-002 | Can a non-persistent Teather backup interface provide TCP/DNS after the owner disables Wi-Fi without mutating the Wi-Fi connection? | P1 |
| E-003 | Does every failure path restore Linux routes and DNS? | P1 |
| E-004 | Can UDP relay support representative DNS, QUIC, and voice traffic? | P2 |
| E-005 | What explicit IPv6 policy is correct for the target environment? | P2 |
| E-006 | Does Android Doze/screen-off interrupt the relay? | P2 |
| E-007 | Can local-only Wi-Fi carry the authenticated relay reliably? | P3 |
| E-008 | How do USB and Wi-Fi compare for throughput, latency, battery, and heat? | P3 |
| E-009 | Can a userspace WireGuard endpoint relay Linux TCP/UDP correctly? | P4 |
| E-010 | Can a mobile WireGuard receiver use the Android-hosted relay? | P4 |
