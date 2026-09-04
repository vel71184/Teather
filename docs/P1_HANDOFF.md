# P1 Linux USB Desktop validation handoff

**P1 acceptance was met (D-022, first packaged as `0.1.0-4`) and Teather is now
the owner's daily connection; the current build is Debian `0.1.0-19` / Android
`0.1.0-p1.6` (`versionCode 8`, release-signed — D-030).** The version numbers in
the VM/install procedures below are historical — substitute the current package.
`docs/PROJECT_STATUS.md` is the live resume point; this file is kept for the
acceptance-gate procedure.

P0 and E-001 are complete. The P1 Android control surface, Linux daemon/CLI/GTK
client, NetworkManager connection module, package, recovery guide, and pinned
tunnel build are implemented in the working tree (there is no privileged
helper). Do not restart P0 or rebuild the P1 scaffold.

The VM and phone steps below need the owner (see `AGENTS.md` "Safety gates").
Everything up to them — building the package, updating code and docs — does not.

## How this document is used now

P1 acceptance is behind us. This file is retained as the **re-validation
procedure** — the sequence to re-run before publishing, or on a fresh machine,
or after a change that touches the route/DNS/TUN path. It is not a live
to-do list; `docs/PROJECT_STATUS.md` is the resume point.

The record below is organized as: the phase-by-phase acceptance evidence that
was actually collected (Phases 1–3, historical), then the standing operating
model and the physical-test checklist. Version numbers in the procedures are
historical — substitute the current package (`0.1.0-19` / `0.1.0-p1.6`).

The final architecture that was accepted (D-022): NetworkManager creates and
owns `teather0` as an in-memory `tun` connection with `tun.owner` delegation, so
`tun2proxy` (spawned by `teatherd` as the desktop user) attaches directly — no
setuid-root helper, no polkit action. DNS is additive (positive, non-exclusive
`ipv4.dns-priority`), automatic failover is the default, and `_verify_additive()`
fails the connection closed if arming ever leaves the sentinel as the only
resolver. The pre-D-022 tree is on branch `archive/d021-reapply-dns-approach`
(commit `c78d45f`).

## Evidence already complete

- `env ANDROID_HOME=/tmp/android-sdk GRADLE_USER_HOME=/tmp/teather-gradle2 make
  check` passed after the 2026-08-27 correction: 92 Android tasks, 25 Linux
  tests, strict helper compilation, helper argument rejection, the helper route
  regression, and the private D-Bus smoke test.
- After isolated validation corrections, two clean patched tun2proxy builds were
  identical at SHA-256
  `ffdd4373cb41401e3f4e8b4d65f84688ed4288966d621580de303b1ca47d15bf`.
- The historical D-020 Debian package used for the accepted Phase 2/first
  physical run is SHA-256
  `77b70295a838daf5a85e0ba4a7e33a1f7109b0f049bee4775cb323a00f880804`
  (`teather_0.1.0-2_amd64.deb`). Two clean builds were byte-identical.
- Root-mapped namespace package tests passed unpack, synthetic upgrade, remove,
  and purge semantics.
- The connected phone was upgraded to versionCode 2 / `0.1.0-p1`. ADB shell
  start/status/stop, compatible attach, incompatible-setting refusal, coarse
  counter preservation, and effective ordinary-app denial passed. The temporary
  probe was uninstalled, the relay was stopped, and no ADB forward remained.
- On 2026-08-27, `assembleDebug` completed successfully and `app-debug.apk` was
  verified with `apksigner`: one Android Debug signer using APK Signature Scheme
  v2, certificate SHA-256
  `873c84175e4447884ab80929e6a40952ef1d31ee807624041abd7796c61d5ccb`.
  `aapt` confirmed package `io.github.vel71184.teather`, versionCode 2, and
  versionName `0.1.0-p1`. The APK SHA-256 is
  `8dbf92b8137533127e1a7e20e199586ccb276e995cb58ad354e8ed968a9ed586`.

## Phase 1 evidence complete — 2026-08-26

> **Superseded by D-022 (2026-08-29):** the Phase 1 and Phase 2 evidence below
> was collected against packages `0.1.0-1`/`0.1.0-2`/`0.1.0-3`, which used the
> now-deleted setuid-root helper and D-021's `Reapply` DNS. It must be re-run
> against `0.1.0-4` (helper removed, NetworkManager-owned `teather0`). The
> package-lifecycle and GUI/watcher structure is unchanged; the privileged-TUN
> and DNS portions are entirely replaced.

- The verified Debian artifact installed in a disposable Debian 12.15 amd64 GNOME
  VM with all hard dependencies. Root-owned helper, tunnel engine, and polkit
  files had modes 0755, 0755, and 0644.
- With no phone available to the VM, D-Bus activation and status, devices, and
  diagnostics reported a ready disconnected state without privilege or TUN
  creation. The optional watcher enable/disable lifecycle passed.
- The real GNOME GTK window remained usable and disconnected. Its AppIndicator
  appeared when supported; a reversible mode-000 typelib test proved the
  window-only fallback, after which the typelib was restored to 0644. Neither
  case invoked `pkexec`.
- Same-version reinstall and remove preserved the exact mode-0600 preference
  file. Purge deleted it; the verified artifact was reinstalled for Phase 2.
- Routes, IPv4 rules, resolver content, NetworkManager connections, and nftables
  rules were byte-for-byte unchanged from the private baseline; `teather0` never
  existed. The clean Phase 1 disk is the backing file for a fresh Phase 2 overlay.

Phase 1 alone did not prove the privileged TUN lifetime, Android APK/device
boundary, system-wide TCP/DNS, or P1 cleanup matrix.

## Phase 2 evidence complete — 2026-08-26

- The controlled loopback virtual-DNS/TCP path passed through the real root
  helper and patched tun2proxy. A query for the synthetic `phase2.test` name
  returned `198.18.0.0`, and a TCP request to that address produced a SOCKS5
  domain request for `phase2.test:18080` and received the controlled HTTP
  response.
- While active, `teather0` had only `192.0.2.1/32`, MTU 1500,
  `198.18.0.0/15`, and the metric-32000 default. QEMU's physical default at
  metric 100 remained selected. The packet engine ran as the desktop UID/GID
  with no supplementary groups, zero inheritable/permitted/effective/bounding/
  ambient capabilities, and `NoNewPrivs: 1`.
- SIGTERM, SIGINT, forced tunnel death, and invoking-parent death all removed
  the non-persistent interface and attached routes. Invalid input, unavailable
  proxy, unsafe tunnel mode, existing interface/address/route collisions,
  nonstandard policy rules, split defaults, and VPN-like defaults refused before
  mutation. Repeated disconnect/recover was idempotent, and ambiguous manually
  created `teather0` state was preserved rather than deleted.
- The matrix exposed and preserved three product defects before passing: helper
  parsing rejected normal typed local-table routes; policy-rule parsing required
  a literal space instead of Debian's tab; and split-default comparisons used
  incorrect fixed lengths. Regression coverage now exercises all three cases.
- The first real packet probe also exposed tun2proxy 0.8.3 ignoring its Linux
  no-packet-information argument, corrupting packets from the approved
  `IFF_NO_PI` descriptor. A second minimal audited patch now honors the existing
  argument; D-015 records the correction.
- Final routes, IPv4 rules, resolver, NetworkManager connection inventory, and
  nftables ruleset were byte-for-byte equal to the matrix baseline. `teather0`
  and tun2proxy were absent. Private evidence remains only in the disposable
  guest; it is not committed. The guest powered off cleanly.

Before Phase 3, these VM results did not prove the actual Android/ADB transport,
retained physical-host DNS after Wi-Fi is disabled, the two-hour session, or
physical cable/service failure recovery.

## Phase 3 attempt stopped at DNS design gate — 2026-08-27

- The phone's installed APK was byte-for-byte identical to the verified debug
  artifact. Version/signature matched; the temporary permission probe and old
  Android package were absent. ADB shell start/query/stop and local hashed-device
  approval passed without leaving a forward or relay.
- Installing package `0.1.0-1` did not mutate host networking, but the first
  connection failed closed because its user unit set `NoNewPrivileges=yes` and
  therefore prevented setuid-root `pkexec` from reaching PolicyKit. Package
  `0.1.0-2` sets the required active directive to `NoNewPrivileges=no`, preserves
  the remaining service sandbox, and adds regression coverage (D-020).
- With `0.1.0-2`, compatible attach passed. Active `teather0` contained only the
  approved address and routes; the physical metric-600 Wi-Fi default remained
  selected over metric 32000. `tun2proxy` ran as the desktop UID/GID with no
  supplementary groups or capabilities and `NoNewPrivs: 1`.
- NetworkManager observed the externally created TUN through an autoconnect-off
  runtime file under `/run`; Teather made no NetworkManager call or persistent
  profile. The runtime entry disappeared with the interface.
- Manually disabling Wi-Fi removed the host's only usable non-loopback IPv4
  nameserver. Teather reported `resolver-unavailable` and disconnected, as the
  safety gate requires. The owner restored Wi-Fi. The Android relay, ADB forward,
  TUN, routes, tunnel/helper processes, journal, and NetworkManager runtime entry
  were absent afterward.
- Final routes, IPv4 rules, resolver, and NetworkManager inventory exactly matched
  baseline. The nftables rule structure matched after normalizing live packet and
  byte counters; no rule changed. Raw private evidence remains under `/tmp`, not
  in the repository.

**Historical stop, now under D-022:** do not repeat Phase 3 until `0.1.0-4`
passes the phone-free Phase 2 VM matrix above. The 2026-08-27 DNS-gate failure
is the reason D-021 existed; D-022's additive DNS is designed so that disabling
the physical link no longer leaves the host with no resolver.

## Safety boundary

Run the first two phases only in a disposable Debian 12 GNOME amd64 VM with a
restorable snapshot. Do not install the package or exercise `teather0` on the
active developer host. Keep `docs/P1_RECOVERY.md` available inside the VM before
starting privileged tests.

**Operator phone gate:** keep the phone disconnected throughout Phase 1 and any
phone-free Phase 2 cases. Before any phone connection, USB passthrough, or
physical acceptance step, stop and tell the owner why the phone is needed and
what state the VM must be in. Continue only after the owner confirms that the
phone is connected. Do not infer phone availability from ADB state.

Teather must create only:

- one in-memory NetworkManager `tun` connection for `teather0` with
  `192.0.2.1/32`, MTU 1500, `198.18.0.0/15`, a metric-32000 backup default
  (present only when failover is armed), and `198.19.0.1` DNS at a positive
  non-exclusive priority;
- one dynamically allocated loopback ADB forward;
- mode-0600 per-user configuration and runtime journal files.

It must not write a persistent NetworkManager profile, edit `/etc/resolv.conf`
directly, or change firewall rules, policy rules, physical interfaces, existing
routes, or any physical link's connection or DNS. Automatic failover once the
physical link is gone is the default; Wi-Fi and Ethernet themselves are never
touched.

## Phase 1 — package, D-Bus, GUI, and watcher in the VM

1. Build `teather_0.1.0-5_amd64.deb` with
   `./packaging/scripts/build-deb.sh` (record two clean builds and confirm they
   are byte-identical). Copy it, this handoff, `docs/P1_RECOVERY.md`, and
   `docs/TEST_PLAN.md` into the VM. Verify the artifact before installing it:

   ```bash
   sha256sum teather_0.1.0-5_amd64.deb
   dpkg-deb --info teather_0.1.0-5_amd64.deb
   dpkg-deb --contents teather_0.1.0-5_amd64.deb
   ```

   The contents must NOT include `/usr/libexec/teather-helper` or
   `/usr/share/polkit-1/actions/…`.

2. Capture a private baseline outside the repository. Do not commit raw host or
   device identifiers:

   ```bash
   mkdir -m 700 "$HOME/teather-p1-evidence"
   ip -4 route show table all > "$HOME/teather-p1-evidence/routes.before"
   ip -4 rule show > "$HOME/teather-p1-evidence/rules.before"
   cat /etc/resolv.conf > "$HOME/teather-p1-evidence/resolver.before"
   nmcli --fields NAME,UUID,TYPE,DEVICE connection show > "$HOME/teather-p1-evidence/nm.before"
   sudo nft list ruleset > "$HOME/teather-p1-evidence/firewall.before"
   ```

3. Install the package with its Debian dependencies:

   ```bash
   sudo apt-get update
   sudo apt-get install ./teather_0.1.0-5_amd64.deb
   ```

   If `sudo` fails, stop and preserve its exact output.

   Confirm the packaged files and that no helper/polkit action was installed:

   ```bash
   stat -c '%U %G %a %n' /usr/lib/teather/tun2proxy
   test ! -e /usr/libexec/teather-helper && echo "no helper (expected)"
   test ! -e /usr/share/polkit-1/actions/io.github.vel71184.teather.policy && echo "no polkit action (expected)"
   grep -c NoNewPrivileges=yes /usr/lib/systemd/user/teather.service
   ```

4. With no phone connected, verify D-Bus activation and read-only behavior:

   ```bash
   teather status --json
   teather devices --json
   teather diagnose --json
   systemctl --user status teather.service --no-pager
   ```

   The commands must report no active phone without creating `teather0` or asking
   for privilege.

5. Launch `teather-gtk`. Verify the window remains usable, reports disconnected
   state, and does not request privilege until Connect is chosen. Verify the tray
   when Ayatana/AppIndicator support is available and the window-only fallback in
   an environment where that typelib is deliberately unavailable. Record how the
   fallback was created; do not remove desktop dependencies from the active host.

6. Test the optional watcher explicitly:

   ```bash
   systemctl --user enable --now teather.service
   systemctl --user is-enabled teather.service
   systemctl --user is-active teather.service
   systemctl --user disable --now teather.service
   ```

7. Exercise install, same-version reinstall or controlled synthetic upgrade,
   remove, and purge. Confirm `~/.config/teather/config.json` is mode 0600,
   holds `auto_failover`, survives remove/upgrade, and is deleted only by purge.
   Reinstall the verified artifact before Phase 2. Record exact commands and
   outcomes.

## Phase 2 (D-022) — VM results, 2026-08-29/30

Run in the disposable Debian 12 GNOME VM against the real
`NetworkManagerConnection` code, driving it from `teatherd`'s actual context (a
`systemd --user` transient service), with a controlled loopback SOCKS endpoint
and the QEMU NIC as "the physical link". **Passed:**

- **No polkit prompt.** From the user-manager context, `network-control` and
  `settings.modify.own` are authorized with no challenge (polkit's "implicit
  inactive: yes"). D-021's `pkexec`/`auth_admin_keep`/active-GNOME requirement
  is gone. (An SSH session is *not* authorized — correctly — but `teatherd` is
  not an SSH session.)
- **Mechanism.** `AddAndActivateConnection`/`…2` return `UnknownDevice` for a
  tun that does not exist yet, so the code adds the connection with
  `AddConnection2` (in-memory flag) then `ActivateConnection` — NM creates
  `teather0` on activation.
- **Additive DNS.** Armed, NIC up: `/etc/resolv.conf` = physical resolver first,
  `198.19.0.1` last.
- **Automatic failover.** `nmcli device disconnect eth0` → `resolv.conf` =
  `198.19.0.1` only, default route = `teather0` only; DNS keeps resolving
  through the sentinel (≈1 s blip during NM route teardown). Reconnecting the
  NIC restores the physical resolver/route on top.
- **Unprivileged engine.** `tun2proxy --tun teather0` (no `--setup`) attaches as
  uid 1000 with `CapEff: 0` and no supplementary groups; `teather0` carrier
  comes up; virtual DNS returns `198.18.0.0/16` addresses; a TCP connection to
  one reaches the loopback SOCKS server.
- **In-memory / teardown.** `/etc/NetworkManager/system-connections/` stays
  empty; deactivate + delete returns routes, `resolv.conf`, and the `nmcli`
  inventory to exact baseline.
- **Crash recovery.** A leaked `teather0` (handles dropped) is removed by a
  fresh instance's `recover()`; idempotent; `recover()` refuses a `teather0` it
  does not own.
- **Dormant mode.** `auto_failover` off → active connection, no default route,
  no DNS entry.

Not covered here (needs the phone): the ADB transport, the full
`manager.connect()` orchestration, real cellular upstream carrying traffic, the
two-hour session, and the package-install/GUI/watcher lifecycle against
`0.1.0-4` (Phase 1 was last run against the helper-based package).

## Phase 3 — end-to-end with the phone — 2026-08-30, passed

Done via USB passthrough of the owner's phone (Samsung `SM S266V`, Verizon LTE)
into the disposable VM: `start-dns-phase-usb.sh` adds
`-device qemu-xhci -device usb-host,vendorid=0x04e8,productid=0x6860`
(`adb kill-server` on the host first; the owner tapped "Allow USB debugging"
once). The VM has its own NAT'd `eth0` as "the physical link", so the host
connection was never at risk.

Results (package `0.1.0-4`, `teather.service` running):

- `teather device approve` + `teather connect` → `state: connected`,
  `dns_ready: true`, `failover_armed: true`, no polkit prompt. It started the
  Android relay, allocated ADB forward `tcp:45621 -> tcp:1080`, had
  NetworkManager create `teather0`, and spawned unprivileged
  `tun2proxy --tun teather0`.
- Real traffic: `curl --interface teather0 https://cloudflare.com/cdn-cgi/trace`
  → HTTP 200, world IP `203.0.113.10` (Verizon) vs `198.51.100.20` via
  `eth0`. `warp=off`.
- Additive DNS with `eth0` up: `resolv.conf` = `10.0.2.3` then `198.19.0.1`;
  ordinary traffic used `eth0`.
- Failover: `nmcli device disconnect eth0` → within 3 s `resolv.conf` =
  `198.19.0.1` only, default = `teather0`; `getent hosts example.com` →
  `198.18.0.2`; `curl https://example.com` and `https://github.com` → HTTP 200
  over cellular. Reconnect → physical resolver/route back on top, Teather still
  connected.
- Stability: ~12 min connected over cellular carrying traffic, then 18/18
  forced requests through `teather0`; teatherd RSS steady at ~25 MB, tun2proxy
  ~7.5 MB — no unbounded growth.
- `teather disconnect` → `resolv.conf`/routes/`nmcli` at exact baseline, ADB
  forward removed, Android relay stopped, `system-connections/` empty, no
  runtime journal.
- `kill -9 tun2proxy` → daemon's 3 s health poll auto-disconnected
  (`tunnel-exited`), same clean baseline. `teather recover` idempotent.
  (Superseded by D-026 / `0.1.0-11`: the same event now self-heals **and**
  auto-reconnects within ~4 s — see the 2026-08-31 work-log entry in
  `docs/PROJECT_STATUS.md`.)

Not yet done for full P1 sign-off: a literal two-hour session, the GUI/tray and
package upgrade/purge lifecycle against `0.1.0-4`, and the repo-wide P1 closeout
(then stop for the P2 discussion, D-018).

### Historical Phase 3 procedure (D-021, superseded)

One physical step: after passthrough, tap "Allow USB debugging" on the phone for
the VM's new ADB key. Confirm the phone has a working data upstream.

1. Install `teather_0.1.0-5_amd64.deb` and its deps in the VM; run the Phase 1
   package/D-Bus/GUI/watcher lifecycle checks against it (last run was against
   the helper-based package).
2. Verify the installed debug-signed APK reports versionCode 2 / `0.1.0-p1`;
   prove ADB shell start/query/stop and ordinary-app denial; repeat compatible
   attach, incompatible-setting refusal, and Linux-start ownership behaviour.
3. Approve the hashed device locally, connect via GUI or CLI with `auto_failover`
   on, and confirm the existing default + resolver stay preferred and browsing
   still uses them.
4. Confirm `/etc/resolv.conf` lists the physical resolver **first**, `198.19.0.1`
   second. Then disconnect the physical link. Verify the resolver becomes only
   `198.19.0.1`, `dns_ready` is true, and UDP + TCP DNS probes return
   `198.18.0.0/16` addresses.
5. Exercise a browser, hostname and IP-literal HTTPS, Git over HTTPS, SSH to a
   controlled endpoint, and package-metadata lookup. General UDP/QUIC is a
   documented P1 limitation, not a failure.
6. Run the two-hour session watching Android/Linux memory, CPU, counters, and
   redacted logs.
7. Exercise normal disconnect, repeated disconnect, SIGINT, SIGTERM, Android
   service stop, USB removal, daemon death, tunnel death, `teather failover
   off/on`, and link restoration. Capture before/after state each time.
8. Restore the physical link, disconnect Teather, and verify no relay service,
   ADB forward, `teather0` connection, route, resolver, or NetworkManager
   residue remains.

## Closeout

Record E-002 for system-wide TCP/DNS behavior and E-003 for cleanup/failure
restoration in `docs/EXPERIMENTS.md`. Update `docs/PROJECT_STATUS.md` with exact
commands, outcomes, and failures. Any cleanup mismatch, destination disclosure,
direct resolver edit, persistent NetworkManager change, unapproved link
mutation, competing nameserver, or DNS residue fails P1.

P1 acceptance is met and D-018's stop-for-P2-discussion happened and was
discharged (2026-08-30) — the owner then directed the focused post-P1 track in
`AGENTS.md`. General UDP shipped (D-024). IPv6, broader DNS, suspend/resume, and
WireGuard stay deferred by priority. Permanent release signing remains a separate
pre-distribution gate under D-019.
