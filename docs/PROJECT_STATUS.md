# Project status

- **Snapshot date:** 2026-08-24
- **Lifecycle:** implementation / pre-alpha
- **Active milestone:** P0 — Android relay over USB/ADB
- **Runnable build:** physical 30-minute relay validated; E-001 closeout pending

This is the canonical resume point. Update it at the end of every meaningful work
session so the next session starts from evidence instead of archaeology.

## North star

An unrooted Android phone hosts an authenticated Internet relay. A receiver uses
that relay over a replaceable local transport, with Android retaining control of
upstream selection, pairing, status, and session metrics.

## Current objective

Run the implemented vertical path on the owner's actual phone and Linux laptop:

```text
Linux curl -> laptop loopback -> ADB forwarding -> Android SOCKS5 relay
           -> explicitly selected Android Network -> Internet
```

The repository contains the complete P0 source path. The physical ten-request,
30-minute, locked-screen, and Wi-Fi-default/cellular-selected relay gates passed
on the owner's phone. The remaining P0 work is the UI counter/selected-upstream
snapshot plus active-session stop and USB-removal cleanup evidence.

## Implemented P0 surface

- Android application and pinned Gradle wrapper/build configuration.
- User-started connected-device foreground service.
- SOCKS5 no-auth negotiation and TCP `CONNECT` for IPv4, domain, and literal
  IPv6 targets.
- Listener bound strictly to Android `127.0.0.1`.
- Per-connection Android upstream selection and network-bound DNS/socket creation.
- Connection limits, handshake/connect/idle timeouts, cancellation, counters, and
  coarse error categories.
- Minimal Android control/status interface.
- Debug-only exported service lifecycle for ADB automation; release service is
  private.
- Linux helper for redacted discovery, build, install, start, test, soak, logs,
  status, and cleanup.
- Unit/integration tests and GitHub Actions build/lint workflow.
- Placeholder-free laptop continuation guide in `docs/P0_HANDOFF.md`.

## Next concrete actions

On the attached phone, complete only the remaining E-001 evidence:

1. Start a controlled explicit-cellular relay and open the Android status screen.
2. Capture the selected-upstream label and directionally compare its counters with
   one short host transfer; retain no destination or device identifiers.
3. Stop the Android service during an active transfer and verify prompt closure,
   then repeat cleanup verification after USB removal.
4. Update E-001 to passed or failed and stop at the D-013 P0/P1 approval gate.

Do not repeat the 30-minute soak unless a later code change invalidates it.

## Confirmed decisions

- The baseline does not require root or bootloader modification.
- The project is personal-first and source-oriented.
- Linux is the first receiver platform.
- USB/ADB is the first development transport.
- The first relay is SOCKS5 TCP `CONNECT`; P0 is not a custom VPN.
- Android explicitly selects the upstream and remains the long-term control plane.
- Wi-Fi and WireGuard compatibility remain later evidence gates.
- P0 compiles with API 37 but targets API 36; Android 17 local-network permission
  work is intentionally deferred to the Wi-Fi milestone.

See `docs/DECISIONS.md` for rationale and status.

## Important unknowns

- The Android UI counter/selected-upstream snapshot and active-session stop/USB
  removal cleanup checks remain unrecorded.
- Provider classification/accounting behavior is unmeasured and cannot be
  generalized from one result.
- UDP strategy, system-wide Linux TUN integration, and IPv6 policy remain P1/P2
  questions.
- The userspace WireGuard endpoint remains a P4 hypothesis.
- Repository license remains undecided until before public access.

## Explicitly not in progress

- Linux TUN or global route mutation
- UDP relay
- Graphical desktop UI
- Polished Android onboarding
- Local-only Wi-Fi, Wi-Fi Direct, AOA, or Bluetooth
- Windows, macOS, Android, or iOS receivers
- Multi-client product support
- App-store packaging
- Carrier-specific behavior modules

## Hard stop before P1

End P0 after the relay is stopped, cleanup is verified, and E-001/status evidence
is recorded. Do not implement P1 or run live TUN, route, policy-rule, DNS,
firewall, or network-service changes until the exact Linux design and an offline
recovery procedure have been reviewed with the owner and the owner explicitly
approves proceeding. A successful P0 soak does not waive this gate. See D-013 and
the P1 entry gate in `docs/ROADMAP.md`.

## Evidence recorded so far

The source-level P0 implementation and prior CI evidence remain valid. On
2026-08-24, commit `eae4169` plus the working helper hardening built and installed
on a stock Samsung Android 16 phone. Readiness and ten-request gates passed; one
continuous cellular-only SOCKS session transferred 15,334,016 bytes over 1,800
seconds while mostly locked/dozing. A normal notification wake did not interrupt
the flow. A fresh explicit-cellular relay also passed ten requests and a
180-second single-session transfer while Wi-Fi was Android's default. Teather PSS
did not grow monotonically, focused system logs showed no Teather kill/crash or
thermal/data-stall event, final service/forward cleanup succeeded, and before/
after Linux route, rule, and resolver hashes matched. See E-001 for failures,
metrics, inference boundaries, and remaining evidence.

## Session closeout template

```markdown
### YYYY-MM-DD — short description

- Completed:
- Verified with:
- Files/areas changed:
- Decisions made:
- Risks or failures:
- Next exact action:
```

## Work log

### 2026-08-22 — P0 source implementation

- Completed: pinned Android build, foreground relay lifecycle, loopback SOCKS5 TCP
  server, explicit Android network binding, UI/status, JVM tests, Linux ADB helper,
  CI workflow, and laptop/phone handoff.
- Verified with: shell syntax, XML parsing, placeholder scan, and GitHub Actions
  run `32607599774` (`testDebugUnitTest`, `lintDebug`, and `assembleDebug`).
- Decisions made: API/toolchain package identity and debug-only ADB lifecycle
  exposure, recorded as D-011 and D-012.
- Risks or failures: CI exposed an asynchronous test-observation race; PR review
  exposed per-direction idle handling, a non-continuous soak, discarded startup
  failures, and missing coarse log events. All five defects were repaired and the
  hardened commit passed CI. No physical Android device was available.
- Next exact action: run the commands in `docs/P0_HANDOFF.md` from the laptop.

### 2026-08-24 — P0 physical relay and soak validation

- Completed: installed the debug APK; hardened helper readiness, failure cleanup,
  and paced-transfer validation; passed cellular-only smoke, 180-second, and
  1,800-second gates; passed fresh explicit-cellular smoke and 180-second transfer
  while Wi-Fi was default; verified final service/ADB-forward cleanup and unchanged
  Linux route/rule/resolver hashes.
- Verified with: `make check`, repeated `./desktop/linux/teather-p0 all`,
  `TEATHER_SOAK_SECONDS=180 ./desktop/linux/teather-p0 soak`, the default
  1,800-second `soak`, memory samples, focused system logcat review, `stop`, and
  `status`.
- Files/areas changed: Linux P0 helper, P0 handoff, E-001 experiment evidence,
  project status, roadmap, and decision log.
- Decisions made: D-013 requires a reviewed Linux networking/rollback plan,
  offline recovery commands, and explicit owner approval before P1 implementation
  or live host-network mutation.
- Risks or failures: the original helper had a service-start race and a curl
  low-speed/rate-limit self-conflict; both were isolated and repaired. UI
  selected-upstream/counter evidence and active-stop/USB-removal cleanup remain.
  Provider accounting and other device/provider combinations remain unknown.
- Next exact action: capture the remaining E-001 UI and active-stop/USB-removal
  evidence, then stop at the D-013 owner-approval gate.
