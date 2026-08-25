# P0 laptop and phone handoff

This is the execution contract for the first Codex session that has both the
repository and an Android phone attached through ADB. It contains no values that
must be guessed or manually substituted. The checked-in helper discovers the
host and phone environment at runtime and keeps device serials out of its output.

## What is already implemented

- Android application ID: `io.github.vel71184.teather`
- Minimum Android API: 26
- Compile API: 37
- Target API: 36
- Android Gradle plugin: 9.1.1
- Gradle wrapper: 9.3.1, with distribution and wrapper checksums pinned
- JDK: 17
- Debug relay listener: `127.0.0.1:1080` by default
- Relay protocol: SOCKS5, no-authentication method, TCP `CONNECT`
- Android upstream modes: cellular, Wi-Fi, Ethernet, or automatic
- Outbound DNS and sockets: explicitly resolved and created on the selected
  Android `Network`
- Host automation: `desktop/linux/teather-p0`

The debug manifest exports the service lifecycle so the ADB helper can start it
without UI automation. The release manifest keeps the service unexported. In
both builds the SOCKS listener binds only to Android loopback. Android loopback is
still reachable by other local apps, so the no-auth SOCKS service is a controlled
P0 experiment, not a releasable authentication design. Stop it after testing and
do not use the debug APK on an untrusted app environment. It is never exposed to
Wi-Fi or another shared link.

## Physical actions that cannot be committed to Git

1. Enable Android Developer options and USB debugging if they are not already on.
2. Connect the phone to the Linux laptop with a data-capable USB cable.
3. Unlock the phone and approve the laptop's ADB key when Android asks.

That is the entire human-only boundary. Do not paste or commit the ADB serial,
ADB keys, phone number, subscriber identifiers, account data, or raw captures.

## Exact continuation sequence

From the repository root:

```bash
./desktop/linux/teather-p0 doctor
./desktop/linux/teather-p0 all
./desktop/linux/teather-p0 soak
```

`doctor` reports the non-sensitive values required by experiment E-001:

- current Teather commit;
- Linux distribution, kernel, desktop/session, and detected network manager;
- ADB and Java versions;
- phone manufacturer/model and Android release/API;
- selected relay port and upstream policy.

`all` builds, installs, starts ADB forwarding, starts the Android foreground
service, waits for one successful readiness request, and then makes the ten
consecutive HTTPS requests counted by the smoke gate. A failed readiness or smoke
gate stops the app and removes the matching forward. `soak` holds one SOCKS session
open with a rate-limited 25 MB response from Cloudflare's public speed-test
endpoint for 1,800 seconds by default. At 8 KiB/s, the 30-minute gate consumes
roughly 14 MiB. The helper reports downloaded bytes, average rate, elapsed time,
connection count, redirects, and exit status without retaining the effective URL.
It requires at least 75 percent of the configured pacing rate and exactly one
SOCKS connection.

The helper does not combine curl's low-speed watchdog with rate limiting because
those options can make curl abort its own intentional pacing pauses; the relay's
five-minute aggregate idle timeout still bounds a genuinely stalled session. A
different harmless streaming URL, rate, or duration can be supplied without
editing source:

```bash
TEATHER_SOAK_URL='https://speed.cloudflare.com/__down?bytes=25000000' \
TEATHER_SOAK_RATE=8K TEATHER_SOAK_SECONDS=1800 \
  ./desktop/linux/teather-p0 soak
```

If more than one ADB device is attached, set `TEATHER_SERIAL` only in the shell.
Never put it in a tracked configuration file.

## Useful commands

```bash
./desktop/linux/teather-p0 status
./desktop/linux/teather-p0 logs
./desktop/linux/teather-p0 stop
```

The Android app also provides start/stop controls, upstream selection, counters,
coarse error categories, and a button that copies the two raw ADB/curl commands.
It never displays or logs destination hosts.

## What laptop Codex should verify

1. Run `make check` before installing anything.
2. Run `doctor` and summarize its redacted output in E-001.
3. Confirm Android stock hotspot and stock USB tethering are off.
4. Run `all`; preserve exact command outcomes, not raw destination logs.
5. Run `soak` with the phone screen both on and off.
6. Stop Teather and confirm `desktop/linux/teather-p0 status` reports no service
   and no matching ADB forward.
7. Update `docs/EXPERIMENTS.md` and `docs/PROJECT_STATUS.md` with observations,
   failures, and the next exact action.
8. Stop the work session at the P0/P1 boundary. Do not implement or exercise TUN,
   route, policy-rule, DNS, firewall, or network-service changes until the D-013
   design review is complete and the owner explicitly approves proceeding.

Passing the P0 exit criteria is necessary but is not authorization to start P1.
The next session should discuss the Linux design, rollback paths, and offline
recovery commands before implementation so loss of the current Internet/chat
connection cannot also remove the recovery instructions.

## Failure isolation

| Symptom | First check | Layer |
|---|---|---|
| `no authorized ADB device` | Unlock phone and accept the USB-debugging prompt | USB/ADB |
| Gradle refuses Java | `java -version`; use JDK 17 | Build |
| Service not present | `teather-p0 logs`; open the app once if notification permission was denied | Android lifecycle |
| Curl cannot reach port | `teather-p0 status`; recreate only the Teather forward | ADB transport |
| SOCKS reply is network/host unreachable | Verify the selected upstream is actually connected | Android upstream |
| Ten requests pass but soak fails | Inspect coarse `Teather` log categories and screen-off timing | Relay lifecycle |

## Deliberate P0 limits

- No UDP, TUN, system-wide routes, or DNS takeover
- No settled IPv6 policy, although literal IPv6 SOCKS destinations can be parsed
- No Wi-Fi listener, discovery, pairing, or multi-client product support
- No guarantee about provider classification or accounting
- Five-minute connection-wide idle timeout; traffic in either direction keeps the
  session alive
- Maximum 64 simultaneous development sessions

These are milestone boundaries, not filler. Change one only through a tested code
change and, when architectural, a decision-log entry.
