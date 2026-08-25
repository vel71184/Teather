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

**Date:** 2026-08-24 · **Status:** inconclusive
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

The core physical relay gates passed, but the experiment remains inconclusive
because the Android UI counter/selected-upstream snapshot and active-session
stop/cable-removal checks were not captured.

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

### Observation vs. inference

- Observed: the physical phone completed the ten-request and 30-minute
  cellular-only gates, survived locked/dozing state plus a notification wake, and
  completed fresh smoke and three-minute gates while Wi-Fi was Android's default.
  Cleanup removed the service/forward without changing measured Linux network
  state.
- Inferred: fresh success with explicit `cellular` while Wi-Fi was default used a
  cellular Android `Network`, because the implemented connector rejects
  non-cellular candidates and performs DNS/socket creation on the selected
  network. The UI label was not captured, so retain that as an inference pending
  the final UI evidence check.
- Not established: provider accounting/classification behavior, behavior on other
  Samsung/Android/carrier combinations, or long-duration Wi-Fi/cellular
  coexistence.

### Follow-up

- Complete E-001 by capturing the live Android selected-upstream/counter display
  and exercising active-session service stop and USB removal with cleanup checks.
- Then stop at the P0/P1 boundary. D-013 requires an owner-reviewed Linux network
  design, offline recovery procedure, and explicit owner approval before E-002 or
  any P1 implementation begins.

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
