# Project status

- **Snapshot date:** 2026-08-25
- **Lifecycle:** implementation / pre-alpha
- **Active milestone:** P0 complete — stopped at the P1 entry gate
- **Runnable build:** P0 Android relay over USB/ADB validated; E-001 passed

This is the canonical resume point. Update it at the end of every meaningful work
session so the next session starts from evidence instead of archaeology.

## North star

An unrooted Android phone hosts an authenticated Internet relay. A receiver uses
that relay over a replaceable local transport, with Android retaining control of
upstream selection, pairing, status, and session metrics.

## Current objective

P0 proved the implemented vertical path on the owner's actual phone and Linux
laptop:

```text
Linux curl -> laptop loopback -> ADB forwarding -> Android SOCKS5 relay
           -> explicitly selected Android Network -> Internet
```

The physical ten-request, 30-minute, locked-screen,
Wi-Fi-default/cellular-selected, UI-counter, active-stop, and USB-removal cleanup
gates passed on the owner's phone. The current objective is discussion only:
review the exact P1 route, DNS, privilege, failure-cleanup, and offline recovery
design. Do not implement P1 or mutate live host networking before owner approval.

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

1. Discuss the proposed P1 `teather0`, route-preference, scoped-DNS, privilege,
   recursion-prevention, saved-state, and cleanup design without touching live
   networking.
2. Produce exact offline recovery commands and validate the design in a network
   namespace or disposable VM where possible.
3. Present the complete plan for owner review. Do not implement or run live P1
   networking commands unless the owner explicitly approves it.

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
- P1's first Linux mode is a non-persistent `teather0` backup interface. Existing
  Wi-Fi/Ethernet remains untouched and preferred; the owner manually disables or
  restores it. Teather performs no NetworkManager writes (D-014).

See `docs/DECISIONS.md` for rationale and status.

## Important unknowns

- Provider classification/accounting behavior is unmeasured and cannot be
  generalized from one result.
- Safe Teather-owned DNS and exact backup-route preference remain unresolved P1
  design work. Disabling Wi-Fi may remove its resolver or leave an unreachable
  LAN-only resolver; P0 `socks5h` covers explicit proxy clients, not transparent
  TUN applications. UDP strategy and IPv6 policy remain P2 questions.
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

P0 ended with the relay stopped, cleanup verified, and E-001/status evidence
recorded. Do not implement P1 or run live TUN, route, policy-rule, DNS,
firewall, or network-service changes until the exact Linux design and an offline
recovery procedure have been reviewed with the owner and the owner explicitly
approves proceeding. A successful P0 soak does not waive this gate. See D-013 and
the P1 entry gate in `docs/ROADMAP.md`. D-014 fixes the desired operating model
but does not authorize implementation: Teather creates only its own temporary
backup interface and scoped network state, performs no NetworkManager writes, and
never alters an existing Wi-Fi/Ethernet connection or profile.

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
metrics, inference boundaries, and closeout evidence. On 2026-08-25, a fresh
explicit-cellular smoke passed, the UI reported `cellular (validated)` and
directionally advancing counters, an unbuffered active session closed when the
Android service stopped, and USB removal left measured Linux network state
unchanged. Final cleanup left no service or ADB forward.

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

### 2026-08-24 — Linux backup-interface requirement

- Completed: aligned README, architecture, roadmap, test plan, threat model,
  experiment queue, and status around the first P1 Linux operating model.
- Decisions made: D-014 requires a non-persistent `teather0` with lower preference
  than existing physical defaults. Teather performs no NetworkManager writes and
  never changes existing Wi-Fi/Ethernet profiles, routes, or DNS; the owner
  manually toggles Wi-Fi to select or recover the path.
- Risks or failures: exact route preference and safe Teather-owned scoped DNS are
  unresolved. P1 remains blocked by D-013 until those commands and offline
  recovery steps are reviewed and explicitly approved.
- Next exact action: finish the remaining E-001 evidence. Before P1, design and
  review route/DNS behavior in a namespace or VM without touching the live host.

### 2026-08-25 — P0 evidence closeout

- Completed: passed a fresh ten-request explicit-cellular smoke; captured the
  Android `cellular (validated)` label and directionally advancing counters;
  verified that stopping the service closes an unbuffered active SOCKS session;
  exercised physical USB removal and final cleanup; marked E-001 passed.
- Verified with: `./desktop/linux/teather-p0 doctor`, `start`, `test`, `status`,
  and `stop`; the Android visible status; an isolated idle SOCKS connection;
  physical USB removal/reconnection; and before/after SHA-256 hashes of all Linux
  routes, policy rules, and `/etc/resolv.conf`.
- Files/areas changed: README, roadmap, E-001 experiment evidence, and project
  status.
- Decisions made: none. D-013 and D-014 remain authoritative.
- Risks or failures: today's `make check` rerun could not locate an API 37 SDK;
  the unchanged APK retains the successful 2026-08-24 build evidence. A paced
  curl retained host-buffered bytes after USB removal, so cable removal does not
  establish immediate application-level EOF. Provider accounting remains
  unmeasured.
- Next exact action: remain at the hard stop and review the complete P1 Linux
  route/DNS/privilege/rollback plan with the owner before implementation.
