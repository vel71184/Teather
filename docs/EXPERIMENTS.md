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

**Date:** not run  
**Status:** planned  
**Question:** Can a Linux TCP client reach the Internet through an unrooted Android
application relay reached over USB/ADB, using an explicitly selected Android
upstream?

### Environment

- Phone model: **to record**
- Android version/build family: **to record**
- Teather commit: **to record**
- Linux distribution/version: **to record**
- Desktop/network manager: **to record**
- ADB version: **to record**
- Upstream type: cellular initially
- Provider context: **to record without account identifiers**

### Preconditions

- Phone is stock and unrooted.
- USB debugging is enabled and the Linux host is explicitly authorized.
- Android stock hotspot and USB tethering are off.
- Linux has another known-good path available for setup, or required dependencies
  are already installed.
- Baseline stock-tethering behavior and visible provider accounting are noted if
  it is safe and permitted to test them.

### Procedure

1. Start the minimal Android foreground relay.
2. Confirm it listens only on the intended development endpoint.
3. Establish ADB port forwarding to a Linux loopback port.
4. Configure one test client to use the proxy.
5. Request a small known test resource ten times.
6. Transfer a non-sensitive test payload continuously for thirty minutes.
7. Record byte counts on Android and Linux.
8. Stop the service and verify connections close.
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

Not run.

### Observation vs. inference

- Observed: none yet.
- Inferred: the architecture is feasible based on available Android socket and ADB
  behavior, but target-device/provider behavior is unverified.

### Follow-up

- If successful, proceed to E-002 and P1 TUN integration.
- If unsuccessful, isolate ADB transport, Android upstream selection, and SOCKS
  handling before changing architecture.

## Planned experiment queue

| ID | Question | Milestone |
|---|---|---|
| E-002 | Can Linux TUN/tun2socks provide system-wide TCP and tunneled DNS? | P1 |
| E-003 | Does every failure path restore Linux routes and DNS? | P1 |
| E-004 | Can UDP relay support representative DNS, QUIC, and voice traffic? | P2 |
| E-005 | What explicit IPv6 policy is correct for the target environment? | P2 |
| E-006 | Does Android Doze/screen-off interrupt the relay? | P2 |
| E-007 | Can local-only Wi-Fi carry the authenticated relay reliably? | P3 |
| E-008 | How do USB and Wi-Fi compare for throughput, latency, battery, and heat? | P3 |
| E-009 | Can a userspace WireGuard endpoint relay Linux TCP/UDP correctly? | P4 |
| E-010 | Can a mobile WireGuard receiver use the Android-hosted relay? | P4 |

