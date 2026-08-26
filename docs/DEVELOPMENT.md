# Development guide

Teather has a physically validated P0 implementation. This guide defines the
pinned build, host workflow, and evidence boundary; P1 remains behind the D-013
design-review and owner-approval gate.

## Pinned P0 toolchain

| Item | Pinned value |
|---|---|
| Application ID | `io.github.vel71184.teather` |
| Minimum / target / compile API | 26 / 36 / 37 |
| Android Gradle plugin | 9.1.1 |
| Gradle wrapper | 9.3.1 |
| JDK | 17 |
| Debug APK | `app/build/outputs/apk/debug/app-debug.apk` |

The wrapper distribution checksum and wrapper JAR checksum are both enforced.
Android Studio is optional; the checked-in wrapper is the build interface.

## Runtime environment discovery

Do not hand-edit phone or laptop facts into code. With one authorized phone
attached, run:

```bash
./desktop/linux/teather-p0 doctor
```

It reports the current commit, non-sensitive host/network-manager details, ADB and
Java versions, and phone model/Android version while deliberately omitting the ADB
serial. If multiple devices exist, set `TEATHER_SERIAL` in the shell only.

## P0 prerequisites

- Linux with Git, Bash, curl, JDK 17, and Android platform tools (`adb`).
- Physical stock/unrooted Android device with USB debugging enabled.
- One-time approval of the laptop's ADB key on the unlocked phone.
- Android API 37 installed locally, or network access for Gradle/SDK setup.
- No stock hotspot or stock USB tethering during E-001.

The exact continuation is maintained in `docs/P0_HANDOFF.md`.

## Development sequence

Use narrow vertical slices:

1. Start and stop a foreground Android service.
2. Listen on Android loopback and return a fixed test response through ADB.
3. Open one outbound socket through an explicitly selected upstream.
4. Implement the minimum SOCKS5 CONNECT path.
5. Verify repeated Linux TCP requests.
6. Add cancellation, timeouts, counters, and clean shutdown.
7. Only then introduce TUN and receiver routing.

Avoid building the full configuration model, theme, tray icon, or generic plugin
system before step 6 passes.

## Planned local workflow

The repository exposes these commands through the checked-in `Makefile` and
`desktop/linux/teather-p0` helper:

```text
check          format, lint, and unit tests
android-build  build the debug APK
android-run    install/start the development relay
linux-build    build the receiver
e2e-p0         run the non-destructive P0 test
diagnose       print redacted environment and link state
```

Implemented equivalents are `make check`, `make android-build`, `make p0-doctor`,
`make p0-run`, `make p0-test`, and `make p0-stop`. The helper additionally provides
`status`, `logs`, and the 30-minute `soak` gate.

## Branches and commits

- Keep `main` in a documented, internally consistent state.
- Use short-lived branches once implementation begins.
- Prefer one coherent behavior change per commit.
- Use imperative commit subjects, such as `Add Android relay lifecycle`.
- Include experiment or decision-document changes in the same pull request as the
  behavior they validate or establish.
- Do not rewrite shared history merely to make exploratory work look linear.

## Configuration and secrets

- Development ports and non-secret defaults belong in versioned configuration.
- Private keys, ADB keys, device identifiers, provider credentials, and local
  network credentials never belong in Git.
- Generated test keys must be clearly marked and unusable outside tests.
- Local overrides should use ignored files with an `.example` template once the
  first real option exists.
- Logs and diagnostics must be reviewed before attaching them to issues.

## Android implementation rules

- Keep activity/Compose UI separate from relay lifecycle.
- Use a foreground service for sustained user-initiated operation.
- Make upstream selection explicit and observable.
- Perform network I/O off the main thread.
- Every accepted connection has a timeout and cancellation path.
- Do not bind a development relay to Wi-Fi/LAN interfaces without authentication.
- Handle notification permission and foreground-service restrictions according to
  the selected target SDK.
- Avoid hidden or reflection-based platform APIs.

## Linux implementation rules

- Start P0 with loopback proxying; do not mutate global routes unnecessarily.
- Before P1 mutation, snapshot relevant links, addresses, routes, rules, resolver
  state, and Teather-owned firewall entries.
- Apply the smallest possible route change.
- Exclude the relay transport path from the tunnel route.
- Track only state created by Teather and remove only that state.
- Trap normal termination signals and provide idempotent cleanup.
- Provide a separate diagnostic command that performs no mutations.
- Never grant the GUI or a broad command wildcard passwordless privilege.

## Logging

Use structured categories from the beginning:

- `android.lifecycle`
- `android.upstream`
- `transport.adb`
- `relay.socks`
- `receiver.tun`
- `receiver.route`
- `dns`
- `session`

Default logs may include timestamps, component, state transition, byte counts, and
coarse error type. Destination hostnames/IP addresses and payloads should be
redacted unless the user explicitly enables a time-limited diagnostic mode.

## Dependency policy

Before adding a dependency:

- Verify its maintenance status and license.
- Prefer a focused library over a framework that owns the architecture.
- Pin enough information for a reproducible build.
- Record why a security-sensitive networking or cryptography dependency was
  selected.
- Do not write custom cryptography.

## Definition of done

A change is complete when:

- The behavior works on the current target environment.
- Relevant automated tests pass.
- Manual network-state restoration is verified where applicable.
- Logs explain expected failure modes.
- No sensitive files are staged.
- Architecture, decision, experiment, test, and status documents are updated as
  needed.
- The next exact task is left in `docs/PROJECT_STATUS.md`.
