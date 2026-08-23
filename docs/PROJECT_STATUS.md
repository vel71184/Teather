# Project status

- **Snapshot date:** 2026-08-22
- **Lifecycle:** implementation / pre-alpha
- **Active milestone:** P0 — Android relay over USB/ADB
- **Runnable build:** CI-verified debug APK; physical-phone validation pending

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

The repository now contains the complete P0 source path. The remaining P0 work is
runtime evidence, not additional speculative architecture.

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

On a Linux laptop with the phone physically attached:

1. Read `docs/P0_HANDOFF.md`.
2. Run `make check`.
3. Run `./desktop/linux/teather-p0 doctor`.
4. Run `./desktop/linux/teather-p0 all`.
5. Run `./desktop/linux/teather-p0 soak`.
6. Stop the relay and verify the matching ADB forward is removed.
7. Record the redacted environment and observed results in experiment E-001.

No source value needs to be filled in before these commands. `TEATHER_SERIAL` is
needed only in a shell with multiple ADB devices and must never be committed.

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

- The P0 source has not run on the owner's actual phone/provider connection.
- Screen-off, Doze, upstream changes, 30-minute transfer, and thermal behavior are
  unmeasured.
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

## Evidence recorded so far

The source-level P0 implementation exists. GitHub Actions run `32607599774` passed
at commit `0914eb5`: all six JVM tests, Android lint, and debug APK assembly
succeeded with the pinned wrapper/JDK/toolchain. That run includes a regression
test proving one-way active streams survive the connection-wide idle policy. The
Android ChatGPT workspace also passed shell syntax, XML well-formedness, and
placeholder scans. No attached phone was available, so device/network claims
remain unverified until E-001 runs.

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
