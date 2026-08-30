# Project status

- **Snapshot date:** 2026-08-30
- **Lifecycle:** implementation / pre-alpha
- **Active milestone:** P1 — Linux USB Desktop. Acceptance met: D-022
  is validated end-to-end and running live on the developer host. The owner has
  since directed a post-P1 track of work (see the 2026-08-30 entries and the
  punch list) — not P2 as scoped by D-018. UDP/IPv6 "protocol completeness"
  stays deferred; the owner rejected the roadmap's assumption that all of P2/P4
  must happen. Next build task: track 2, lightweight UDP.
- **Runnable build:** Android `0.1.0-p1.1` (`versionCode 3`); Debian package
  `0.1.0-6` (rebuild pending). `0.1.0-4` = D-022 (NetworkManager owns `teather0`
  as an in-memory `tun` connection, no setuid helper or polkit action, additive
  DNS, automatic failover). `0.1.0-5` adds D-023 (`teather upstream
  auto|cellular|wifi|ethernet`). `0.1.0-6` / `0.1.0-p1.1` makes the upstream
  switch zero-gap (`ACTION_RECONFIGURE`, also phone-side), matches the Android
  icon to the Linux artwork, and drops stale "P0" wording. 48 host unit tests +
  Android unit tests + D-Bus smoke pass; the `0.1.0-p1.1` APK is built but not
  yet on the phone. **Validated end to end on 2026-08-30**: in the
  disposable VM with the phone on USB passthrough, then installed and run on the
  actual laptop — `teather connect` works, traffic exits on the phone's Verizon
  cellular (`203.0.113.10`), `teather upstream wifi` flips it to the phone's
  Wi-Fi exit (`198.51.100.20`) with `teather0`/tunnel/DNS/forward untouched, DNS +
  routing fail over automatically when the physical link drops and restore
  cleanly, and every teardown returns the host to exact baseline. GUI and
  package lifecycle pass. See the 2026-08-30 work-log entries.

This is the resume point. Update it at the end of a meaningful work session so
the next one starts from evidence instead of archaeology.

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

The physical P0 gates passed on the owner's phone. On 2026-08-25 the owner
provided the complete P1 implementation plan and explicitly requested its
implementation. This satisfies D-013's source-implementation approval gate. The
bounded desktop, Android control, recovery, and package surfaces are implemented
and pass host checks. The disposable-VM Phase 1 package, D-Bus, real GNOME
GUI/tray/fallback, watcher, and no-mutation gate passed on 2026-08-26 (against
the older helper-based package). D-019 accepts Gradle's debug signing for
private P1 testing. The debug APK is verified. On 2026-08-27 the physical run
connected the bounded tunnel but disabling Wi-Fi removed the only usable
non-loopback IPv4 nameserver; Teather failed safely and restored owned state.
D-021's `Reapply` DNS design was then implemented and disproven against real
NetworkManager (E-002). **D-022 (NetworkManager owns `teather0`, no privileged
helper, additive DNS, automatic failover) and D-023 (`teather upstream` picks
the phone's transport) are implemented and validated** — in the disposable VM
and then live on this laptop (see the 2026-08-30 work log). P1's question is
answered. The current objective is the P2 design discussion (D-018); the owner
is daily-driving `0.1.0-5` in the meantime.

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
- P0 originally used a debug-only exported service lifecycle. P1 supersedes it
  with a release service protected by `android.permission.DUMP`.
- Linux helper for redacted discovery, build, install, start, test, soak, logs,
  status, and cleanup.
- Unit/integration tests and GitHub Actions build/lint workflow.
- Placeholder-free laptop continuation guide in `docs/P0_HANDOFF.md`.

## Next concrete actions

1. **Stop for the P2 design discussion (D-018)** before any general-UDP / IPv6 /
   broader-DNS / WireGuard / wireless-transport work. P2 = "Protocol
   Completeness": a documented UDP relay path, explicit IPv6 policy and tests,
   DNS A/AAAA behaviour, keepalive/backpressure, suspend/resume. Let real
   daily-use friction inform the priorities.
2. When the APK is next built: unify the Android launcher icon to the Linux
   `desktop/linux/resources/icons/teather.svg` art (owner preference); update
   any TCP-only UI strings once P2 adds UDP.
3. Optional, if the owner wants a belt-and-suspenders safety net for bare-host
   daily use: the standalone auto-revert / dead-man's-switch sketched in the
   2026-08-29 conversation (not built).

`~/teather-host-evidence/` holds the host before/after network snapshots.
Generated `__pycache__`, private VM evidence, and signing keys are not
implementation artifacts and must not be staged.

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
  Wi-Fi/Ethernet stays untouched and preferred; Teather takes over automatically
  only once such a link is actually gone, with a per-user opt-out (D-014 as
  amended by D-022).
- The P1 route, virtual-DNS, trust, D-Bus, packaging, and recovery architecture
  is approved (D-015 through D-017).
- Work must stop for explicit planning and approval after P1, before P2 (D-018).
- Private P1 device testing uses debug signing; permanent signing is deferred
  until distribution is considered (D-019).
- NetworkManager owns `teather0` as an in-memory `tun` connection
  with `tun.owner` delegation and additive DNS; there is no setuid-root helper or
  custom polkit action (D-022, supersedes D-020 and D-021).

See `docs/DECISIONS.md` for rationale and status.

## Important unknowns

- Provider classification/accounting behavior is unmeasured and cannot be
  generalized from one result.
- Carrier classification/accounting over sustained tethering-like use is
  unmeasured — that is the owner's daily use, not a synthetic gate. General UDP
  and IPv6 remain P2.
- The userspace WireGuard endpoint remains a P4 hypothesis.
- Repository license remains undecided until before public access.

## Explicitly not in progress

- UDP relay
- Polished Android onboarding
- Local-only Wi-Fi, Wi-Fi Direct, AOA, or Bluetooth
- Windows, macOS, Android, or iOS receivers
- Multi-client product support
- App-store packaging
- Carrier-specific behavior modules

## Deferred / punch list

Small items, not blocking, to fold into the next relevant change:

1. ~~**Launcher icon.**~~ Done 2026-08-30 (`0.1.0-p1.1`): `ic_teather.xml` now
   mirrors `desktop/linux/resources/icons/teather.svg`.
2. ~~**Zero-gap upstream toggle + phone-side live change.**~~ Done 2026-08-30
   (`0.1.0-p1.1`): `RelayService.ACTION_RECONFIGURE` +
   `RelayRuntime.reconfigure()` swap the live `AndroidNetworkConnector`'s
   transport in place — no `Socks5Server` teardown, established sessions keep
   their transport, no gap. `teather upstream` (via `adb.reconfigure_relay`) and
   the phone's `MainActivity` spinner both drive it. Not yet exercised on the
   phone.
3. **Bare-host auto-revert safety net.** Optional dead-man's-switch for
   daily-driver host use — a `systemd-run` timer armed at connect that runs a
   standalone `nmcli con down/delete teather0` revert unless a connectivity
   heartbeat keeps re-arming it. Sketched 2026-08-29, not built. Only worth it
   if the owner wants zero-babysit confidence beyond `teather disconnect` /
   `docs/P1_RECOVERY.md`.

## P1 authorization and live-test boundary

The owner-approved implementation plan on 2026-08-25 resolves D-013 and authorizes
P1 source work. It does not authorize unbounded experimentation on the active
host: network behavior must pass isolated tests first, and the physical gate must
capture before/after routes, rules, resolver, NetworkManager, and firewall
state. D-022 authorizes only the one in-memory `teather0` `tun`
connection through NetworkManager; persistent profiles, direct resolver edits,
firewall, policy rules, and any change to a physical link remain forbidden.

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

## Work log

A short dated entry per meaningful session: what changed, how it was verified,
and the next action. When a milestone finishes, make sure the roadmap, this
file, `AGENTS.md`'s "Current priority", the README status line, and the next
handoff agree — a milestone isn't done until they do.

### 2026-08-30 — Zero-gap upstream switch + Linux-matched icon + stale-text cleanup

- Completed (punch-list items 1 and 2; Android `versionCode 3` / `0.1.0-p1.1`,
  Debian `0.1.0-6`):
  - `RelayService.ACTION_RECONFIGURE` → `RelayRuntime.reconfigure()` swaps the
    running `AndroidNetworkConnector`'s transport preference in place (new
    `@Volatile var preference` + `rebind()`), instead of going through
    `RelayStartPolicy`. No `Socks5Server` teardown, the SOCKS listener stays
    bound, and sessions already established keep their transport (a live TCP
    socket cannot move) — no client sees a gap. A port change or a stopped relay
    still falls back to a full (re)start.
  - `desktop` drives it via `adb.reconfigure_relay(serial, upstream)`;
    `manager.set_upstream` no longer does stop+start. The phone's `MainActivity`
    upstream spinner now sends `ACTION_RECONFIGURE` while the relay runs, so the
    transport can be changed phone-side too.
  - `app/.../drawable/ic_teather.xml` redrawn to mirror
    `desktop/linux/resources/icons/teather.svg` (owner prefers the Linux logo).
  - `screen_description` string and the `Socks5Protocol` "Only CONNECT … in P0"
    message reworded off the stale P0 framing.
- Verified with: `./gradlew :app:testDebugUnitTest :app:lintDebug
  :app:assembleDebug` (green; new `Socks5ServerIntegrationTest` case proves a
  connector rebind steers only new sessions) and 48 Linux host unit tests
  (`FakeAdb` grew `reconfigure_relay`; the upstream-toggle test now asserts no
  stop/start). **Not yet exercised on the phone** — needs the APK reinstalled
  and a live `teather upstream` switch under load.
- Files/areas changed: `app/.../service/{RelayService,RelayRuntime}.kt`,
  `app/.../network/AndroidNetworkConnector.kt`, `app/.../relay/Socks5Protocol.kt`,
  `app/.../MainActivity.kt`, `app/.../res/values/strings.xml`,
  `app/.../res/drawable/ic_teather.xml`, `app/build.gradle.kts`,
  `app/src/test/.../Socks5ServerIntegrationTest.kt`; `desktop/linux/teather/
  {constants,adb,manager}.py`, `desktop/linux/tests/test_core.py`;
  `packaging/debian/{control,changelog}`, `packaging/scripts/build-deb.sh`,
  `packaging/man/teather.1`; `docs/DECISIONS.md` (D-023 updated),
  `docs/DEVELOPMENT.md`.
- Next: track 2 — lightweight UDP (udpgw-style framed datagrams over a second
  adb-forwarded TCP port). Phone re-test of this batch folds into that reinstall.

### 2026-08-30 — D-023: pick the phone's upstream (cellular/wifi/ethernet/auto)

- Completed: `teather upstream <auto|cellular|wifi|ethernet>` (also `SetUpstream`
  on D-Bus, a GUI dropdown, a `config.json` `upstream` key). The Android app
  already supported all four (`UpstreamPreference`); the Linux side stopped
  hard-coding `cellular` and now accepts a non-cellular relay. Switching while
  connected restarts **only** the Android relay binding — `manager.set_upstream`
  does `adb.stop_relay` + `adb.start_relay(serial, new)`; `teather0`, the tunnel,
  routes, DNS, and the ADB forward are untouched. Teather refuses to change a
  relay it did not start (`manual-relay`). Package bumped to `0.1.0-5`.
  Decision: D-023.
- Verified with: 48 host unit tests + D-Bus smoke; then live on the laptop with
  the phone (which had both Verizon cellular and the "Banyan Patients" Wi-Fi):
  `teather connect` → exit IP `203.0.113.10` (Verizon); `teather upstream
  wifi` → exit IP `198.51.100.20` (the AP), same `tun2proxy` PID, same ADB
  forward, `teather0` still UP, `/etc/resolv.conf` unchanged, Android reported
  `selected_upstream=wifi_(validated)`; `teather upstream cellular` → back to
  Verizon; `teather disconnect` → exact baseline.
- Files/areas changed: `android_status.py`, `config.py`, `adb` call sites in
  `manager.py` (+ `set_upstream`, status/diagnose fields), `dbus_service.py`,
  `cli.py`, `gui.py`, `tests/test_core.py`, `packaging/debian/{control,changelog}`,
  `packaging/scripts/build-deb.sh`, `docs/DECISIONS.md` (D-023).
- Milestone transition: not applicable; D-023 is transport selection on the
  existing TCP+virtual-DNS relay, so it is not gated by D-018's P2 stop.
- Punch list for the next APK build (not done, no APK change was needed for
  D-023): (a) update Android UI strings that imply TCP-only once P2 adds UDP;
  (b) replace the Android launcher icon with the Linux
  `desktop/linux/resources/icons/teather.svg` art — the owner prefers the Linux
  logo and wants them unified.
- Next exact action: unchanged — stop for the P2 design discussion (D-018).

### 2026-08-30 — D-022 live on the developer host; merged to main

- Completed: after the VM validation below, installed `0.1.0-4` on the actual
  developer laptop (Debian 12, NM 1.42.4, Wi-Fi `wlo1`) at the owner's request
  and ran it live. Host baseline snapshotted to `~/teather-host-evidence/`.
  `teather connect` (phone already approved from the 2026-08-27 run): connected
  with no polkit prompt, `/etc/resolv.conf` = `8.8.8.8` then `198.19.0.1` (Wi-Fi
  resolver first), Wi-Fi default (metric 600) still preferred over `teather0`
  (metric 32000), `teather0` never written to
  `/etc/NetworkManager/system-connections/`. `curl --interface teather0` exited
  at the phone's Verizon IP (`203.0.113.10`) vs `198.51.100.20` on Wi-Fi.
  Then `nmcli device disconnect wlo1` → within 3 s the whole machine (this
  Claude Code session included) was on cellular through Teather:
  `resolv.conf` = `198.19.0.1` only, default = `teather0`, real sites
  (`github.com`, `google`, `claude.ai`, `api.anthropic.com`) all reachable,
  6/6 and more probe requests OK, teatherd RSS steady ~29 MB. `nmcli device
  connect wlo1` + `teather disconnect` returned the host to exact baseline.
- Verified with: the above, plus `~/teather-host-evidence/{routes,resolv,nm}.
  {before,active}`. The D-022 branch merged fast-forward to `main` and pushed
  (`9ad8c0d`).
- Milestone transition: P1's core question is answered on real hardware. The
  owner will daily-drive `0.1.0-4`; sustained/live-data behaviour and carrier
  reclassification are that ongoing use, not a synthetic gate.
- Next exact action: **stop for the P2 design discussion (D-018)** before any
  general-UDP / IPv6 / broader-DNS / WireGuard / wireless-transport work. P2 =
  "Protocol Completeness": a documented UDP relay path, explicit IPv6 policy and
  tests, DNS A/AAAA behaviour, keepalive/backpressure, suspend/resume. Let real
  daily-use friction inform the P2 priorities.

### 2026-08-30 — D-022 validated end-to-end with the real phone (VM + USB passthrough)

- Completed: full P1 acceptance in the disposable Debian 12 GNOME VM with the
  owner's phone (Samsung `SM S266V`, Verizon LTE) passed through over USB
  (`-device qemu-xhci -device usb-host,vendorid=0x04e8,productid=0x6860`; the
  owner tapped "Allow USB debugging" once). Package `0.1.0-4` installed; the
  `systemd --user` unit runs.
- Verified with, all against `0.1.0-4` and the running `teatherd`:
  - `teather connect` end to end → `state: connected`, `dns_ready: true`,
    `failover_armed: true`. It started the Android relay, allocated the ADB
    forward (`tcp:45621 -> tcp:1080`), had NetworkManager create `teather0`,
    and spawned `tun2proxy --tun teather0` (unprivileged) — no polkit prompt.
  - Real traffic: `curl --interface teather0 https://cloudflare.com/cdn-cgi/trace`
    → HTTP 200, world-visible IP `203.0.113.10` (Verizon cellular), vs.
    `198.51.100.20` (host) via `eth0`. Traffic genuinely exits as the phone's
    own cellular app traffic; `warp=off`.
  - Additive DNS: with `eth0` up, `/etc/resolv.conf` = `10.0.2.3` then
    `198.19.0.1`; normal browsing used `eth0`.
  - Automatic failover: `nmcli device disconnect eth0` → within 3 s
    `resolv.conf` = `198.19.0.1` only, default route = `teather0` only,
    world-visible IP = the Verizon address. `getent hosts example.com` →
    `198.18.0.2`; `curl https://example.com` and `https://github.com` →
    HTTP 200 over cellular. Reconnecting `eth0` restored the physical
    resolver/route on top with Teather still connected.
  - `teather disconnect` → `resolv.conf`, routes, and `nmcli` back to exact
    baseline; ADB forward removed; Android relay stopped;
    `/etc/NetworkManager/system-connections/` empty; no runtime journal.
  - `kill -9` of `tun2proxy` → the daemon's 3 s health poll auto-disconnected
    (`error_category: tunnel-exited`), cleaning `teather0`, the forward, and
    the relay. `teather recover` idempotent.
  - Phone-free VM matrix (2026-08-29/30, from `teatherd`'s context): mechanism,
    additive DNS, dormant mode, `SIGKILL`+`recover()`, in-memory/teardown — all
    pass. 46 host unit tests + D-Bus smoke pass.
- Fixes made during validation:
  - `networkmanager.py`: `AddAndActivateConnection`/`…2` return `UnknownDevice`
    for a not-yet-existing tun, so switched to `AddConnection2` (in-memory
    flag) then `ActivateConnection`.
  - `manager._tunnel_command`: removed `--setup false` — `--setup` is a bare
    root-only flag; omitting it is correct.
  - `manager._system_interface_snapshot`: NetworkManager picks the metric for
    the scope-link `198.18.0.0/15` route, so the parity check pins only the
    backup default's metric.
  - `packaging/systemd/teather.service`: dropped `ProtectControlGroups` /
    `ProtectKernelModules` / `RestrictNamespaces` — they fail at step
    CAPABILITIES in a `systemd --user` unit. Kept `NoNewPrivileges=yes`,
    `ProtectSystem=strict`, `ProtectHome=read-only`, `RestrictSUIDSGID`,
    `LockPersonality`. Package rebuilt (sha256 `141d542a…`).
- Also verified (VM, no phone): `0.1.0-4` package lifecycle — same-version
  reinstall and `remove` preserve the mode-0600 `config.json`, `purge` removes
  it, reinstall works. `teather-gtk` renders against `0.1.0-4` with the
  "Automatic failover" checkbox (default on) and the tray indicator.
- Soak: the owner decided a synthetic two-hour run is not needed — real daily
  use will be the sustained/live-data validation. ~15 min connected over
  cellular showed flat RSS (teatherd ~25 MB, tun2proxy ~7.5 MB) and no errors,
  which covers the "doesn't leak / fall over" intent. P0 already ran a 30-min
  soak on the same Android relay code.
- Milestone transition: P1 acceptance is essentially complete; the repo-wide
  closeout (roadmap status, this file, README, E-002/E-003) is done in this and
  the same-day entries. Phone handed back (USB passthrough removed, host
  `adb start-server`).
- Risks or failures: `--setup false` and the over-hardened unit each cost one
  iteration; both fixed and re-verified. Reproducible-build verification of the
  `.deb` still needs Rust 1.90 on the host (not installed). Carrier
  reclassification over sustained tethering-like use is unmeasured and is an
  owner-daily-use / future-experiment question, not a P1 gate.
- Next exact action: commit the D-022 change set, then **stop for the P2 design
  discussion (D-018)** — no general UDP / IPv6 / broader-DNS / WireGuard work
  until that happens. If the owner wants to daily-drive `0.1.0-4` on the real
  host first, the useful prep is the standalone auto-revert path + installing
  the package there.

### 2026-08-29 — cut documentation ceremony

- Completed: the owner said the process/documentation ceremony was itself a
  source of friction. Removed the fresh-session reasoning-level gate, the
  same-thread reasoning transition gate, the 9-step milestone transition
  protocol, the mandatory 7-file "read in order and reconcile" pass, the
  change-completion checklist, and the session-closeout template from
  `AGENTS.md` and their echoes in `README.md`, `docs/PROJECT_STATUS.md`,
  `docs/P1_HANDOFF.md`, `docs/DEVELOPMENT.md`, `docs/ROADMAP.md`,
  `docs/DECISIONS.md`, and `CONTRIBUTING.md`. `AGENTS.md` is now ~110 lines
  (was 245): resume pointer, current priority, safety gates (phone + active
  host), hard constraints, engineering rules, testing, a one-paragraph
  "finishing a change" note.
- Kept unchanged: the hard constraints, the phone and active-host safety gates,
  engineering rules, testing expectations, and `docs/DECISIONS.md` as the
  rationale record (append, don't rewrite).
- Verified with: `make p1-check` (46 tests + D-Bus smoke), `git diff --check`,
  and a scan for dangling links to the removed sections (only dated work-log
  entries still name them, which is fine as history).
- Next exact action: unchanged — build `0.1.0-4` and run the disposable-VM
  Phase 2 matrix.

### 2026-08-29 — D-022 accepted and implemented (package `0.1.0-4`)

- Completed: the owner delegated the D-022 decision ("just do whatever … so long
  as whatever the app does doesn't cause the wifi to suddenly stop working while
  still on"). Accepted D-022 and implemented it in shipped source:
  - `desktop/linux/teather/networkmanager.py` rewritten from a `Reapply` DNS
    helper into `NetworkManagerConnection` — creates and owns an in-memory `tun` connection added in-memory then activated,
    with `tun.owner`/`tun.group` delegation, `ipv4` manual address + the two
    fixed routes, and additive DNS. `_verify_additive()` fails the connection
    closed if arming ever leaves the sentinel as the only resolver while a
    physical link is up — the exact "Wi-Fi stops working while still on" case
    the owner called out.
  - `DNS_PRIORITY` moved from `-32768` (exclusive) to `32050` (positive,
    non-exclusive); `ignore-auto-dns` is now `false`.
  - `desktop/linux/helper/teather-helper.c`, its route test,
    `packaging/polkit/…`, and `packaging/man/teather-helper.8` deleted.
    `tun2proxy` is spawned by `teatherd` as the desktop user with
    `--tun teather0`.
  - `packaging/systemd/teather.service` restores `NoNewPrivileges=yes` and adds
    `RestrictSUIDSGID`/`ProtectControlGroups`/`RestrictNamespaces`/
    `LockPersonality`; `packaging/debian/control` drops the `pkexec` dependency;
    package version `0.1.0-4`.
  - Auto-failover setting (`config.auto_failover()`, default on) with
    `SetAutoFailover` on D-Bus, `teather failover on|off`, and a GTK checkbox.
    Off = the connection is created dormant (no default route, no DNS) until
    armed, for metered upstreams.
  - `manager.py` connect/disconnect/recover/health_check rewritten around the
    new module; refusal checks stay in `preflight.py`, now run against
    `route show table all`.
- Verified with: `python3 -m unittest discover -s desktop/linux/tests` — 46
  tests pass (37 core + subtests); `./desktop/linux/tests/dbus_smoke.sh` passes;
  `git diff --check` clean. The Android/`gradle` half of `make check` was not
  re-run in this session (no source under `app/` changed).
- Files/areas changed: `desktop/linux/teather/{networkmanager,manager,config,
  constants,cli,gui,dbus_service}.py`, `desktop/linux/tests/test_core.py`,
  `Makefile`, `packaging/{systemd,debian,scripts,man}/…`, and the decision,
  architecture, threat-model, roadmap, test-plan, handoff, recovery,
  development, experiment, README, and this status documentation. Deleted the
  helper, its test, its polkit action, and its man page.
- Decisions made: D-022 Accepted (supersedes D-021's mechanism, D-020, and
  D-014's manual-only model). The privilege trade-off was resolved in favour of
  NetworkManager-native ownership: `teatherd` runs unprivileged and holds only
  `network-control`/`settings.modify.own` (which an active session already
  has), replacing a 350-line setuid-root C helper that Phase 2 found three
  parsing defects in.
- Milestone transition: not applicable. P1 remains active; E-002/E-003
  incomplete.
- Risks or failures: the real-NetworkManager path is unproven — no polkit
  prompt for an active session, `tun2proxy --tun teather0`
  attaching to a `tun.owner` device unprivileged, in-memory teardown, and
  `SIGKILL`-then-`recover()` all need the disposable-VM matrix. `tun2proxy`
  0.8.3's exact `--tun NAME` / no-`--setup` behaviour on an NM-created
  device is the single largest unknown.
- Next exact action: build `teather_0.1.0-4_amd64.deb` (two byte-identical
  builds) and run the Phase 2 matrix in `docs/P1_HANDOFF.md` from the
  disposable VM's active GNOME session. Do not reconnect the phone or attempt
  physical Phase 3 until it passes.

### 2026-08-29 — generalize the fresh-session gate beyond Codex

- Completed: the owner pointed out that the first-prompt gate assumed the
  assistant was Codex with a selectable Ultra/High reasoning level, which is not
  true for every assistant (Claude Code, for example, exposes no such selector).
  Rewrote the gate to be assistant-agnostic: the durable mechanic is now a
  **broad scope** vs **focused scope** classification of the requested work, and
  the Codex "GPT-5.6 Sol with Ultra/High" selector is documented as one mapping
  of that classification rather than the classification itself. An assistant
  without reasoning selectors states the classification and its consequences
  (broad-scope work moves to Codex at Ultra or is divided into independently
  reviewable units) instead of naming a selector. The read-only first pass,
  stop-and-wait-for-owner step, and same-thread transition gate are unchanged in
  intent.
- Verified with: `grep` for residual `fresh-codex-session-gate` anchors and
  Codex-only selector language in live (non-historical) sections; `git diff
  --check`; local Markdown link inventory for the renamed
  `#fresh-session-gate` anchor.
- Files/areas changed: `AGENTS.md` (gate rename `Fresh Codex session gate` ->
  `Fresh session gate`, both gate sections rewritten), `README.md`,
  `docs/PROJECT_STATUS.md` (this entry and the top blockquote),
  `docs/P1_HANDOFF.md`, `docs/DEVELOPMENT.md`. Historical work-log entries and
  `docs/P0_HANDOFF.md` were left as written; they are dated records, not live
  instructions.
- Decisions made: none new. This is a workflow-wording change, not an
  architectural or technical decision, so it follows the 2026-08-28 gate entry's
  precedent of a work-log note rather than a `docs/DECISIONS.md` entry. D-015
  through D-021 remain authoritative; D-022 remains Proposed.
- Milestone transition: not applicable. P1 remains active.
- Risks or failures: none observed. No code, build, network, VM, device, or
  Android/Linux runtime state was touched.
- Next exact action: unchanged from the entry below — the owner decides whether
  to accept D-022's privilege trade-off (broader NetworkManager permission scope
  vs. the current narrower single-purpose polkit action). If accepted, design the
  full replacement (routes beyond the base address, refusal/collision checks, the
  automatic-failover toggle setting) before writing shipped code, then rerun the
  disposable-VM matrix. Do not reconnect the phone or attempt physical Phase 3
  until the VM DNS gate passes with the chosen mechanism.

### 2026-08-29 — D-021 DNS mechanism found broken at the root; D-022 proposed and prototyped

- Completed: resumed the phone-free disposable-VM D-021 matrix from the
  guest's real active GNOME session (not SSH), as the prior session's next
  action required. Found and fixed two environment problems first: the
  launcher used `-accel tcg`, under which GNOME Shell segfaulted on an AVX2
  instruction roughly every 15-25 seconds (a QEMU TCG bug, not a broken VM
  image); switching to `-accel kvm -cpu host` fixed it completely
  (`/dev/kvm` is available on this host, contrary to the stale 2026-08-26
  note). Separately confirmed `auth_admin_keep` polkit authorizations expire
  after a few minutes and need a fresh graphical prompt each time.
- Verified with: `loginctl show-session` confirming `Type=x11 Remote=no
  Active=yes`; NetworkManager's own audit log recording
  `op="device-reapply" ... result="success"` from that session (the original
  SSH/remote gate is genuinely resolved); a step-by-step manual reproduction
  (bypassing the 5-second auto-cleanup) showing `Reapply()` accepts the DNS
  sentinel settings without error but `/etc/resolv.conf` never reflects them,
  even held for 25 seconds, and a manual `Reload(DNS)` afterward does not fix
  it either. Root-caused to `teather0` being a NetworkManager
  *externally-assumed* connection, a code path NM does not fully support for
  DNS regeneration; reproduced identically under both TCG and KVM, ruling out
  timing.
- Decisions made: D-022 (Proposed) documents this finding and proposes
  replacing D-021's Reapply-based mechanism with NetworkManager-native `tun`
  connection ownership (NM creates and owns the interface from the start
  instead of discovering it after the fact). Prototyped end-to-end via
  `nmcli` from the active session: DNS came up as *only* the sentinel, an
  unprivileged process successfully attached to the owner-delegated
  persistent TUN device, the connection was never persisted to disk, and
  teardown left the host byte-for-byte at baseline. This is a real
  architectural trade (D-022's broader NetworkManager-mediated permission
  model vs. D-021/D-015's narrower single-purpose custom polkit action), not
  a drop-in fix, and needs explicit owner acceptance before implementation.
- Files/areas changed: `docs/DECISIONS.md` (D-022), `docs/EXPERIMENTS.md`
  (E-002 addendum), this status entry. No shipped source was changed. The
  pre-D-022 working tree is preserved unmodified on branch
  `archive/d021-reapply-dns-approach` (commit `c78d45f`) specifically so
  D-021's implementation remains recoverable regardless of what happens next
  — nothing was deleted, only superseded.
- Milestone transition: not applicable; P1 remains active. D-022 is
  Proposed, not Accepted.
- Risks or failures: D-022's route configuration beyond the base address,
  collision/refusal checks equivalent to the current helper's validation
  matrix, and the actual privileged-helper shrink are not yet designed or
  implemented — only the core DNS/ownership hypothesis was validated.
- Next exact action: the owner decides whether to accept D-022's trade-off
  (broader NetworkManager permission scope vs. a working DNS mechanism). If
  accepted, design the full replacement (routes, refusal conditions, reduced
  helper) before writing shipped code. If rejected, D-021 remains the active
  approach and the assumed-connection DNS gap needs a different fix. Either
  way, do not reconnect the phone or attempt physical Phase 3 until the VM
  DNS gate actually passes with whichever mechanism is chosen.

### 2026-08-28 — D-021 audit hardened; first fresh VM attempt stopped at session authorization

- Completed: rebased the implementation onto the owner's five reasoning-gate
  documentation commits; reconciled stale resume points; hardened exact resolver,
  route, cleanup-error, dependency, and failure-path checks; built reproducibly;
  installed package `0.1.0-3` in a fresh disposable overlay; and confirmed API 2.
- Verified with: 37 Python tests, strict helper/D-Bus checks, the full 92-task
  Android/Linux `make check`, two identical tunnel builds at
  `9ad64db8987a7035ab86edae99417506e5cc931bb876cd7736e9ba148f470146`,
  two identical package builds at
  `f3aa412bf64c3131eeb8f671161392164f5f72df04e404cb9c34cee7dea769d9`,
  guest NetworkManager 1.42.4, installed API 2, post-denial core cleanup, clean
  guest poweroff, and a clean QCOW check.
- Files/areas changed: DNS manager/adapter/preflight tests and package dependency;
  architecture, decisions, development, experiments, handoff, test, README,
  project-status, and agent resume documentation.
- Decisions made: an SSH process is a remote PolicyKit subject, so its
  `network-control` denial is not accepted as the active GNOME product result.
  Do not add a wildcard/passwordless rule; rerun through the real desktop and
  packaged `pkexec` path.
- Milestone transition: not applicable. P1 remains active.
- Risks or failures: two `apt-get --no-download` local-file attempts failed before
  unpack because Debian reduced the pathname to a non-absolute basename; offline
  `dpkg -i` succeeded. The eight-case DNS matrix did not advance past `normal`.
  Private evidence remains only in the powered-off disposable overlay.
- Next exact action: with no phone, use a fresh disposable overlay and run the
  D-021 matrix from the active GNOME session through product authorization. Only
  after it passes may the operator phone gate open.

### 2026-08-28 — add fresh-session Codex reasoning gate

- Completed: documented a mandatory first-prompt, read-only reasoning-level gate
  plus a symmetric same-thread High-to-Ultra or Ultra-to-High transition gate
  across the agent instructions, README, current P1 handoff, development guide,
  and canonical resume point.
- Verified with: exact cross-document references and scope rules distinguish
  GPT-5.6 Sol with Ultra for separable repository-wide or cross-subsystem work
  from High for focused work with an accepted design and bounded verification.
- Files/areas changed: AGENTS.md, README.md, docs/PROJECT_STATUS.md,
  docs/P1_HANDOFF.md, and docs/DEVELOPMENT.md.
- Decisions made: the then-current P1 DNS design review was classified as Ultra;
  the gate now classifies D-021's multi-part VM validation as Ultra and requires
  another reassessment before physical validation.
  The gate selects execution mode only and does not authorize implementation, device
  use, network mutation, or bypass of another approval stop.
- Milestone transition: not applicable. P1 remains active.
- Risks or failures: Codex may not be able to observe its active selector setting,
  so it must recommend the level and wait for owner confirmation rather than
  assert that the setting is active.
- Next exact action: in a new Codex conversation, run the fresh-session gate; once
  the owner confirms Ultra and prompts again, continue the disposable-VM D-021
  matrix without reconnecting the phone or changing active-host resolver state.

### 2026-08-27 — D-021 DNS implementation; paused before VM validation

- Completed: implemented temporary NetworkManager active-device DNS with the
  preserve-external-IP flag, reserved sentinel/pool separation, UDP/TCP readiness,
  cleanup/recovery, API-v2 diagnostics, pinned TCP-DNS tunnel patch, checked-in
  verified Cargo lock, and Debian package `0.1.0-3`.
- Verified with: 37 Python tests, strict helper checks, host-session D-Bus smoke,
  two Rust TCP-DNS tests, read-only real NetworkManager 1.42.4 API access, the
  92-task Android build/lint/unit matrix, two byte-identical clean tunnel builds,
  and two byte-identical same-source package builds.
- Milestone transition: not applicable; P1 remains active.
- Risks or failures: the sandbox-only D-Bus smoke cannot reach the host user bus;
  the required host-session rerun passed. Fresh lock generation changed with the
  registry index, so the previously verified checksum-matching lock is now a
  checked-in build input. Real NetworkManager mutation/cleanup is not yet tested.
- Next exact action: keep the phone disconnected; run the fresh disposable-VM
  DNS matrix, then request the phone explicitly.

### 2026-08-27 — physical P1 stopped at DNS gate; cleanup passed

- Completed: validated the phone's installed Teather APK byte-for-byte against
  the verified debug build; confirmed the old Android package and temporary
  permission probe are absent; installed Debian package `0.1.0-1`; captured a
  private host baseline; exercised Android ADB shell control and local hashed-
  device approval; corrected the discovered PolicyKit launch conflict as package
  `0.1.0-2`; connected the bounded tunnel; and ran the owner-controlled Wi-Fi/DNS
  gate. The phone may now be disconnected.
- Verified with: `env ANDROID_HOME=/tmp/android-sdk
  GRADLE_USER_HOME=/tmp/teather-gradle2 make check` passed 92 Android tasks, 25
  Python tests, strict helper/route checks, and D-Bus smoke. The installed APK
  and build both hash to
  `8dbf92b8137533127e1a7e20e199586ccb276e995cb58ad354e8ed968a9ed586`
  and share the recorded debug certificate. Two clean `0.1.0-2` package builds
  were byte-identical at SHA-256
  `77b70295a838daf5a85e0ba4a7e33a1f7109b0f049bee4775cb323a00f880804`.
  The installed unit reports `NoNewPrivileges=no`, `ProtectSystem=strict`, and
  `ProtectHome=read-only`. While active, `teather0` had only `192.0.2.1/32`,
  `198.18.0.0/15`, and the metric-32000 default; the metric-600 physical default
  remained selected. `tun2proxy` ran as the desktop UID/GID with no supplementary
  groups or capabilities and `NoNewPrivs: 1`.
- Physical result: disabling Wi-Fi removed the only usable non-loopback IPv4
  nameserver. Teather reported `resolver-unavailable` and disconnected. The
  owner's OpenAI session lost connectivity until Wi-Fi was restored, so the
  required browser/Git/SSH/package/two-hour gates were not attempted.
- Cleanup: the blocked first `pkexec` attempt and the later resolver failure both
  left no unexpected state. Final Android relay, ADB forward, `teather0`, helper/
  tunnel processes, ownership journal, and NetworkManager runtime entry were
  absent. Routes, IPv4 rules, resolver, and NetworkManager inventory exactly
  matched baseline. nftables structure matched after normalizing ordinary live
  packet/byte counters; no rule changed. Private evidence remains under `/tmp`
  and must not be committed.
- Files/areas changed: systemd user unit, Debian revision/changelog/build metadata,
  Linux regression test, agent/README/resume/handoff/roadmap, architecture,
  decisions, threat model, and E-002/E-003 evidence.
- Decisions made: D-020 records why the user daemon cannot set
  `NoNewPrivileges=yes` while invoking setuid-root `pkexec`; remaining service
  hardening and the helper/tunnel privilege drop remain required.
- Milestone transition: not applicable. P1 remains active; E-002 failed and E-003
  is incomplete.
- Risks or failures: the current P1 DNS design is unsupported on this host.
  General UDP, IPv6, or an unreviewed persistent resolver change is not an
  authorized workaround.
- Next exact action: owner-reviewed DNS design discussion and explicit approval.
  Do not reconnect the phone or rerun Phase 3 first.

### 2026-08-27 — debug signing accepted for private P1 testing

- Completed: published the P1 implementation and disposable-VM validation
  checkpoint to `origin/main` at commit `5a6f6b2`. Confirmed the local and remote
  main refs match and the VM remains stopped. Audited the next release-signing
  gate without connecting or querying the phone.
- Verified with: the build configuration reports versionCode 2 /
  `0.1.0-p1`; `app/build/outputs/apk/release/app-release-unsigned.apk` exists and
  `apksigner verify --verbose --print-certs` reports `DOES NOT VERIFY`, as expected
  for the unsigned output. No `jks`, `keystore`, `p12`, or `pfx` file exists in
  the repository, and no signing-related environment variable is configured.
  After D-019, `env ANDROID_HOME=/tmp/android-sdk
  GRADLE_USER_HOME=/tmp/teather-gradle2 make android-build` passed outside the
  network sandbox. `apksigner verify --verbose --print-certs` validates one v2
  Android Debug signer; `aapt dump badging` confirms package
  `io.github.vel71184.teather`, versionCode 2, and versionName `0.1.0-p1`. The APK
  signer certificate SHA-256 is
  `873c84175e4447884ab80929e6a40952ef1d31ee807624041abd7796c61d5ccb`;
  the APK SHA-256 is
  `8dbf92b8137533127e1a7e20e199586ccb276e995cb58ad354e8ed968a9ed586`.
- Files/areas changed: `.gitignore` now excludes `*.jks` and `*.keystore`; the
  resume, roadmap, handoff, experiment log, README, and agent starting point now
  distinguish private debug testing from future release signing.
- Decisions made: D-019 accepts Gradle's automatically signed debug APK for the
  private P1 experiment and defers a permanent release identity until distribution
  is being considered.
- Milestone transition: not applicable; P1 remains active.
- Risks or failures: a future release certificate cannot update the debug-signed
  installation. Moving to a release identity will require uninstall/reinstall and
  may discard local application state. The owner accepts that development-stage
  tradeoff.
- Next exact action: **superseded by the physical-run entry above later on
  2026-08-27**. The current action is DNS design review, not phone reconnection.

### 2026-08-26 — disposable VM Phase 2 passed and powered off

- Completed: ran the real privileged helper and patched tun2proxy in the
  phone-free Debian 12.15 QEMU guest against a controlled loopback SOCKS/HTTP
  service. Virtual DNS returned a synthetic pool address, then the controlled TCP
  request arrived at SOCKS as the original domain and passed. Exercised interface
  lifetime, physical-route preference, privilege drop, preflight refusals,
  signal/death cleanup, repeated control calls, and ambiguous-state preservation.
- Verified with: `env ANDROID_HOME=/tmp/android-sdk
  GRADLE_USER_HOME=/tmp/teather-gradle2 make check` passed 92 Android tasks,
  24 Python tests, the strict C build, the new helper-route regression
  executable, argument rejection, and private D-Bus smoke. The current tun2proxy is
  `ffdd4373cb41401e3f4e8b4d65f84688ed4288966d621580de303b1ca47d15bf`;
  the installed package is
  `f723c2ebfe92d68cb18959bdfe414e997dded22c20150d1793d07d9bc8cedc52`.
  The final matrix printed `PHASE2_MATRIX_PASS`. Baseline/final routes, rules,
  resolver, NetworkManager inventory, and nftables were identical; `teather0`
  and tun2proxy were absent before clean poweroff.
- Files/areas changed: helper route/rule parsing and regression test; a second
  audited tun2proxy patch; build integration; architecture/decision/evidence/
  status documentation.
- Decisions made: preserve D-015's `IFF_NO_PI` boundary and patch tun2proxy 0.8.3
  to honor its existing packet-information argument.
- Milestone transition: not applicable; P1 remains active until physical
  acceptance passes.
- Risks or failures: the matrix found three helper parsing defects and one
  tun2proxy packet-framing mismatch. All failed closed except the incorrect
  split-default comparison, which started only the disposable-VM tunnel; the
  exact owned process was terminated and the harness restored its test state.
  Regression tests and the final matrix now pass. Physical DNS retention,
  physical APK/ADB behavior, two-hour behavior, and cable/service recovery remain
  unproven. Permanent release signing is deferred by D-019.
- Next exact action: **superseded by D-019 on 2026-08-27**. Verify the debug APK,
  then request explicit phone connection and run Phase 3.

### 2026-08-26 — Phase 2 guest ready; paused at guest sudo authorization

- Completed: the owner explicitly confirmed the phone was disconnected. Verified
  that no QEMU guest was running, checked the fresh Phase 2 overlay and complete
  backing chain with `qemu-img check`/`qemu-img info`, and booted a dedicated
  Phase 2 launcher that references `phase2.qcow2` rather than the accepted Phase
  1 disk. The VM has no USB passthrough. Staged and syntax-checked a private
  controlled loopback SOCKS/HTTP service, virtual-DNS/TCP probe, and reversible
  privileged matrix in the guest.
- Verified with: the guest reports `systemctl is-system-running` as `running`,
  `eth0` is up on QEMU user networking, the physical default has metric 100,
  IPv4 policy rules are the three standard rules, `teather0` is absent, and the
  installed helper/tunnel are root-owned mode 0755.
- Files/areas changed: this resume point only; private harness and evidence paths
  remain under `/tmp` and the guest home, outside the repository.
- Decisions made: continue phone-free with a controlled loopback SOCKS endpoint.
  Do not weaken sudo or add a passwordless rule.
- Milestone transition: not applicable; P1 remains active.
- Risks or failures: the first guest privilege probe, `sudo -n true`, correctly
  stopped with `sudo: a password is required`. Repository rules prohibit the
  agent from retrying sudo after that failure.
- Next exact action: from the host, the owner runs the exact SSH command supplied
  in chat, enters the disposable guest password at the sudo prompt, and returns
  the complete matrix output. Keep the phone disconnected. **Resolved later the
  same day:** the owner explicitly authorized Codex to enter the disposable guest
  password; the corrected matrix passed and the VM powered off.

### 2026-08-26 — disposable VM Phase 1 passed

- Completed: booted the Debian 12.15 amd64 GNOME guest under QEMU TCG with
  loopback-only SSH forwarding. Corrected two guest-bootstrap omissions before
  accepting evidence: NetworkManager took ownership of the QEMU NIC after the
  no-recommends build omitted a DHCP client, and the standard Xorg stack was
  installed after GDM accurately reported that it could not start an X server.
  Restored Debian's normal APT recommendation behavior. Installed and verified
  the Teather package, no-phone D-Bus/CLI behavior, optional watcher, real GNOME
  GTK window, AppIndicator-positive and typelib-unavailable fallback cases, and
  same-version reinstall/remove/purge/final-reinstall lifecycle.
- Verified with: the package matched SHA-256
  `621b8732459e4ab3108e12eed567c6ea00a81f81866a8611b810ac67b086c6e3`.
  `teather status --json`, `devices --json`, and `diagnose --json` reported a
  ready disconnected state, no devices, no mutations, and one usable resolver;
  D-Bus activation started the user daemon without privilege or `teather0`.
  Watcher enable/active/disable/inactive passed. Privileged files were root-owned
  at modes 0755, 0755, and 0644. The GTK window remained usable and disconnected
  with zero counters; the tray icon appeared with AppIndicator enabled and was
  absent when the exact typelib was temporarily mode 000. The typelib was
  restored to 0644 and neither GUI case started `pkexec`.
- Package lifecycle: the mode-0600 preference file retained SHA-256
  `ee03aa4e566e50876c666e8343b64ea56d234a0650d4ecb678b087c678cf0a19`
  across same-version reinstall and remove. Remove deleted installed program
  files; purge deleted only the Teather preference directory and package record;
  private evidence remained. The verified artifact was reinstalled afterward.
- No-mutation evidence: routes, IPv4 rules, resolver content, NetworkManager
  connection inventory, and nftables ruleset were byte-for-byte unchanged from
  the private pre-install baseline. `teather0` never existed. No host network,
  ADB, USB passthrough, or phone command was used.
- Artifacts: private screenshots remain outside the repository at
  `/tmp/teather-p1-vm/gui-tray.png` and `gui-fallback.png`, with SHA-256
  `8c2067855bc3b9e40a11b67a7f4e6761bb0f98c332104b509ad24b992f382116`
  and `270acc39d849e6bba6081d270300aed457d518cdfbf6b0ede09fbe7a87b48123`.
  Guest state was powered off cleanly; `qemu-img check` found no errors. The
  completed Phase 1 overlay is now the immutable backing file for a fresh
  mode-0600 `/tmp/teather-p1-vm/phase2.qcow2` overlay.
- Milestone transition: not applicable; P1 remains active.
- Risks or failures: the guest bootstrap corrections are validation-environment
  setup, not product passes. `/tmp` remains volatile. The privileged helper/TUN
  matrix and all physical device evidence remain open. The owner
  connected the phone early; Codex did not query it or pass USB through and asked
  for it to be disconnected. Confirmation of disconnection is pending.
- Next exact action: after the owner confirms the phone is disconnected, boot
  `phase2.qcow2` with no USB passthrough and run the controlled loopback SOCKS
  Phase 2 matrix in `docs/P1_HANDOFF.md`.

### 2026-08-26 — paused after disposable VM image construction

- Completed: the owner installed QEMU 7.2 and its required utilities. Direct
  downloads from Debian's cloud-image backing mirrors repeatedly reset, so the
  guest was assembled instead with `mmdebstrap` in an unprivileged user namespace
  from Debian's signed Bookworm, Bookworm updates, and Bookworm security package
  repositories. The guest contains Debian 12, GNOME, systemd, NetworkManager,
  SSH, sudo without a passwordless rule, a normal test user, the P1 documents,
  and the verified Teather package. A 16 GiB ext4 filesystem was converted to a
  private QCOW2 base plus a disposable Phase 1 overlay.
- Verified with: `e2fsck -fn` passed all five filesystem passes with 83,000 files
  and no reported errors. The package copied into the guest matches SHA-256
  `621b8732459e4ab3108e12eed567c6ea00a81f81866a8611b810ac67b086c6e3`.
  `qemu-img info --backing-chain` reports a non-corrupt 16 GiB overlay backed by
  the non-corrupt 16 GiB base; the base occupies about 2.19 GiB and the new
  overlay about 196 KiB.
- Files/areas changed: private transient VM assets are under
  `/tmp/teather-p1-vm`; non-secret rootfs staging is under
  `/tmp/teather-p1-build`. The repository change in this sub-session is limited
  to the explicit phone gate in `docs/P1_HANDOFF.md` and this status checkpoint.
- Decisions made: build the same Debian 12 GNOME validation environment from
  signed Debian packages rather than weaken verification or trust an arbitrary
  cloud-image mirror. QEMU will use TCG software CPU emulation, user-mode
  networking, and an SSH forward bound only to `127.0.0.1:2222`; `/dev/kvm` and
  host TUN are unavailable.
- Operator gate: the phone remains disconnected. Before any phone connection or
  USB passthrough, stop, explain why it is needed and the required VM state, and
  wait for the owner to confirm connection. This gate is also durable in
  `docs/P1_HANDOFF.md`.
- Pause state: the headless launch tool call was canceled before completion. No
  QEMU PID file, monitor socket, serial log, or running VM remained afterward.
  No package was installed in the VM and no P1 test command was run yet. No host
  TUN, route, resolver, NetworkManager, firewall, policy-rule, interface, ADB, or
  phone state changed.
- Next exact action: if `/tmp/teather-p1-vm/phase1.qcow2` still exists, run
  `/tmp/teather-p1-vm/start-headless.sh`, wait for SSH on host loopback port 2222,
  verify the guest baseline, and begin Phase 1 of `docs/P1_HANDOFF.md`. If `/tmp`
  was cleared, reconstruct the disposable image from this recorded design. Do
  not connect the phone.

### 2026-08-26 — milestone transition protocol and VM prerequisite check

- Completed: added a mandatory repository-wide milestone transition protocol to
  `AGENTS.md` and linked it from this session-closeout workflow. Every completed
  P# must now advance the roadmap, experiments, canonical status, agent priority,
  README, next handoff/recovery documents, and affected technical guidance before
  the following milestone begins.
- Verified with: local tool discovery and host inspection. The host is Debian 12
  with KVM modules loaded, but `/dev/kvm` is unavailable; no QEMU/Boxes/libvirt
  launcher or existing VM image is installed. LXC is present but was not used
  because the accepted gate calls for a disposable GNOME VM and host networking
  must remain untouched.
- Files/areas changed: `AGENTS.md` and this canonical status. No application,
  package, phone, TUN, route, resolver, NetworkManager, policy-rule, firewall, or
  interface state changed.
- Decisions made: use QEMU user-mode networking for the disposable VM so setup
  does not add a host bridge or change host routes. This is a validation-environment
  choice, not a product architecture decision. The owner added an explicit
  operator gate: stop and request confirmation before any phone connection or USB
  passthrough; do not silently advance from VM-only validation to phone work.
- Risks or failures: QEMU and cloud-image tools are not installed. The first sudo
  attempt stopped at the password prompt and ended with `sudo: a password is
  required`; repository instructions prohibit retrying sudo from this session.
  The phone is not needed for VM Phase 1.
- Next exact action: the owner runs `sudo apt-get update && sudo apt-get install -y
  qemu-system-x86 qemu-utils cloud-image-utils` locally and provides the complete
  output. Then resume Phase 1 of `docs/P1_HANDOFF.md` without connecting the phone.

### 2026-08-26 — interrupted-session audit and P1 handoff reconciliation

- Completed: reviewed the complete repository documentation, shipped man pages,
  package metadata, and the prior Codex session log. The log confirms the P1 run
  completed its final phone cleanup and successfully wrote the durable status
  checkpoint immediately before the usage limit prevented a user-facing handoff.
  Reconciled stale P0 priority, release-service, resolver, development, and test
  guidance; added `docs/P1_HANDOFF.md` as the current disposable-VM and physical
  acceptance contract.
- Verified with: `git diff --check`; local Markdown link inventory; and
  `make p1-check` outside the sandbox, which passed 24 Linux tests, strict helper
  compilation/argument rejection, and the private D-Bus daemon/CLI smoke test.
  The same D-Bus smoke failed inside the sandbox because it could not reach the
  user-session bus; the permitted host-only rerun passed.
- Files/areas changed: agent resume instructions, README documentation map,
  project/development/architecture/threat/test/roadmap/P0 handoff guidance, and
  the new P1 validation handoff. No application, helper, package, phone, TUN,
  route, resolver, NetworkManager, policy-rule, firewall, or interface state was
  changed during this audit.
- Decisions made: none. D-015 through D-018 remain authoritative.
- Risks or failures: the P1 implementation remains uncommitted. The disposable-VM
  TUN/helper/GUI/package gate, APK/device run, and full physical
  TCP/DNS/cleanup/two-hour acceptance remain open. D-019 later selected debug
  signing for that private device run. Generated Python
  bytecode is present in the worktree and must not be staged.
- Next exact action: follow Phase 1 of `docs/P1_HANDOFF.md` in a disposable Debian
  12 GNOME amd64 VM. Do not rerun P0 or mutate the active host network.

### 2026-08-25 — P1 implementation checkpoint

- Completed: approved P1 documentation and milestone names; Android version bump,
  DUMP-protected release control, idempotent attach policy, and schema-v1 status;
  Linux secure device trust/journal, manager state machine, D-Bus API, CLI,
  GTK/tray fallback, fixed polkit helper, recovery guide, Debian packaging, and
  pinned tun2proxy source/lock/patch build inputs. Host safety hardening covers
  full relay-setting compatibility, standard-only IPv4 policy routing, overlapping
  virtual-DNS routes, IPv4 resolver validation, uncertain Android-start ownership,
  and journal retention whenever cleanup cannot be proved.
- Verified with: `env ANDROID_HOME=/tmp/android-sdk
  GRADLE_USER_HOME=/tmp/teather-gradle2 make check`, which passed Android JVM
  tests, lint, debug/release assembly, 24 Linux unit tests, strict C compilation,
  helper argument rejection, and an isolated private D-Bus daemon/CLI smoke test.
  Two clean patched tun2proxy builds were byte-identical at SHA-256
  `19003e9c9bc61086ed30b3d4ac39c6432b61766a2ae407d8dfcfcfd71618b05d`.
  Two final `.deb` builds were byte-identical at SHA-256
  `621b8732459e4ab3108e12eed567c6ea00a81f81866a8611b810ac67b086c6e3`;
  lintian reports only its conventional initial-upload warning and a Rust
  fortification informational tag. Root-mapped namespace `dpkg` tests passed
  unpack, synthetic upgrade, remove, and purge while proving preferences survive
  remove/upgrade and disappear on purge.
- Physical Android control evidence: the connected phone was upgraded in place
  from P0 to the P1 debug-signed build and reported versionCode 2 / 0.1.0-p1.
  ADB shell started and dumped the DUMP-protected schema-v1 relay; cellular was
  available and validated. A coarse accepted-client counter survived a compatible
  attach, and an incompatible Wi-Fi request left the cellular relay/counter intact
  while reporting `incompatible-configuration`. A separately signed temporary
  ordinary-app probe lacked effective access: its start API returned on this
  Samsung build, but Android did not create the protected service. The probe was
  uninstalled. Final phone state is P1 debug installed, relay stopped, and zero
  ADB forwards. No Linux route, rule, resolver, firewall, or interface was changed.
- Files/areas changed: Android manifest/runtime/status/tests and version metadata;
  `desktop/linux`; `packaging`; `third_party/tun2proxy`; README and P1 documents.
- Decisions made: D-015 through D-018 record the approved P1 architecture and P2
  stop. The upstream 0.8.3 archive omits `Cargo.lock`, so the generated graph is
  checksum-pinned before the locked build. Rust 1.90 is needed by that graph.
- Risks or failures: this sandbox cannot create `/dev/net/tun` or display GTK.
  The root/helper interface lifetime and privilege-drop gate, dependency-configured
  Debian 12 install, GUI/tray and optional watcher tests, physical APK/device run,
  and full TCP/DNS/cleanup/two-hour P1 acceptance remain open. D-019 later selected
  debug signing for the private device run. The
  ordinary probe established that the service was not created, but its start API
  did not synchronously throw `SecurityException`; retain that platform nuance in
  final acceptance evidence.
- Next exact action: take `build/p1/teather_0.1.0-1_amd64.deb` into a disposable
  Debian 12 GNOME VM and run the namespace/helper, package-lifecycle, GUI/tray,
  and watcher gates in `docs/TEST_PLAN.md`. Only after those host-isolated gates
  pass should the physical Android acceptance sequence begin. Stop for explicit
  P2 design approval after P1 acceptance.

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
