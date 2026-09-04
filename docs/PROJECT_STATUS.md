# Project status

- **Snapshot date:** 2026-09-03
- **Lifecycle:** implementation / pre-alpha
- **State:** P1 (Linux USB Desktop) is complete and is the owner's daily
  connection. It is **feature-complete for the owner's use**; remaining work is
  the pre-public checklist (below) and optional future directions
  (`docs/ROADMAP.md`).
- **Current build:** Debian `0.1.0-21` / Android `0.1.0-p1.6` (`versionCode 8`,
  release-signed — D-030). Status-wire schema 2; every `p1.x` pairs with every
  desktop build. `docs/DECISIONS.md` has the per-decision rationale; the work
  log below has the per-session detail.
- **License:** GPL-3.0-or-later (`LICENSE`, D-010). Bundled `tun2proxy` binary
  is MIT (its upstream). The pilot phone's egress IPs have been scrubbed from
  the working tree and all git history (RFC 5737 documentation addresses).

### What runs — proven live on the dev laptop + pilot phone

- NetworkManager owns an in-memory `teather0` `tun` connection: no privileged
  helper, additive DNS, automatic failover once Wi-Fi/Ethernet is gone (D-022).
- The phone's upstream (`auto|cellular|wifi|ethernet`) switches with no gap
  (D-023). General UDP rides tun2proxy's `udpgw` stream, terminated on the phone
  with no VpnService and no second forward (D-024) — Shadow PC cloud gaming
  works.
- Teather can be the sole internet path when armed and no other link exists
  (D-025). An abnormal disconnect self-heals and auto-reconnects, with a
  persistent `~/.local/state/teather/teatherd.log` and toast notifications
  (D-026).
- The loopback SOCKS relay requires a per-run RFC 1929 secret the phone
  publishes only in its `DUMP`-protected status (D-028) — closes the "any app on
  the phone can use the relay" gap. The `.deb` bundles the matching APK and a
  GTK button installs/updates it, with a stronger prompt for security-relevant
  releases (D-029, D-031).
- Both clients follow `docs/DESIGN_LANGUAGE.md` (D-032): native per platform, no
  cross-platform toolkit; Appearance (Light / Dark / system) on both.

### Primary goal

Cellular traffic through Teather must not be classified as tethered. The
re-origination that serves it is built in (the phone terminates every receiver
connection and opens a fresh socket itself). **Operational evidence (E-012):**
on the owner's hard-stop prepaid plan, sustained daily use — including a ~4-hour
heavy session — has drawn no tether hard-stop and no carrier notice. Recorded as
observation, not proof (D-009). The controlled TTL/JA3 comparison (E-011) is
opportunistic.

### Not built / not in progress

IPv6 through the tunnel; the WireGuard endpoint (P4); Wi-Fi/Bluetooth receiver
transports (P3, deprioritised — a local receiver link is invisible to the
carrier); other platform clients (Windows/macOS/iOS); multi-client support. See
`docs/ROADMAP.md` "Possible future directions".

### Before the repo can go public

- ~~An explicit license~~ — **done: GPL-3.0-or-later (D-010).**
- ~~Scrub git history of private data~~ — **done: the pilot phone's IPs, the
  only sensitive strings in 57 commits, rewritten to documentation addresses and
  force-pushed.**
- ~~A first tagged release with the APK + `.deb`~~ — **done:
  [`v0.1.0-p1.6`](https://github.com/vel71184/Teather/releases/tag/v0.1.0-p1.6)
  (pre-release).**
- **Owner action:** flip the repo to public (Settings → General → Danger Zone),
  then enable private vulnerability reporting (Settings → Security) — it cannot
  be enabled while the repo is private. `SECURITY.md` already covers the gap.
- Not blocking public: the phone-reboot fault case and an ongoing daily-use
  soak.

### Verification

97 host unit tests + the D-Bus smoke test; 30 Android unit tests; both APKs and
the `0.1.0-21` `.deb` build. Live end to end (work log): connect, TCP on
cellular, full Wi-Fi-loss failover, UDP via udpgw, zero-gap upstream switch,
clean teardown to byte-identical host state; the D-028 relay-auth path (an
unauthenticated SOCKS connection is refused, authenticated egress on cellular);
`teather device install` keeping the app in schema lockstep.

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

D-018 (stop for explicit planning before P2) was discharged by the owner's
2026-08-30 post-P1 directive: a focused track — D-024 lightweight UDP, D-025
standalone connect, D-026 robustness, then the D-028…D-032 hardening and polish —
instead of the full P2/P4 sequence. That track is done. See the top of this file
for current state and `docs/ROADMAP.md` for what remains optional.

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

### Linux client — `desktop/linux/teather/` (Python + PyGObject, Debian `0.1.0-21`)

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
- `session_log` — each finished session (duration, bytes each way, upstream,
  end reason) appended to a capped `~/.local/state/teather/sessions.jsonl`
  (0600, D-033).
- `dbus_service` — the `io.github.vel71184.Teather1.Manager` interface
  (`GetStatus`, `ListDevices`, `Connect`, `Disconnect`, `ApproveDevice`,
  `RenameDevice`, `ForgetDevice`, `SetAutoConnect`, `SetAutoFailover`,
  `SetUpstream`, `AndroidAppState`, `InstallAndroid`, `Diagnose`,
  `SessionHistory` + `StatusChanged`/`DevicesChanged`/`MetricsChanged` signals)
  and the self-clearing toast notifications.
- `cli.py` — `teather status|devices|connect|disconnect|device
  approve|rename|forget|install|autoconnect|failover|upstream|diagnose|sessions|recover`,
  all pure D-Bus clients.
- `gui.py` — single-instance GTK3 window: device picker, connect/disconnect,
  approve/rename/forget, auto-connect + failover checkboxes, upstream combo,
  live metrics (human-readable byte units), recovery hint, and a HeaderBar menu
  (Session history, Diagnostics, Restart). AppIndicator tray when the desktop
  supports it; closing the window never disconnects.
- `config.py` — mode-0600 JSON, locally salted device-id hashes, never the raw
  serial.
- Packaging: `.deb` (`packaging/`), `systemd --user` unit with
  `ProtectSystem=strict` + `StateDirectory=teather`, D-Bus activation file, man
  pages, `RECOVERY.md.gz`, the bundled `Teather.apk`. `build-deb.sh` rebuilds
  `tun2proxy` with `--features udpgw` as needed and prefers a release-signed APK.
- 97 host unit tests (`python3 -m pytest desktop/linux/tests/test_core.py`).

### Historical P0

The `desktop/linux/teather-p0` helper and `docs/P0_HANDOFF.md` reproduce the
completed P0 experiment (SOCKS-only TCP over ADB). Superseded by P1; kept for
reference.

## Open threads (none blocking)

- **Pre-public checklist** — `SECURITY.md` reporting channel and a first tagged
  release with the APK + `.deb`. Licensing (D-010, GPL-3.0-or-later) and the
  git-history scrub of the pilot phone's IPs are done. See "Before the repo can
  go public" above.
- **E-012 follow-ups** — check per-app cellular data-usage attribution on the
  phone after a heavy session; keep logging heavy sessions and any carrier
  contact across billing cycles.
- **E-011 (opportunistic)** — the controlled TTL/JA3 comparison, when a
  reflector host reachable from the phone's cellular is available; a
  ready-to-deploy reflector can be built ahead of the host.
- **Phone-reboot fault case** — the one D-026 fault not yet exercised; plus the
  ongoing daily-use soak.
- **Bare-host auto-revert** *(optional)* — see the punch list.

`~/teather-host-evidence/` holds the host before/after network snapshots.
Generated `__pycache__`, private VM evidence, and signing keys are not
implementation artifacts and must not be staged.

## Confirmed decisions

A quick index; `docs/DECISIONS.md` has the rationale and status.

- Unrooted baseline; personal-first and source-oriented; Android is the
  long-term control plane and explicitly selects the upstream (D-001…D-004).
- Linux first, USB/ADB first; the relay is SOCKS5 `CONNECT` for TCP, not a
  custom VPN (D-003). API 37 compile / API 36 target — Android 17 local-network
  permission work deferred to a Wi-Fi milestone (D-011).
- NetworkManager owns a non-persistent, in-memory `teather0` `tun` connection
  with `tun.owner` delegation and additive DNS — no setuid helper, no custom
  polkit action (D-022, supersedes D-020/D-021). It stays a backup interface:
  Wi-Fi/Ethernet is untouched and preferred, Teather takes over automatically
  only once that link is gone, with a per-user opt-out (D-014 as amended).
- General UDP over tun2proxy's `udpgw`, terminated on the phone — no VpnService
  (D-024). Teather may be the sole path when armed with no other link (D-025).
  Abnormal disconnects self-heal and auto-reconnect (D-026).
- The loopback SOCKS relay requires RFC 1929 auth with a per-run secret the
  phone publishes only in its `DUMP`-protected status; `dumpsys` schema 2
  (D-028). The `.deb` bundles the matching APK and installs/upgrades it to keep
  the halves on one schema (D-029). Release-signed with the owner's off-repo key
  (D-030, supersedes D-019).
- Clients are native per platform against a shared spec — no cross-platform UI
  toolkit (D-032).
- D-018 (stop for explicit planning before P2) was discharged by the owner's
  2026-08-30 post-P1 directive.

## Important unknowns

- **Carrier classification/accounting is unmeasured and cannot be generalized.**
  The egress is confirmed to be the phone's own cellular link; E-012 records the
  operational evidence (no tether hard-stop on a hard-stop prepaid plan under
  sustained daily use), and the controlled TTL/JA3 comparison (E-011) is
  opportunistic. This is the owner's real daily use, not a synthetic gate.
- The userspace WireGuard endpoint (P4) is a hypothesis, not planned work.
- IPv6 through Teather is unsupported and not in progress.

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

One open item; the rest shipped (see git and the work log).

- **Bare-host auto-revert safety net** *(open, optional)*. A dead-man's-switch
  for daily-driver host use — a `systemd-run` timer armed at connect that runs a
  standalone `nmcli con down/delete teather0` revert unless a connectivity
  heartbeat keeps re-arming it. Sketched 2026-08-29, not built. Only worth it if
  the owner wants zero-babysit confidence beyond the D-026 self-heal, `teather
  disconnect`, and `docs/P1_RECOVERY.md`.
- **Shipped:** launcher icon and zero-gap upstream toggle (`0.1.0-p1.1`);
  idempotent ADB cleanup + robust journal recovery, the automatic reconciliation
  loop, and the post-standalone connectivity re-check (all folded into D-026's
  teardown model, `0.1.0-11`).

## Live-host boundary (still in force)

D-013 was satisfied by the owner-approved 2026-08-25 plan. Network behaviour
must still pass isolated tests before any live-host run, and a physical test
captures before/after routes, rules, resolver, NetworkManager, and firewall
state. **D-022 authorizes only the one in-memory `teather0` `tun` connection
through NetworkManager** — persistent profiles, direct `/etc/resolv.conf` edits,
firewall changes, policy rules, and any change to a physical link remain
forbidden.

## Work log

A short dated entry when something ships or a session ends: what changed and how
it was verified. A "next action" line is optional — add one only when you are
deliberately leaving a specific thread for later, not as a routine handoff. When
a milestone finishes, make sure the roadmap, this file, `AGENTS.md`'s "Current
priority", and the README status line agree — a milestone isn't done until they
do. When this section runs long, fold the oldest entries into the History
digest at the end (a few lines per milestone) and let git keep the detail; it
was last compressed on 2026-09-03.

### 2026-09-03 — License (GPL-3.0-or-later), history scrub, pre-public audit (D-010, `0.1.0-21`)

- **License (D-010):** the owner chose a "share and share alike" license →
  **GPL-3.0-or-later**. Added `LICENSE` (canonical FSF text), a README license
  section with a non-binding "thank-you if it makes you money" note, updated
  `packaging/debian/copyright` (Teather = GPL-3.0-or-later, `tun2proxy` = MIT),
  and `CONTRIBUTING.md` (inbound = outbound, no CLA). AGPL/MPL/Apache/MIT
  considered and rejected — see D-010.
- **History scrub:** the pilot phone's public egress IPs (four Verizon cellular
  addresses and one Wi-Fi address) were the only sensitive data found anywhere
  in 57 commits. Replaced with RFC 5737 documentation addresses (`203.0.113.x` /
  `198.51.100.x`) in the working tree **and rewritten out of all git history**
  (`git filter-branch`), then force-pushed. No serials, keys, credentials,
  tokens, phone numbers, or subscriber data were ever committed;
  `keystore.properties` never was (only the `CHANGE_ME` template).
- **Dependency audit:** `cargo audit` on the vendored `tun2proxy` `Cargo.lock` —
  **0 vulnerabilities** (3 low-severity unmaintained/yanked advisories on
  transitive crates, none reachable). Android app: no runtime deps. Python
  client: no pip deps. CI workflow: read-only permissions, no secrets, pinned
  actions.
- **SECURITY.md:** switched to "use GitHub private vulnerability reporting."
- **First release:**
  [`v0.1.0-p1.6`](https://github.com/vel71184/Teather/releases/tag/v0.1.0-p1.6)
  cut as a **pre-release** — source plus `teather_0.1.0-21_amd64.deb`,
  `Teather-0.1.0-p1.6.apk` (release-signed, `CN=Teather`), and `SHA256SUMS`.
  Publishing model (owner-directed): source + binaries.
- **Verified:** 97 host + 30 Android unit tests still pass; `0.1.0-21` deb
  built; `git log --all -S` for every sensitive string comes back empty
  post-rewrite; `origin/main` blob + message scan is clean; GitHub now detects
  the license as GPL-3.0.
- **Remaining (owner action only):** flip the repo to public, then enable
  private vulnerability reporting (Settings → Security; the API rejects it while
  the repo is private).

### 2026-09-03 — Session history; human-readable byte units (D-033, `0.1.0-20`)

- **Trigger:** the owner found the GTK raw byte counters confusing and floated a
  per-session log for showing long-soak viability.
- **Decision (D-033):** the history lives on the **daemon**, not the phone —
  `teatherd` already has the poll loop, the persistent log, and connect/
  disconnect detection, and the Android app stays a thin relay.
- **Built:** `session_log.py` (append + 100-entry cap, `sessions.jsonl`, 0600).
  `Manager` stamps a session on `connect()` and, on any `_finish_teardown`,
  writes `{started, ended, duration_s, to_internet, to_client, upstream,
  end_reason}` — byte fields are `max(0, end − start)` deltas on the phone's
  cumulative counters. New `SessionHistory` D-Bus method, `teather sessions
  [--json]`, and a "Session history" table in the GTK HeaderBar menu. GTK byte
  counters switched to KiB/MiB/GiB.
- **Android:** untouched (`0.1.0-p1.6`); Linux-only release. Status schema and
  `api_version` unchanged.
- **Verified:** 97 host unit tests (7 new — session_log cap/round-trip, a
  recorded session's byte deltas, a health-drop's `end_reason`, the GTK
  formatters and history table); `gui.py` imports headless; `0.1.0-20` deb
  built. A test-isolation gap was caught and fixed (the manager tests now pin
  the state dir into their tempdir so `sessions.jsonl` never touches the real
  `~/.local/state`). Live check after `dpkg -i` is the owner's.

### 2026-09-03 — Shared design language; GTK visual pass (D-032, `0.1.0-18`/`-19` / `0.1.0-p1.6`)

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
  sidecar `8 / 0.1.0-p1.6 / 1`, deb built. `gui.py` imports and the pill helper
  renders/escapes correctly.
- **Follow-up (`0.1.0-19`):** the owner installed `0.1.0-18` and found the
  HeaderBar menu items dead on click. Two causes, both fixed: "Restart window"
  ran `os.execv` on `os.path.realpath(sys.argv[0])`, but `sys.argv[0]` is the
  bare `teather-gtk` name under a `.desktop` launch and resolved against the
  wrong directory — and GTK swallows the exception from a signal handler, so the
  click did nothing; it now re-execs `python3 -m teather.gui`. "Diagnostics"
  wrote its result to the `detail` label, now at the bottom of a scrolled window
  and off-screen; it now shows a `Gtk.MessageDialog` with the diagnose fields.
  The "update installed" banner shares the fixed `_restart_self`. Verified: menu
  popup + item activation confirmed on the owner's Wayland session with a
  throwaway test window; 90 host tests; `0.1.0-19` deb built. Live GTK look is
  the owner's check after installing `0.1.0-19`; the Android reinstall is
  optional (cosmetic, schema unchanged).

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

## History digest (2026-08-22 → 2026-08-31)

Full per-session entries for this period were removed on 2026-09-03 to keep the
work log legible; `git log docs/PROJECT_STATUS.md` and `docs/DECISIONS.md` /
`docs/EXPERIMENTS.md` retain the detail.

- **P0 — Relay Proof (2026-08-22 → 2026-08-25).** Built the minimal Android
  project, foreground `RelayService`, explicit upstream binding, and SOCKS5
  `CONNECT`. Physical validation on a stock Samsung Android 16 phone: readiness
  and ten-request gates, then a continuous cellular-only SOCKS session that
  moved 15,334,016 bytes over 1,800 s while mostly locked, with before/after
  Linux route/rule/resolver hashes matching and clean service/forward teardown.
  Marked E-001 passed 2026-08-25.
- **P1 build-up (2026-08-26 → 2026-08-29).** Two disposable-VM phases passed
  (privileged-TUN lifetime, virtual-DNS/TCP path, cleanup matrix — which exposed
  and fixed three helper argument-parsing defects). Debug signing accepted for
  private testing (D-027-era). The first physical P1 run (2026-08-27) connected
  the bounded tunnel but failed safely when Wi-Fi removal left no usable
  resolver. D-021's `Reapply` DNS mechanism was then disproven (E-002:
  `teather0` was an externally-assumed NetworkManager connection, so `Reapply`
  never propagated the sentinel). **D-022** — NetworkManager creates and owns
  one in-memory `tun` connection with `tun.owner` delegation and additive DNS —
  was accepted and implemented as package `0.1.0-4`, deleting the setuid-root
  helper, its polkit action, and its C route parser. Per-turn documentation
  ceremony was cut the same week.
- **P1 acceptance + the owner-directed post-P1 track (2026-08-30 → 2026-08-31).**
  D-022 was validated end-to-end with the owner's phone passed through USB into
  the VM (traffic on the phone's cellular, automatic DNS/route failover on link
  loss, byte-exact teardown), then installed and run live on the laptop, and
  merged to main. **P1 acceptance was met and Teather became the owner's daily
  connection.** The owner then directed a focused track instead of the full
  P2/P4 sequence (discharging D-018): **D-023** (`teather upstream
  auto|cellular|wifi|ethernet`, zero-gap via `ACTION_RECONFIGURE`, `0.1.0-5..7`),
  **D-024** (general UDP over tun2proxy's `udpgw` stream + a phone-side
  `UdpGatewayServer` — no VpnService, no second forward; `0.1.0-6..8`; Shadow PC
  cloud gaming confirmed working), **D-025** (Teather as the sole internet path
  when armed and no other link exists, `0.1.0-9`), and **D-026**
  (abnormal-disconnect self-heal + auto-reconnect, persistent `teatherd.log`,
  self-clearing toast notifications, single-instance GTK, sole-path tracking,
  `0.1.0-11`; fault-injection tested 2026-08-31 — phone-reboot case deferred).
  The **primary goal** was clarified in this period: cellular traffic through
  Teather must not be classified as tethered; P3 wireless was deprioritised
  because it does not serve that goal. The relay concurrency ceiling was raised
  64 → 256 (`0.1.0-7`) after a full-desktop failover exhausted the old limit.

