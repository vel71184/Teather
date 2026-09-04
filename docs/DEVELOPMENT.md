# Development guide

P1 (Linux USB Desktop) is complete and is the owner's daily connection.
NetworkManager owns `teather0` as an in-memory `tun` connection with no
privileged helper, additive DNS, and automatic failover (D-022). Post-P1, all
live-verified: upstream switching (D-023), general UDP over udpgw (D-024),
standalone connect (D-025), abnormal-disconnect self-heal (D-026), SOCKS relay
authentication (D-028), APK bundling/install (D-029), release signing (D-030),
the security-version layer (D-031), and the shared design language (D-032,
`docs/DESIGN_LANGUAGE.md`). Current build: Debian `0.1.0-19` /
Android `0.1.0-p1.6`
(`versionCode 8`). `docs/PROJECT_STATUS.md` is the resume point.

## Pinned Android and P1 toolchain

| Item | Pinned value |
|---|---|
| Application ID | `io.github.vel71184.teather` |
| Minimum / target / compile API | 26 / 36 / 37 |
| Android Gradle plugin | 9.1.1 |
| Gradle wrapper | 9.3.1 |
| JDK | 17 |
| Debug APK | `app/build/outputs/apk/debug/app-debug.apk` |
| P1 Android version | `versionCode 8` / `0.1.0-p1.6` (SOCKS relay auth — D-028, status schema 2; "get desktop client" button — D-029; appearance setting; security-version layer — D-031; design-language visual pass — D-032) |
| Android SDK | `~/Android/Sdk` (`local.properties`, gitignored) — `platforms/android-37`, `build-tools/37.0.0` |
| Release signing | D-030: `keystore.properties` at the repo root (gitignored) or `TEATHER_KEYSTORE*` env; debug-key fallback with a warning |
| P1 Linux target | Debian 12 GNOME amd64 |
| P1 desktop stack | Python 3.11, PyGObject, GTK 3, Ayatana AppIndicator |
| Packet engine | tun2proxy 0.8.3 plus audited Linux packet-information and TCP virtual-DNS patches with a checked-in Cargo lock; run as `--tun teather0` |
| Rust toolchain | 1.90.0 |

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

## P0 reproduction prerequisites

- Linux with Git, Bash, curl, JDK 17, and Android platform tools (`adb`).
- Physical stock/unrooted Android device with USB debugging enabled.
- One-time approval of the laptop's ADB key on the unlocked phone.
- Android API 37 installed locally, or network access for Gradle/SDK setup.
- No stock hotspot or stock USB tethering during E-001.

The historical P0 reproduction sequence is maintained in `docs/P0_HANDOFF.md`.
The current P1 continuation is `docs/P1_HANDOFF.md`.

## Completed P0 development sequence

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

## Current local workflow

The repository exposes these commands through the checked-in `Makefile` and
`desktop/linux/teather-p0` helper:

```text
make check             Android tests/lint/APKs plus all host-only P1 checks
make android-build     build the debug APK
make p1-check          Linux unit tests and the private D-Bus smoke test
make p1-dbus-smoke     isolated D-Bus daemon/CLI smoke test
make p1-package        build the amd64 Debian package
make p0-doctor         historical redacted P0 discovery
make p0-run/test/stop  historical P0 device workflow
```

`make check` is the source-level gate and does not create a live TUN, contact
NetworkManager, or change host routes. P1 GUI, package-lifecycle, and physical
validation is separate and must follow `docs/P1_HANDOFF.md`. The P0 helper
additionally provides `status`, `logs`, and the historical 30-minute `soak`
gate.

Since D-029, `make p1-package` bundles the Android APK into the `.deb`, so build
it first (`make android-build`, or an `assembleRelease` once a release key is
configured — `build-deb.sh` prefers `app-release.apk` and warns when it falls
back to the debug APK).

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

Since D-026 the Linux daemon writes a persistent rotating log to
`~/.local/state/teather/teatherd.log` (mode 0600) in addition to the journal;
`TEATHER_DEBUG=1` in the service environment raises it to DEBUG (every `adb`
argv, every poll tick). `adb` serials are redacted to `<device>`; destinations
and resolver contents are never logged. It is the first place to look when the
tether misbehaves.

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
- Any doc the change actually touched (architecture, decision, experiment, test)
  is updated, and `docs/PROJECT_STATUS.md` reflects the new state at the end of
  the work session. No per-change status write, no "next exact task" handoff.
