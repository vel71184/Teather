# Project status

- **Snapshot date:** 2026-09-03
- **Lifecycle:** implementation / pre-alpha
- **Active milestone:** P1 — Linux USB Desktop. **Complete and daily-driven.**
  D-022 (NetworkManager owns `teather0`, additive DNS, automatic failover) is
  validated end-to-end and running live on the developer host. The owner then
  directed a focused post-P1 track — not the full P2/P4 sequence — which
  discharged D-018. IPv6 and the broader "become a VPN" scope stay deferred.
  The core aim: cellular traffic through Teather must not be classified as
  tethered. P3 wireless is **deprioritised** (does not serve that aim).
- **Committed 2026-08-31** (`071e2cc` + docs `36f4286`), all deployed and
  live-tested:
  - **D-023** (`0.1.0-5..7`) — `teather upstream auto|cellular|wifi|ethernet`,
    zero-gap via `ACTION_RECONFIGURE`.
  - **D-024** (`0.1.0-6..8`) — general UDP over tun2proxy's `udpgw` stream, a
    phone-side `UdpGatewayServer`. Shadow PC cloud gaming works (`0.1.0-8`).
  - **D-025** (`0.1.0-9`) — Teather comes up as the *only* internet path when
    armed and no other link exists.
  - **D-026** (`0.1.0-11`) — abnormal-disconnect self-heal + auto-reconnect,
    persistent `teatherd.log`, self-clearing toast notifications,
    single-instance GTK, sole-path tracking. Fault-injection tested 2026-08-31
    (daemon restart, tun2proxy kill, `adb kill-server`, unplug/replug, Wi-Fi
    toggle, GUI). Phone-reboot case deferred.
- **D-028** (`0.1.0-12` / Android `0.1.0-p1.3`, 2026-09-01) — the SOCKS relay
  now requires RFC 1929 username/password auth with a per-run 128-bit secret the
  phone publishes only in its `DUMP`-protected status. Closes the "any app on
  the phone can use the loopback relay" gap the threat model had flagged as
  not-releasable. Status schema → 2. Also hardened the udpgw address parser.
  From a whole-tree security review — the only finding above defense-in-depth.
- **D-029** (`0.1.0-12`, 2026-09-01) — the `.deb` bundles the matching APK;
  `teather device install` installs/upgrades it on the phone so the two halves
  stay on the same schema. Android app has a "Get the desktop client" button
  linking to the releases page.
- **D-030** (2026-09-01) — release signing done (supersedes D-019). The owner's
  key lives at `~/.teather/teather-release.jks` (password in KeePass);
  `keystore.properties` and `TEATHER_KEYSTORE*` configure it, with a debug
  fallback for CI/contributors. The pilot phone's one-time debug→release
  uninstall/reinstall is complete; the app and bundled APK are `CN=Teather`.
- **`0.1.0-13`** (2026-09-03) — self-heal wedge fix. A failed auto-connect
  latched the raw error category (`dns-residue`) instead of `recovery-pending`,
  which the poll-loop reconcile did not recognise, so the daemon stayed stuck in
  `error` after a reboot with a stale DNS sentinel — no automatic recovery until
  a manual restart. Reconcile now self-heals on any error state, and `recover()`
  clears an orphaned sentinel via a NetworkManager DNS reload. Also: the GTK
  window now carries the Teather icon in the Wayland/X11 switcher. See the
  2026-09-03 worklog entry.
- **`0.1.0-14`–`0.1.0-17` / Android `0.1.0-p1.4`–`0.1.0-p1.5`** (2026-09-03) —
  an Appearance setting (Follow system / Light / Dark) on both halves
  (`0.1.0-14` / `p1.4`); a state-driven "Phone app" install/update button in
  the GTK client (`0.1.0-15`); the D-031 security-version layer with a
  security-update prompt (`0.1.0-16` / `p1.5`, `versionCode 7`); and the GTK
  window replacing a stale instance on relaunch instead of re-showing
  pre-upgrade code (`0.1.0-17`). Status schema unchanged (2) throughout — every
  `p1.x` pairs with every desktop build.
- **`0.1.0-18` / Android `0.1.0-p1.6`** (2026-09-03) — first application of the
  shared design language (D-032, `docs/DESIGN_LANGUAGE.md`). The GTK window gets
  a HeaderBar, labelled sections (Connection / This phone / Preferences /
  Activity), a coloured status pill, a header overflow menu, and symbolic icons
  on the primary buttons; the Android app aligns its palette tokens, section
  headings, and status pill to the same spec. Cosmetic only — no behaviour
  change, no new dependency, status schema still 2.
- **Verification:** 90 host unit tests, 30 Android unit tests, both APKs + the
  `0.1.0-18` deb build. **Live end to end on the dev laptop + pilot phone.**
  2026-09-01: release key generated (D-030), release-signed APK pushed via
  `teather device install` (D-029), `teather connect` through the new `teatherd`
  — unauthenticated SOCKS refused (`000`), authenticated egress on Verizon
  cellular over the real `teather0` failover route (D-028), both APKs
  `CN=Teather`. 2026-09-03: `0.1.0-13` self-heal fix recovered a real wedged
  daemon; `0.1.0-17` + `p1.5` installed, the GTK "Update app (v5→v7)" button
  pushed the new APK, and the daemon now reports `android_security: 1` /
  `security_update_available: false` (matched) — confirmed by the owner as
  "all working".
- **Remaining:** nothing blocking. Primary-goal verification has operational
  support (E-012: no tether hard-stop or carrier notice on a hard-stop prepaid
  plan under heavy daily use); the controlled E-011 network-layer check is
  opportunistic, pending a reflector host. Plus the phone-reboot fault case and
  an ongoing daily-use soak.
- **Runnable build:** Android `0.1.0-p1.6` (`versionCode 8`, design-language
  visual pass — D-032; `0.1.0-p1.5` security-version layer — D-031; `0.1.0-p1.4`
  appearance setting; `0.1.0-p1.3` SOCKS relay auth — D-028, status schema 2);
  Debian package
  `0.1.0-18` (design-language visual pass to the GTK client — D-032; `0.1.0-17` GTK window replaces a stale instance on relaunch; `0.1.0-16` D-031 security layer + state-driven phone-app button; `0.1.0-15` GUI "Phone app" install button; `0.1.0-14` appearance setting on both halves; `0.1.0-13` self-heal wedge fix +
  orphaned-sentinel recovery + GTK icon; `0.1.0-12` D-028 relay auth + udpgw
  parser hardening; `0.1.0-11` D-026 self-healing + logging; `0.1.0-9` D-025
  standalone connect; `0.1.0-8` added the udpgw tuning;
  `0.1.0-7` raised the 64->256 flow ceiling). `0.1.0-4` = D-022 (NetworkManager owns `teather0` as an in-memory
  `tun` connection, no setuid helper or polkit action, additive DNS, automatic
  failover). `0.1.0-5` adds D-023 (`teather upstream auto|cellular|wifi|
  ethernet`). `0.1.0-6` / `0.1.0-p1.1` makes the upstream switch zero-gap
  (`ACTION_RECONFIGURE`, also phone-side), adds general UDP (D-024: tun2proxy
  `udpgw` + a phone-side `UdpGatewayServer` — no VpnService, no second forward),
  matches the Android icon to the Linux artwork, drops stale "P0" wording.
  `0.1.0-7` / `0.1.0-p1.2` raises the relay concurrency ceiling to 256. 90 host
  unit tests (4 for D-025, 20 for D-026, 3 for D-028, 5 for D-029, 2 for the
  `0.1.0-13` self-heal fix, 2 for the appearance setting, 4 for D-031, 2 for the
  D-032 status pill) + D-Bus smoke
  pass; 30 Android unit tests pass (`:app:testDebugUnitTest`) with the SDK now at
  `~/Android/Sdk` (`local.properties` corrected).
  **Live-tested end to end on 2026-08-30 on the developer laptop + phone**
  (see the work-log entry): install, connect, TCP, full Wi-Fi-loss failover,
  UDP via udpgw (STUN round-trip), zero-gap `teather upstream` switch, and a
  clean teardown to byte-identical host state. **Earlier** validation (pre-UDP):
  in the
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

The implemented vertical path, proven end to end on the owner's phone + laptop:

```text
Linux app -> teather0 TUN -> tun2proxy -> ADB forward (loopback) ->
  Android SOCKS5 / udpgw relay -> selected Android upstream (cellular) -> Internet
```

P1 (Linux USB Desktop) is **complete and daily-driven.** D-022 (NetworkManager
owns an in-memory `teather0`, no privileged helper, additive DNS, automatic
failover) and D-023 (`teather upstream` picks the phone's transport, zero-gap)
were validated in a disposable VM and then live on this laptop 2026-08-30.

After P1, the owner **directed a focused post-P1 track** and rejected the
roadmap's assumption that all of P2 ("protocol completeness") and P4 (WireGuard)
must follow — this discharged D-018. What was actually done:

- **D-024** — lightweight general UDP over tun2proxy's `udpgw` stream, terminated
  by a phone-side `UdpGatewayServer` (no VpnService, no packet stack, no second
  forward). Live-tested (STUN round-trip); Shadow PC cloud gaming works.
- **D-025** — Teather can come up as the *only* internet path when the host has
  no other link. Live-tested 2026-08-30.
- **D-026** — self-healing after an abnormal disconnect, persistent
  `teatherd.log`, toast notifications, single-instance GTK, sole-path tracking.
  Fault-injection tested 2026-08-31.

The owner also clarified the **primary goal**: cellular traffic through Teather
must not be classified as tethered. The re-origination that serves that goal is
already built (the phone opens every socket itself); the 2026-08-30 test
confirmed the egress is genuinely the phone's cellular link.

**Operational evidence (E-012, 2026-09-01):** on the owner's prepaid Straight
Talk plan, where exceeding the tether allowance is a hard stop, sustained daily
Teather use — including a ~4-hour heavy session — has produced no tether
hard-stop and no carrier notice. Recorded as observation, not proof (D-009).
The controlled network-layer comparison (E-011) is now opportunistic, pending a
reflector host reachable from the phone's cellular.

**Remaining:** the phone-reboot fault case; an ongoing daily-use soak. IPv6,
multi-client, other platforms, and the WireGuard endpoint (P4) stay deferred and
not in progress.

## Implemented surface (what actually exists)

### Android relay — `app/` (Kotlin, `0.1.0-p1.6`, `versionCode 8`, release-signed — D-030)

- `RelayService` — an exported `connectedDevice` foreground service protected by
  `android.permission.DUMP` (D-016), driven by `ACTION_START` / `ACTION_STOP` /
  `ACTION_RECONFIGURE` intents carrying `relay_port` + `relay_upstream`.
- `Socks5Server` — SOCKS5 with RFC 1929 username/password auth (D-028: a per-run
  128-bit secret the phone publishes only in its `DUMP`-protected status), TCP
  `CONNECT` for IPv4 / domain / literal IPv6 targets, bound strictly to
  `127.0.0.1`; per-connection outbound socket opened by `AndroidNetworkConnector`
  on the selected `Network`.
- `UdpGatewayServer` + `UdpGatewayProtocol` — terminates tun2proxy's badvpn-style
  "udpgw" TCP stream on the phone, one `DatagramSocket` (bound to the chosen
  upstream) per connection id. Carries general UDP with no VpnService, no packet
  stack, no second ADB forward (D-024).
- `NetworkSelector` / `UpstreamPreference` — `auto|cellular|wifi|ethernet`,
  swappable live (`reconfigure()` rebinds without a listener teardown; open
  sockets keep their link).
- `RelayStats` / `RelayStatusWire` — accepted/established/rejected/active
  counts, byte totals, last upstream, error categories, cellular
  available/validated, and the per-run SOCKS secret; surfaced via `dumpsys`
  (schema 2).
- `MainActivity` — port + upstream picker, start/stop, live status, "copy the
  laptop commands" clipboard helper, "Get the desktop client" link (D-029),
  notification-permission prompt.
- 27 unit/integration tests: SOCKS5 negotiation + RFC 1929 auth, udpgw framing
  (incl. truncated-address rejection), the udpgw server, and the status wire.

### Linux client — `desktop/linux/teather/` (Python + PyGObject, Debian `0.1.0-18`)

- `teatherd` — per-user D-Bus service (`systemd --user`), no elevation. Poll
  loop runs `reconcile()` → `health_check()` → `maybe_auto_connect()` every ~3s.
- `Manager` — connect / disconnect / recover / reconcile / health-check /
  upstream-switch / device approve-rename-forget / failover + auto-connect
  toggles. Owns the `teather0` lifecycle, the tun2proxy child, the ADB forward,
  and the ownership journal in `$XDG_RUNTIME_DIR/teather/`.
- `NetworkManagerConnection` — creates/activates/deletes the one in-memory
  `tun` connection for `teather0` over the system bus (`AddConnection2`
  in-memory flag, `tun.owner` delegation, additive `ipv4.dns-priority` 32050,
  backup default at metric 32000), plus the non-mutating `CheckConnectivity`
  nudge (D-026).
- `preflight` — refuses VPN/split defaults, overlapping routes, nonstandard
  policy rules, a pre-existing `teather0`, or a default that would outrank
  metric 32000; recognises the "standalone" (no physical default) case (D-025).
- `dns_probe` — UDP + TCP virtual-DNS readiness check before reporting connected.
- `AdbClient` — `devices` / `forward` / `forward --list` / `dumpsys` status /
  relay start-stop-reconfigure / `installed_version` / `install -r`, serials
  redacted, 10s timeouts.
- APK lockstep (D-029) — the `.deb` bundles `/usr/lib/teather/Teather.apk` + a
  version sidecar; `Manager.android_app_state` / `install_android` and
  `teather device install` install or upgrade the phone app so the two halves
  stay on the same status schema.
- `logging_setup` — rotating `~/.local/state/teather/teatherd.log` (0600),
  `TEATHER_DEBUG=1` for DEBUG.
- `dbus_service` — the `io.github.vel71184.Teather1.Manager` interface
  (`GetStatus`, `ListDevices`, `Connect`, `Disconnect`, `ApproveDevice`,
  `RenameDevice`, `ForgetDevice`, `SetAutoConnect`, `SetAutoFailover`,
  `SetUpstream`, `AndroidAppState`, `InstallAndroid`, `Diagnose` +
  `StatusChanged`/`DevicesChanged`/`MetricsChanged` signals) and the
  self-clearing toast notifications.
- `cli.py` — `teather status|devices|connect|disconnect|device
  approve|rename|forget|install|autoconnect|failover|upstream|diagnose|recover`,
  all pure D-Bus clients.
- `gui.py` — single-instance GTK3 window: device picker, connect/disconnect,
  approve/rename/forget, auto-connect + failover checkboxes, upstream combo,
  live metrics, diagnostics, recovery hint. AppIndicator tray when the desktop
  supports it; closing the window never disconnects.
- `config.py` — mode-0600 JSON, locally salted device-id hashes, never the raw
  serial.
- Packaging: `.deb` (`packaging/`), `systemd --user` unit with
  `ProtectSystem=strict` + `StateDirectory=teather`, D-Bus activation file, man
  pages, `RECOVERY.md.gz`, the bundled `Teather.apk`. `build-deb.sh` rebuilds
  `tun2proxy` with `--features udpgw` as needed and prefers a release-signed APK.
- 90 host unit tests (`python3 -m pytest desktop/linux/tests/test_core.py`).

### Historical P0

The `desktop/linux/teather-p0` helper and `docs/P0_HANDOFF.md` reproduce the
completed P0 experiment (SOCKS-only TCP over ADB). Superseded by P1; kept for
reference.

## Open threads (none blocking)

1. **E-012 follow-ups** — check per-app cellular data-usage attribution on the
   phone after a heavy session; keep logging heavy sessions and any carrier
   contact across billing cycles.
2. **E-011 (opportunistic)** — the controlled TTL/JA3 comparison, when a
   reflector host reachable from the phone's cellular is available. A
   ready-to-deploy reflector can be built ahead of the host.
3. **Phone-reboot fault case** — the one D-026 fault not yet exercised; plus the
   ongoing daily-use soak.
4. Optional: the bare-host auto-revert / dead-man's-switch (punch item 3,
   sketched, not built) if the owner wants zero-babysit confidence beyond the
   D-026 self-heal.
5. Remaining pre-public items (roadmap): explicit license (D-010), a
   vulnerability-reporting channel (`SECURITY.md`), and a first tagged release
   with the APK + deb attached (the app's download button and `teather device
   install` want something to point at).

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
- D-018 (stop for explicit planning before P2) was **discharged** by the owner's
  2026-08-30 post-P1 directive: a focused track (D-024 lightweight UDP, D-025
  standalone connect, D-026 robustness, E-011 primary-goal verification) instead
  of the full P2/P4 sequence.
- The Android build is release-signed with a project key held by the owner
  outside the repo (D-030, supersedes D-019). `keystore.properties` /
  `TEATHER_KEYSTORE*` configure it; a debug fallback keeps CI/contributors
  unblocked.
- The `.deb` bundles the matching APK and can install/upgrade it on the phone to
  keep the two halves on one status schema (D-029).
- NetworkManager owns `teather0` as an in-memory `tun` connection
  with `tun.owner` delegation and additive DNS; there is no setuid-root helper or
  custom polkit action (D-022, supersedes D-020 and D-021).
- General UDP is carried over tun2proxy's `udpgw` and terminated on the phone —
  no VpnService, no packet stack (D-024).
- Teather may be the sole internet path when armed and no other link exists
  (D-025); an abnormal disconnect self-heals and auto-reconnects (D-026).
- The loopback SOCKS relay requires RFC 1929 auth with a per-run secret the
  phone publishes only in its `DUMP`-protected status; `dumpsys` schema is 2
  (D-028).

See `docs/DECISIONS.md` for rationale and status.

## Important unknowns

- Provider classification/accounting behavior is unmeasured and cannot be
  generalized. The egress is confirmed to be the phone's cellular link; the
  controlled TTL/JA3 comparison (E-011) is opportunistic, and E-012 records the
  operational evidence (no tether hard-stop on a hard-stop prepaid plan).
- Carrier classification/accounting over sustained daily use is unmeasured —
  that is the owner's ongoing daily use, not a synthetic gate.
- The userspace WireGuard endpoint remains a P4 hypothesis and is not planned
  work right now.
- IPv6 through Teather is unsupported and not in progress.
- Repository license remains undecided until before public access.

## Explicitly not in progress

- IPv6 through the tunnel
- WireGuard endpoint / "become a VPN" scope
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
4. ~~**Idempotent ADB cleanup + robust journal recovery.**~~ Done 2026-08-31,
   first as `0.1.0-10` then reworked into D-026's teardown model (`0.1.0-11`):
   the ownership journal now names *host* resources to release, and is cleared
   as soon as the host side (tun2proxy + `teather0`) is verified clean — a
   phone-side ADB step that cannot be confirmed is logged and hinted but never
   keeps the journal, so `teather connect` is never wedged by one. An
   unverifiable `teather0` still raises `ambiguous-interface` and asks for a
   restart. Original report below.
   Observed 2026-08-30 after deploying `0.1.0-9`: restarting
   `teatherd` while a connection was live left the ownership journal with
   `recovery-pending`, and `teather connect` then refused until the journal file
   was removed by hand. Cause: `adb forward --remove` of an already-gone forward
   (and `stop_relay` of an already-stopped relay) returned non-zero, which
   `disconnect()` and the startup `recover()` both treated as "cleanup
   unverified", so the journal was kept. Fix, as landed: `AdbClient.
   remove_forward` swallows a `... not found` failure (covers both a missing
   listener and a vanished device) and `AdbClient.stop_relay` catches a failed
   STOP delivery and lets the status poll confirm the relay is down; the
   loopback-only forward and a phone-side relay are not host state.
   `Manager.recover()` now runs the ADB cleanup best-effort inside a
   `try/except TeatherError` and always clears the journal after `nm.recover()`
   has verified the NetworkManager/tunnel teardown — `nm.recover()` still raises
   (journal retained) for a genuinely ambiguous `teather0`. Takes effect on the
   next package rebuild + `systemctl --user restart teather.service`; the stale
   journal from the original report was cleared by hand in the meantime.
5. ~~**Connectivity re-check after a standalone activation.**~~ Implemented
   2026-08-31 (`0.1.0-11`, D-026), **not yet live-verified**. After a
   standalone armed activation the manager calls
   `NetworkManagerConnection.recheck_connectivity()`, which invokes
   `CheckConnectivity` on the NM D-Bus object (best effort, never fails a
   connect). Still to confirm in a real standalone session with
   `nmcli -f CONNECTIVITY,STATE g`; if NM's default probe URL can't be reached
   through the tunnel the icon may still lag until a real request goes out.
6. ~~**Automatic reconciliation loop.**~~ Implemented 2026-08-31 (`0.1.0-11`,
   D-026), **not yet live-verified**. `Manager.reconcile()` runs on the daemon
   poll: when nothing is connected but there is leftover state (a
   `recovery-pending` error, an ownership journal, or a `teather0` interface) it
   releases Teather-owned resources and returns to a clean `disconnected` state
   so auto-connect can take over. `health_check()` also detects an unplugged
   phone, a dropped ADB forward, and a stopped relay (not just a dead tunnel /
   vanished `teather0`). The host side (routes/DNS/`teather0`) stays strict — an
   unverifiable `teather0` still surfaces and asks for a restart, and nothing
   re-mutates routes/DNS on a schedule. Only phone-side cleanup is treated as
   non-blocking. The opt-in dead-man's-switch (item 3) is still separate and
   unbuilt.

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

A short dated entry when something ships or a session ends: what changed and how
it was verified. A "next action" line is optional — add one only when you are
deliberately leaving a specific thread for later, not as a routine handoff. When
a milestone finishes, make sure the roadmap, this file, `AGENTS.md`'s "Current
priority", and the README status line agree — a milestone isn't done until they
do. When this section runs past ~400 lines, drop the entries older than the
current milestone; git history keeps them.

### 2026-09-03 — Shared design language; GTK visual pass (D-032, `0.1.0-18` / `0.1.0-p1.6`)

- **Trigger:** the owner asked how to polish the utilitarian GTK window and keep
  it uniform with the Android app and future platform clients.
- **Decision (D-032):** uniformity comes from a written spec
  (`docs/DESIGN_LANGUAGE.md`), not a cross-platform UI toolkit (Electron /
  Flutter / Compose Multiplatform / one Qt client all rejected — they fight
  "keep Android lightweight"). Each client stays native and follows the spec:
  same section order and vocabulary, same daemon-driven status-pill model, same
  accent + pill colour tokens, same icon metaphors. Worst-case fallback the
  owner accepted: rewrite the same small program per platform.
- **GTK (`gui.py`):** HeaderBar with a title and an overflow menu (Diagnostics,
  Restart window); the flat control stack is now labelled sections (Connection /
  This phone / Preferences / Activity) inside a `ScrolledWindow`; connection
  state is a coloured **●** pill (`_status_markup`, Pango markup on a label — no
  CSS provider, so it cannot fight the theme) instead of a "State:" line;
  Connect / Disconnect / Approve / Rename / Forget / Phone-app carry symbolic
  icons. No behaviour change.
- **Android (`MainActivity.kt`, `res/`):** `colors.xml` + `values-night/`
  carry named palette tokens (`accent`, `surface_sunken`, `status_*`); the
  theme's `colorAccent` references `@color/accent`; content is grouped under
  accent section headings; a bold coloured status pill sits above the monospace
  block. Cosmetic; `SECURITY_VERSION` and `SCHEMA_VERSION` unchanged.
- **Verified:** 90 host unit tests (2 new for `_status_markup`), 30 Android unit
  tests, `:app:assembleRelease` + `lintVitalRelease`, `Teather.apk.version`
  sidecar `8 / 0.1.0-p1.6 / 1`, `0.1.0-18` deb built. `gui.py` imports and the
  pill helper renders/escapes correctly. Live GTK look is the owner's check
  after installing `0.1.0-18`; the Android reinstall is optional (cosmetic,
  schema unchanged).

### 2026-09-03 — GTK window replaces a stale instance on relaunch (`0.1.0-17`)

- **Trigger:** the owner disconnected, closed the Teather window, installed a
  new `.deb`, reopened `teather-gtk` — and got the **old** GUI. Cause: closing
  the window only hides it to the tray (D-026), so the pre-upgrade process stays
  alive, and the single-instance `Gtk.Application` re-presents that stale
  process instead of loading the new code.
- **Fix (`gui.py` only):** the app now uses
  `ALLOW_REPLACEMENT | REPLACE`, so any `teather-gtk` launch takes over a
  running instance rather than re-presenting it. Belt-and-suspenders: a window
  open across a package upgrade watches its own installed `*.py` mtimes and
  shows a "restart this window" banner (which `os.execv`s itself) when they
  jump. Takes full effect once the running instance is already on `0.1.0-17+`
  (the replacement handshake needs both sides to allow it).
- **Verified:** 88 host unit tests still pass; `gui.py` compiles; the mtime
  helper resolves against whichever copy is running. Live window behaviour is
  the owner's check after installing `0.1.0-17`.

### 2026-09-03 — Security-version layer + state-driven phone-app button (D-031, `0.1.0-16` / `0.1.0-p1.5`)

- **Trigger:** the owner wanted a multi-layer version scheme — a visible
  "security version" in the app, a desktop that treats a matching one as
  compatible and an older one as an update, with the install button greyed to
  "installed" when everything checks out, and a *popup* (not just a button) for
  security-relevant updates.
- **Android:** `RelayStatusWire.SECURITY_VERSION` (=1), published as
  `teather.status.security` and shown as "Security level: N". Does **not** gate
  pairing (that stays `SCHEMA_VERSION`). `versionCode 7` / `0.1.0-p1.5`.
- **Linux:** `android_status.py` parses `security`; `Teather.apk.version` gains
  a third line (bundled security level); `build-deb.sh` reads it from the Kotlin
  source. `teatherd` remembers the phone's level (`_note_relay_status`) and
  exposes `android_security` + `security_update_available` in `GetStatus`.
- **GTK:** the phone-app button is now state-driven — "Install app" / "Update
  app" / "Security update" (destructive-action styling) / disabled "App up to
  date" / "Phone app is newer". A one-time dialog fires when
  `security_update_available` becomes true. The app check is on-demand (GUI
  start, phone appears, app-related connect error), never on the poll loop.
- **Verified:** 88 host unit tests (4 new), 30 Android unit tests,
  `assembleRelease` + `lintVitalRelease` clean, `0.1.0-16` deb's sidecar reads
  `7 / 0.1.0-p1.5 / 1`. See `docs/DECISIONS.md` D-031.
- **Done 2026-09-03:** `0.1.0-17` installed; the GTK "Update app (v5→v7)" button
  pushed `p1.5` to the pilot phone; the daemon then reported `android_security:
  1` / `security_update_available: false`. Owner confirmed "all working".

### 2026-09-03 — Appearance setting on both halves (`0.1.0-14` / `0.1.0-p1.4`)

- **Trigger:** the owner asked for a dark mode with a toggle, first on the GTK
  client and then "the same for the app" (phone app built, not installed yet).
- **GTK client:** an "Appearance" combo (Follow system / Light / Dark) in the
  window. Persisted to `~/.config/teather/gui.json` (a GUI-local file — the
  daemon's `config.json` stays its own domain), applied with
  `GtkSettings.gtk-application-prefer-dark-theme` (`reset_property` for "follow
  system"). `desktop/linux/teather/gui.py`.
- **Android app:** matching setting, no AppCompat (keeps the app light —
  `teather-keep-android-lightweight`). `ThemePreference` enum + a pure
  `applyNightMode(pref, uiMode)`; `MainActivity.attachBaseContext` hands the
  activity a base `Configuration` with forced night bits and `recreate()`s on
  change; `res/values-night/{styles,colors}.xml` added; the one hardcoded
  status-box colour moved to `@color/status_background`. Works on the full
  minSdk 26+ range. `versionCode 6` / `0.1.0-p1.4`.
- **Packaging:** `0.1.0-14` deb bundles the `p1.4` APK. Status schema unchanged
  (2) — `p1.3` and `p1.4` pair identically, so no forced upgrade.
- **Verified:** 84 host unit tests (2 new for the GUI prefs round-trip), 30
  Android unit tests (3 new for `ThemePreference`), `assembleRelease` +
  `lintVitalRelease` clean, `0.1.0-14` deb built and its bundled
  `Teather.apk.version` reads `6 / 0.1.0-p1.4`. The GTK theme API was
  smoke-checked live (`set_property` / `reset_property` both work).
- **Done 2026-09-03:** superseded on the phone by `p1.5`; the Appearance
  dropdown is live in the installed GTK client (`0.1.0-17`).

### 2026-09-03 — Self-heal wedge fix; orphaned DNS sentinel; GTK icon (`0.1.0-13`)

- **Trigger:** daily use — after a reboot the daemon was stuck in `state=error`
  / `dns-residue`, looping "The Teather DNS sentinel is already present" and
  never recovering on its own. The Sep 2 shutdown had left `198.19.0.1` in
  `resolv.conf` with no `teather0` connection (adb server had died mid-teardown:
  `shutdown teardown incomplete: ['networkmanager-connection']`); at boot
  `teatherd` started before NetworkManager regenerated `resolv.conf`.
- **Root cause:** two compounding gaps. (1) `Manager._reconcile_locked`'s
  `needs` predicate only self-healed while `_error_category == "recovery-pending"`.
  A failed `maybe_auto_connect` runs through `connect()` → `preflight()`, which
  raises `dns-residue`; the except handler latches that raw category. The poll
  loop then saw a category it did not recognise, went dormant, and never
  re-checked — even after NM cleared the stale `resolv.conf` ~60 s later.
  `maybe_auto_connect` is separately gated on `_state in {disconnected,detected}`,
  so it was dormant too. Fully wedged until a manual restart. (2)
  `NetworkManagerConnection.recover()` raised `dns-residue` on an orphaned
  sentinel (sentinel present, no `teather0` to delete) with no way to act on it.
- **Fix:** `desktop/linux/teather/manager.py` — reconcile self-heals on any
  `_state == "error"`. `desktop/linux/teather/networkmanager.py` — new
  `transport.reload_dns()` (NM `Reload(0x2)`, the D-Bus form of
  `nmcli general reload dns-rc`); `recover()` calls it when the sentinel is
  orphaned, then re-checks. `desktop/linux/teather/gui.py` — window
  `set_icon_name("teather")` + `GLib.set_prgname("teather")` so the Wayland
  shell / X11 switcher shows the Teather icon; `packaging/teather.desktop`
  gained `StartupWMClass=teather`.
- **Verified:** 82 host unit tests (2 new — `test_reconcile_self_heals_an_error_
  latched_by_a_failed_connect`, `test_recover_clears_an_orphaned_dns_sentinel_via_
  networkmanager_reload`). Live: `teather recover` on the running (old-code)
  daemon unwedged it — `state: connected`, `standalone: true`, egress
  `203.0.113.12` (Verizon cellular), `teather0` activated, DNS ready.
- **Done 2026-09-03:** shipped in `0.1.0-13` and now installed (via `0.1.0-17`);
  the self-heal is automatic on the running daemon.

### 2026-09-01 — Security review of the tree; SOCKS relay authentication (D-028, `0.1.0-12`)

- **Trigger:** the owner asked for a full security review + hardening pass now
  that the feature set is stable and public release is a goal.
- **Review:** read the whole tree (Android relay + parsers, Linux `teatherd` +
  D-Bus + all subprocess construction, config/journal handling, DNS probe,
  packaging/supply chain). The code is well-hardened — `O_NOFOLLOW`/mode/uid
  checks on state files, list-form subprocess with a fixed `PATH` everywhere, no
  `eval`/`pickle`/`shell=True`, checksummed tun2proxy source + `Cargo.lock`,
  NM-ownership verification before any `teather0` delete, bounds-checked
  parsers. **Nothing HIGH or MEDIUM.** One real finding (already noted in the
  threat model as not-releasable): the phone-side SOCKS listener was no-auth and
  Android loopback is reachable by every installed app, so any app — even one
  with no `INTERNET` permission — could use the relay as an open proxy on the
  phone's upstream. Plus one LOW: a truncated udpgw address block threw an
  unchecked exception instead of a protocol error.
- **Fix (D-028):** the relay now requires SOCKS5 username/password auth
  (RFC 1929). `RelayRuntime` generates a fresh 128-bit hex secret per start
  (kept across a same-port live rebind), exposed only in the `DUMP`-protected
  status wire (`teather.status.secret`); `teatherd` reads it and passes
  `--proxy socks5://teather:<secret>@127.0.0.1:<port>` to tun2proxy. Constant-time
  compare on the phone. Status schema → 2 so a schema-1 relay and this client
  refuse to pair. udpgw `readTarget` now bounds-checks and raises `IOException`.
- **Files:** `app/.../relay/{Socks5Protocol,Socks5Server,UdpGatewayProtocol}.kt`,
  `app/.../service/{RelayRuntime,RelayStatusWire}.kt`, `app/build.gradle.kts`
  (`versionCode 5` / `0.1.0-p1.3`); `desktop/linux/teather/{constants,
  android_status,manager}.py`; `packaging/{debian/control,debian/changelog,
  scripts/build-deb.sh}` (`0.1.0-12`); Android + Linux tests; `docs/{DECISIONS
  (D-028),THREAT_MODEL,DEVELOPMENT}.md`.
- **Verified:** `test_core.py` 72 → 80; `:app:testDebugUnitTest` 27, both APKs
  and the `0.1.0-12` deb build (SDK installed at `~/Android/Sdk` during this
  session; `local.properties` corrected from a stale `/tmp/android-sdk`). D-028's
  parser + schema-2 gate confirmed against a real schema-1 `dumpsys` from the
  pilot phone. Live D-028 handshake + D-029 install flow against the new APK
  still pending (needs the new `teatherd`).

### 2026-09-01 (later) — D-028/D-029/D-030 live-verified end to end

- Owner generated the release key (`~/.teather/teather-release.jks`, KeePass);
  `keystore.properties` filled in. `assembleRelease` now signs with `CN=Teather`
  (SHA-256 `5416ff96…78f7f4`); `build-deb.sh` bundles it with no debug warning.
- Sequence on the dev laptop + pilot phone: `adb uninstall` the debug build →
  `dpkg -i` the `0.1.0-12` deb (daemon already on the new code) → `teather
  device install --yes` installed the release-signed APK (`action: installed`);
  a second `teather device install` reported "already current" → `teather
  connect` → `state: connected`, armed, `dns_ready`.
- D-028 confirmed live through the real `teatherd`: an unauthenticated
  `--socks5-hostname` curl is refused (`000`); `teather:<secret>@…` egresses on
  Verizon cellular (`203.0.113.11`), including over the `teather0` failover
  route. `tun2proxy` runs with `--proxy socks5://teather:<secret>@…`; the relay
  shows `accepted_clients=2` (SOCKS + udpgw, both authenticated).
- End state: connected as the armed backup, Wi-Fi primary — the owner's normal
  daily config, now fully on schema 2 + the release key.

### 2026-09-01 — Desktop bundles/installs the APK (D-029); release signing wired (D-030)

- **Trigger:** the owner asked whether the two halves could be packaged so one
  can provide/install the other, and whether to move to a real signing key.
- **D-029:** the `.deb` bundles `Teather.apk` + a `Teather.apk.version` sidecar
  (`build-deb.sh` reads the version from `app/build.gradle.kts`, prefers a
  release APK). `teatherd` gains `AndroidAppState` / `InstallAndroid`; the CLI
  gains `teather device install [id] [--yes]` (confirms, no-ops when current or
  newer, `adb install -r` otherwise). `connect()`'s app-missing error points at
  it. The Android app got a "Get the desktop client" button → releases page.
  Rejected: bundling the desktop client in the APK — the phone can't push to the
  host.
- **D-030:** `app/build.gradle.kts` reads a gitignored `keystore.properties` (or
  `TEATHER_KEYSTORE*` env), falling back to the debug key with a warning.
  `keystore.properties.example` + `.gitignore` entry added. Supersedes D-019.
  The keystore is the owner's to create; the pilot phone needs one
  uninstall/reinstall on the debug→release transition.
- **Files:** `app/build.gradle.kts`, `app/.../MainActivity.kt`,
  `app/src/main/res/values/strings.xml`, `keystore.properties.example`,
  `.gitignore`; `desktop/linux/teather/{constants,adb,manager,dbus_service,
  cli}.py`; `packaging/{scripts/build-deb.sh,debian/changelog,man/teather.1}`;
  tests; `docs/{DECISIONS,PROJECT_STATUS,README,...}`.
- **Verified:** 80 host tests, 27 Android tests, deb built and inspected
  (`Teather.apk` + `Teather.apk.version` present, sidecar reads `5 / 0.1.0-p1.3`).

### 2026-09-01 — Record operational carrier evidence; E-011 becomes opportunistic (E-012)

- **Trigger:** the owner pointed out real-world evidence for the primary goal —
  on a prepaid Straight Talk plan where exceeding the tether allowance is a hard
  stop, heavy daily Teather use (incl. a ~4-hour session, mostly Claude Code CLI)
  has never tripped the tether hard-stop or drawn a carrier notice.
- **Change (docs only):** added `docs/EXPERIMENTS.md` **E-012** (ongoing
  operational observation, hedged per D-009 — consistent with on-device metering,
  not proof), queue row, and reprioritised **E-011** (the controlled TTL/JA3
  reflector comparison) from "next / blocking" to opportunistic. Propagated to
  `AGENTS.md` "Current priority" item 3, `docs/PROJECT_STATUS.md` top block +
  Current objective + Open threads.
- **Note:** clarified that the phone's *built-in tethering monitor* staying flat
  is expected by construction (Teather never touches Android's hotspot subsystem)
  and is not itself evidence. The over-allowance usage with no hard-stop is the
  real signal. E-012 follow-up: check per-app cellular data attribution on the
  phone.
- **Verified:** docs only, no code. `grep` for stale "E-011 ... Next" framing.

### 2026-09-01 — Retire the per-turn check-in process (D-027, docs only)

- **Trigger:** the owner noted that the project's Codex-era docs bake in
  handholding — the assistant checks in at nearly every step because the
  instructions were written that way — and asked to remove that so the assistant
  can run longer autonomously.
- **Change (docs only, no code):** `AGENTS.md` — trimmed the resume ritual to
  `PROJECT_STATUS.md` alone, added a "Working autonomy" section (whole arcs, no
  "next exact task" handoff, deferred scope is deprioritised not gated), rewrote
  "Finishing a change" to drop the per-edit status write and the handoff line.
  `docs/DEVELOPMENT.md` "Definition of done" — same. `docs/PROJECT_STATUS.md`
  work-log preamble — entries on ship/session-end, "next action" optional, trim
  past ~400 lines. `docs/P1_HANDOFF.md` — replaced the stale "stop for P2 / no
  UDP" closeout with the discharged-D-018 state. `docs/DECISIONS.md` — D-027.
- **Unchanged:** the Safety gates (phone, live-host network, outward actions),
  the Hard constraints, D-009 (no stealth features), D-010 (license), D-019
  (release signing). Those are real gates, not process ceremony.
- **Verified:** `python3 -m pytest desktop/linux/tests/test_core.py` (unchanged,
  passing) — no code touched. `grep` for residual "next exact action" /
  "discuss with the owner before starting" in the live docs.

### 2026-08-31 — Self-healing, persistent logging, notifications (D-026, `0.1.0-11`)

- **Trigger:** the owner, on a live tether, hit "no internet" after rebuilding
  `0.1.0-10` and restarting `teatherd`. Diagnosis: the standalone connection
  came up fine, then the ADB forward on :44095 died in a USB/adb blip ~7 min
  later; `health_check()` only tested "tun2proxy alive" and "teather0 present",
  so the daemon kept reporting `connected` over a dead data path with no
  fallback. There was also **no daemon log** to look back at (`teatherd` used
  the `logging` module nowhere; `daemon.py` and `recover()` swallowed every
  exception). Recovered live by killing 7 stale GTK instances and
  `teather disconnect && teather connect` (verified with a SOCKS-proxied curl).
- **Owner asks:** (1) always keep a comprehensive debug log; (2) any *abnormal*
  disconnect (not a click / command) must self-detect, self-clean, and let the
  next connect just work — "idiot-proof"; (3) closing the GTK window must not
  look like it kills the connection; (4) a visible status surface even when
  connecting with no Wi-Fi (no tray icon in standalone mode).
- **Change (D-026, all in `desktop/linux`, uncommitted):**
  - `logging_setup.py` — rotating `~/.local/state/teather/teatherd.log` (0600)
    via `StateDirectory=teather`, plus stderr→journal. `TEATHER_DEBUG=1` → DEBUG.
    `adb`/D-Bus/NM/connect/reconcile/health steps logged; destinations and
    resolver contents are not. Falls back to stderr-only if the dir isn't
    writable; never crashes.
  - `manager.py` — `_release_owned()` shared teardown: **host side strict**
    (journal kept, `clean=False`, until tun2proxy + `teather0` verified
    released; an unverifiable `teather0` raises `ambiguous-interface`),
    **phone side lenient** (a forward that won't remove / a relay that won't
    confirm stopped is logged + hinted, journal still cleared). `health_check()`
    runs cheap checks every ~3 s (unplugged phone via `adb devices`, dropped
    forward via `adb forward --list`, dead tunnel, vanished `teather0` — all
    local to the adb server / D-Bus). The relay `dumpsys` probe is a slow
    (~2 min) backstop, suppressed while a GUI is polling status. An abnormal
    drop lands in a clean `disconnected` state (not `error`) with a new
    `last_drop` field, so the existing 3-s auto-connect brings it back when the
    phone returns — but auto-connect stops after 3 straight failures and rests
    until a replug / manual Connect / 2-min pause. `reconcile()` runs on the
    poll loop and clears a `recovery-pending` / stale-journal / orphan-`teather0`
    state without a manual `teather recover`. Startup runs the same check and
    logs its result. New status fields `recovery_hint`, `last_drop`.
  - `adb.py` — `list_forwards()`; every `_run` argv logged with the serial
    redacted.
  - `networkmanager.py` — `recheck_connectivity()` (`CheckConnectivity` on NM),
    called after a standalone armed activation (punch item 5).
  - `dbus_service.py` — desktop notifications on connect / drop / self-heal /
    sole-path change / needs-attention. Critical urgency + `replaces_id` (GNOME
    won't banner normal urgency), and the daemon closes its own banner after
    ~8 s so all but "needs attention" behave as toasts.
  - `gui.py` — single-instance `Gtk.Application` (re-launch re-presents, kills
    the multi-process problem); window close never disconnects; shows
    `recovery_hint` and a "closing this window doesn't disconnect" note.
  - `packaging` — `0.1.0-11`; `teather.service` gains `StateDirectory=teather`;
    man page notes the log + self-heal.
- **Verified:** `python3 -m pytest desktop/linux/tests/test_core.py` — **72
  passed** (20 new/rewritten for D-026; 6 old tests that encoded the
  conservative "keep the journal, surface recovery-pending" contract were
  rewritten to the new self-heal contract, each still asserting host
  resolver/route state is fully restored).
- **Live-tested 2026-08-31 (dev host, `0.1.0-11`):**
  - Built, `dpkg -i` over `0.1.0-10`, `systemctl --user restart`. Clean start;
    `~/.local/state/teather/teatherd.log` created (0600); startup session check
    cleared the orphaned teather0 + dead tun2proxy left by the `0.1.0-10`
    session. `teather connect` came up as an armed backup with a **verified**
    data path (SOCKS-proxied curl through the phone → 200).
  - **Bug found + fixed:** killing tun2proxy self-healed to `disconnected` but
    did not auto-reconnect — the teardown was stopping the relay Teather
    started, and auto-connect will not start a stopped relay. Fix: only a user
    `disconnect` stops the relay; a `systemctl restart` now also uses a
    host-only `Manager.shutdown()` that leaves the relay up. +3 regression
    tests.
  - **Fault-injection tests, all pass on the fixed build (`0.1.0-11`):**
    `systemctl restart` → auto-reconnect ~5 s; tun2proxy `kill -9` →
    `tunnel-exited` in 2 s, reconnect ~4 s; `adb kill-server` (the real
    forward-killer) → `relay-unreachable` in 2 s, reconnect ~5 s; phone
    unplug + replug → `phone-disconnected`, reconnect on replug. Data path
    verified each time (SOCKS-proxied curl through the phone). The relay ran
    the whole session (~8 reconnects) without a restart — cumulative byte/client
    counters confirm it.
  - GUI: connection holds through window open/close; a second `teather-gtk`
    re-presents the one window (no second process); clean exit, no orphans.
  - Not the cause of the forward deaths: the phone is USB-only (wireless
    debugging off), USB autosuspend is disabled for it. The USB transport id
    was seen changing on its own (genuine re-enumeration) — that is the
    forward-killer, and it is now a ~5 s self-heal.
  - Standalone (Wi-Fi off while connected): internet kept working, the GNOME
    top-bar network icon **appeared** (the `CheckConnectivity` nudge — punch
    item 5 — works), and `health_check` now tracks Wi-Fi/Ethernet coming and
    going while connected: it keeps the `standalone` flag accurate and toasts
    "Teather is now your only connection" / "Wi-Fi/Ethernet is back". Confirmed
    on a real Wi-Fi toggle — toast fired both ways, icon held, internet held.
  - Notifications: GNOME only banners *critical* urgency and never self-expires
    it, so all notifications go out critical + `replaces_id`, and the daemon
    closes its own banner after ~8 s (toast) for everything but "needs
    attention". Confirmed working on the dev host.
  - **Deferred:** phone reboot (owner will bench it for later).
- **Next action:** commit D-025 + D-026 (owner's call); phone-reboot soak when
  convenient; then the E-011 TTL/JA3 half.

### 2026-08-30 — Connect with no other internet (D-025); standalone/fallback

- **Symptom (owner, on a live tether):** on a host with no Wi-Fi and no
  Ethernet, `teather connect` refused. The gate was `preflight` — `evaluate_routes`
  returned `no-default` ("No existing IPv4 default route") and, before that,
  `resolver-unavailable` when `resolv.conf` had no usable nameserver. Workaround
  was an ordinary phone hotspot to bootstrap, then drop it. The primary use case
  was blocked by a leftover D-014/D-015 precondition.
- **Change:**
  - `packaging` — bumped to `0.1.0-9` (changelog + `control` + `build-deb.sh`).
  - `preflight.py` — no physical default is now a `standalone` result
    (`safe=True`), not a refusal. Every ambiguous/unsafe state (VPN/split
    default, overlapping route, nonstandard policy rule, an existing default
    that would outrank metric 32000) is still rejected.
  - `manager.py` `preflight(armed)` — in standalone mode skips the
    pre-existing-resolver requirement when `armed` (virtual DNS + phone-side
    sentinel resolve); refuses with `failover-disabled` when **not** armed
    (a dormant no-default connection does nothing). Threads `armed` in from
    `connect()`. Adds `standalone` to `get_status`; connect message reflects it.
  - `networkmanager.py` — `_verify_additive` (the sole-resolver guard) runs
    only when `preflight` recorded a baseline nameserver, i.e. a physical link
    was up. `_nameservers` tolerates a missing `resolv.conf`.
  - `gui.py` shows "Failover: sole path" when standalone + armed.
  - man page + `docs/DECISIONS.md` D-025 (+ D-014/D-015 notes).
- Fallback is unchanged and automatic: same armed connection, metric 32000 +
  positive DNS priority, so Wi-Fi/Ethernet still takes over if it appears.
- **Verified:** `python3 -m pytest tests/test_core.py` — 52 passed (4 new:
  standalone route preflight, `failover-disabled` when not armed, standalone
  activation with a sentinel-only resolver, standalone connect comes up as the
  only path; 1 updated: `make_manager` preflight stub signature).
- **Deployed + live-tested 2026-08-30:** built `0.1.0-9`, `dpkg -i` over
  `0.1.0-8`, `systemctl --user restart teather.service`. The owner then launched
  with Wi-Fi off and **standalone connect worked** — traffic and DNS over
  cellular with no other link. Fallback (bring Wi-Fi/hotspot back) also
  confirmed working earlier in the armed-backup role.
- **Two issues seen, both filed to the punch list (items 4–5), not fixed:**
  1. The `systemctl restart` while the tether was live left the ownership
     journal `recovery-pending`; `teather connect` refused until
     `/run/user/$UID/teather/ownership.json` was removed by hand. Non-idempotent
     ADB cleanup is the cause — see punch-list item 4. Any restart during a
     connection reproduces it.
  2. No GNOME tray network icon in standalone mode (NM parks at
     `CONNECTED_SITE`/`LIMITED` until its connectivity probe passes through the
     tunnel). Cosmetic — punch-list item 5.
- **Next action:** the E-011 TTL/JA3 half (needs a reflector) and the robustness
  pass, which should now start with punch-list item 4.

### 2026-08-30 — UDP gateway tuning for cloud gaming (`0.1.0-8`); Shadow PC works

- Shadow PC would not load through Teather on the earlier build (tested during
  the full-desktop failover, when the 64-flow ceiling was also being hit).
- Added `--udpgw-connections 16` (keep more gateway streams pooled/warm) and
  `--udp-timeout 30` (keep quieter control flows alive) to `_tunnel_command`.
  No APK change — all tun2proxy-side. Package `0.1.0-8`.
- **Retest 2026-08-30: Shadow PC launched and was usable through Teather** with
  Wi-Fi disconnected (whole desktop on `teather0` -> phone cellular). The owner
  confirmed it worked. Relay counters during the session: `active_sessions` ~44,
  `accepted_clients` 88, `rejected_clients` 1 (the 256 ceiling held), traffic
  flowing both directions through the udpgw path. Stream bitrate / resolution /
  latency were not measured — "worked", not "measured".
- Standing limit (unchanged): udpgw frames UDP over one TCP stream per flow, so
  a single very high-rate media stream is still subject to that stream's
  head-of-line blocking, and cellular CGNAT + extra hops add latency/jitter. If
  a future session needs better cloud-gaming quality, the native-UDP path is a
  wireless local link (the deprioritised P3, which is carrier-neutral). Not
  needed right now — Shadow works.

### 2026-08-30 — Live end-to-end test of tracks 1–2 on the laptop + phone

- Built all three artifacts: APK `0.1.0-p1.2`, a tun2proxy rebuilt with
  `--features udpgw` (installed Rust 1.90.0 for it), Debian `0.1.0-7`. Installed
  both on the pilot phone (SM S266V, versionCode 2 -> 4) and the developer host
  (`0.1.0-5` -> `0.1.0-7`).
- Results (host on Wi-Fi "Banyan Patients"; phone reachable on the same AP and on
  Verizon cellular; upstream `cellular`):
  - `teather connect`: `teather0` up, `resolv.conf` = `8.8.8.8` then
    `198.19.0.1` (additive), backup default `dev teather0 metric 32000`.
  - TCP: `curl --interface teather0 https://api.ipify.org` -> `203.0.113.13`
    (Verizon) while both devices sit on the same Wi-Fi — re-origination on
    cellular confirmed. `example.com` 200 in 0.4 s.
  - Full failover: `nmcli device disconnect wlo1` -> default becomes `teather0`,
    `resolv.conf` collapses to `198.19.0.1` only, TCP and DNS keep working.
  - **UDP via udpgw:** a STUN binding request (`stun.l.google.com:19302`)
    returned a mapped address `38.0.16.15`; `relay.udpgw.stream-open` appears in
    logcat. The udpgw path works end to end.
  - **Zero-gap upstream switch:** `teather upstream wifi` flipped the exit IP
    `203.0.113.13` -> `198.51.100.20` (the phone's Wi-Fi) with the **same
    tun2proxy PID** and no error; `teather upstream cellular` switched back.
  - `teather disconnect`: `teather0` gone; `ip route`, `resolv.conf`, and the
    NetworkManager connection list are **byte-identical** to the pre-test
    baseline (`~/teather-host-evidence/wrapup-2026-08-30/`).
- **Issue found and fixed:** under full-desktop failover the phone-side SOCKS
  server hit its 64-flow ceiling repeatedly (`relay.socks.connection-limit` x55);
  long-lived udpgw streams also hold a slot each. Raised the ceiling to 256
  (`Socks5Server.DEFAULT_MAX_CONNECTIONS`, `tun2proxy --max-sessions`) ->
  `0.1.0-7` / `0.1.0-p1.2`. Re-tested clean.
- Still pending: E-011's TTL/JA3 comparison (needs a reflector and a
  cellular-bound request from the phone, which has no HTTP client — `nc`/`ping`
  only); a longer soak under real daily use; the robustness pass.

### 2026-08-30 — Primary goal clarified; P3 wireless deprioritised

- The owner stated the core aim plainly: subvert the carrier classifying the
  connection as a tethered device, on the pilot phone and generally, and left
  the approach to the assistant's judgement.
- Assessment: the mechanism that achieves this is the L4 re-origination already
  built in P0/P1 — the phone opens every outbound socket itself
  (`Socks5Server` -> `AndroidNetworkConnector`, `UdpGatewayServer` ->
  `DatagramSocket`, DNS resolved on the phone), so no receiver packet is
  forwarded/NAT'd and the network-layer signals (TTL/hop limit, IP-stack
  fingerprint, DNS origin, no second-device DHCP) are the phone's own. A code
  read of the relay path found no place a receiver-side characteristic reaches
  the upstream socket.
- Residual, and left alone by policy (D-009): application-layer fingerprints —
  TLS/JA3, QUIC parameters, cleartext User-Agent, SNI, volume/destination
  patterns — pass through unchanged. No camouflage / DPI-evasion work.
- Decision: **P3 wireless is deprioritised.** A local Wi-Fi receiver link is
  invisible to the carrier either way and any AP mode adds a device-side signal
  with no benefit to this goal; USB/ADB stays the transport. Next is **E-011**
  (on-hardware verification of the re-origination), then the robustness pass.
- Files: `docs/THREAT_MODEL.md` (new "Carrier tethering classification"
  section), `docs/EXPERIMENTS.md` (E-011, queue reprioritised), `AGENTS.md`.
  No code change.

### 2026-08-30 — Lightweight UDP over tun2proxy udpgw (D-024)

- Completed (not yet phone-tested; folded into Android `0.1.0-p1.1` / Debian
  `0.1.0-6`):
  - tun2proxy is now built `--no-default-features --features udpgw` (the feature
    is its own default and adds no deps) and run with
    `--udpgw-server 240.0.0.1:1`. tun2proxy tunnels the udpgw stream through the
    existing SOCKS proxy with the sentinel as the CONNECT target.
  - New `app/.../relay/UdpGatewayServer.kt` + `UdpGatewayProtocol.kt`: the
    phone's `Socks5Server` recognises the sentinel CONNECT and hands the stream
    to `UdpGatewayServer`, which speaks the badvpn udpgw framing, holds one
    `DatagramSocket` per connection id bound to the selected upstream, forwards
    datagrams, and frames replies back. Reused connection ids with a new
    destination are rebuilt; idle ones self-close.
  - Network selection was extracted from `AndroidNetworkConnector` into
    `network/NetworkSelector.kt`, shared by the TCP connector and the UDP
    gateway (and it now carries the `rebind()` used by `ACTION_RECONFIGURE`).
  - `manager.py` passes `--udpgw-server`; `get_status()` reports
    `udp_supported: true`.
- Verified with: `./gradlew :app:testDebugUnitTest` (new `UdpGatewayProtocolTest`
  ×7 and `UdpGatewayServerTest` ×3 — real loopback UDP echo through a piped TCP
  stream: datagram forward + reply framing, keepalive echo, connection-id reuse
  rebuild) and 48 Linux host unit tests (`_tunnel_command` now asserts the
  sentinel is outside the routed range). **No phone test yet** — needs the
  tun2proxy rebuild and a live UDP workload (Shadow PC / QUIC).
- Files/areas: `app/.../relay/{UdpGatewayServer,UdpGatewayProtocol}.kt` (new),
  `app/.../relay/Socks5Server.kt`, `app/.../network/{NetworkSelector.kt (new),
  AndroidNetworkConnector.kt}`, `app/.../service/RelayRuntime.kt`,
  `app/src/test/.../{UdpGatewayProtocolTest,UdpGatewayServerTest}.kt` (new);
  `third_party/tun2proxy/build.sh`, `desktop/linux/teather/{constants,manager}.py`,
  `desktop/linux/tests/test_core.py`; `packaging/debian/changelog`,
  `packaging/man/teather.1`; `docs/DECISIONS.md` (D-024), `README.md`, `AGENTS.md`.
- Next: track 3 — P3 wireless (local Wi-Fi link), its own design pass.

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
