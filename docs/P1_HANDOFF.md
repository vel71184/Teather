# P1 Linux USB Desktop validation handoff

This is the current execution contract. P0 and E-001 are complete. The P1 Android
control surface, Linux daemon/CLI/GTK client, privileged helper, package, recovery
guide, and pinned tunnel build are implemented in the working tree. Host-only
checks and partial Android control tests passed on 2026-08-25. Do not restart P0
or rebuild the P1 scaffold.

## Evidence already complete

- `env ANDROID_HOME=/tmp/android-sdk GRADLE_USER_HOME=/tmp/teather-gradle2 make
  check` passed after the 2026-08-27 correction: 92 Android tasks, 25 Linux
  tests, strict helper compilation, helper argument rejection, the helper route
  regression, and the private D-Bus smoke test.
- After isolated validation corrections, two clean patched tun2proxy builds were
  identical at SHA-256
  `ffdd4373cb41401e3f4e8b4d65f84688ed4288966d621580de303b1ca47d15bf`.
- The current corrected Debian package is SHA-256
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

**Stop:** do not repeat Phase 3 or alter resolver state. The current P1 DNS design
is unsupported on this host. The next action is an owner-reviewed DNS design and
explicit approval. The phone is not needed for that discussion.

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

- non-persistent `teather0` with `192.0.2.1/32`, MTU 1500;
- `198.18.0.0/15 dev teather0`;
- `default dev teather0 metric 32000`;
- one dynamically allocated loopback ADB forward;
- mode-0600 per-user configuration and runtime journal files.

It must not change NetworkManager profiles, resolver configuration, firewall
rules, policy rules, physical interfaces, existing routes, or persistent network
state. The owner alone disables or restores Wi-Fi.

## Phase 1 — package, D-Bus, GUI, and watcher in the VM

1. Copy `build/p1/teather_0.1.0-2_amd64.deb`, this handoff,
   `docs/P1_RECOVERY.md`, and `docs/TEST_PLAN.md` into the VM. Verify the artifact
   before installing it:

   ```bash
   sha256sum teather_0.1.0-2_amd64.deb
   dpkg-deb --info teather_0.1.0-2_amd64.deb
   dpkg-deb --contents teather_0.1.0-2_amd64.deb
   ```

   The SHA-256 must be
   `77b70295a838daf5a85e0ba4a7e33a1f7109b0f049bee4775cb323a00f880804`.

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
   sudo apt-get install ./teather_0.1.0-2_amd64.deb
   ```

   If `sudo` fails, stop and preserve its exact output. Do not improvise a broad
   sudo or polkit rule.

   Confirm privileged files are root-owned and not group/world-writable:

   ```bash
   stat -c '%U %G %a %n' /usr/libexec/teather-helper
   stat -c '%U %G %a %n' /usr/lib/teather/tun2proxy
   stat -c '%U %G %a %n' /usr/share/polkit-1/actions/io.github.vel71184.teather.policy
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
   survives remove/upgrade, and is deleted only by purge. Reinstall the verified
   artifact before Phase 2. Record exact commands and outcomes.

## Phase 2 — privileged helper and TUN gate in the VM

Use a controlled loopback SOCKS endpoint or pass the authorized phone through to
the disposable VM. Do not disable the VM's existing network yet.

Before every case, capture routes, rules, resolver, NetworkManager, firewall, and
`teather0` state. Prove all items in the `Executable P1 checks` section of
`docs/TEST_PLAN.md`, including:

- `teather0` and both routes exist only while the inherited TUN descriptor lives;
- the existing physical default remains preferred over metric 32000;
- virtual DNS produces SOCKS domain requests;
- interface/address/route collisions, nonstandard IPv4 rules, VPN/split-default
  ambiguity, invalid helper input, and an unsafe tunnel path fail before mutation;
- the helper drops capabilities, supplementary groups, GID, and UID before the
  packet engine handles traffic;
- SIGINT, SIGTERM, daemon death, helper death, and tunnel death remove all owned
  state;
- repeated disconnect and `teather recover` are idempotent and never delete
  ambiguous state.

After each case, verify that only `teather0` and its two routes appeared and then
disappeared. Use `docs/P1_RECOVERY.md` if cleanup is uncertain. Restore the VM
snapshot after the matrix passes.

## Phase 3 — physical P1 acceptance

**Blocked after the 2026-08-27 step-5 failure. Do not rerun this sequence until
the DNS design review is recorded and explicitly approved.**

Start this phase only after Phases 1 and 2 pass and the explicit operator phone
gate above is satisfied.

1. Build and cryptographically verify versionCode 2 / `0.1.0-p1` as a debug APK.
   Gradle's local debug certificate is accepted for this private P1 experiment
   under D-019; do not treat it as a distributable release identity. Connect one
   authorized phone through ADB. Do not record its raw serial.
2. Capture the complete Linux baseline from Phase 1 plus interface state. Confirm
   no existing VPN, split default, nonstandard IPv4 rule, or `teather0` exists.
3. Verify the installed debug-signed APK reports versionCode 2 / `0.1.0-p1`.
   Prove ADB shell start/query/stop and effective ordinary-app denial. Repeat
   compatible attach, incompatible-setting refusal, and Linux-start ownership
   behavior.
4. Approve the detected hashed device locally, connect through the GUI or CLI,
   and confirm the existing Wi-Fi/Ethernet default remains preferred. Confirm the
   Android relay and dynamic ADB forward are ready before changing Wi-Fi.
5. Manually disable Wi-Fi. Immediately verify a usable non-loopback IPv4
   nameserver remains. If none remains—or it is retained but unreachable—run
   `teather disconnect`, manually restore Wi-Fi, record a DNS failure, and return
   the design to review. Do not edit resolver configuration.
6. With the resolver gate satisfied, exercise a browser, hostname and IP-literal
   HTTPS, Git over HTTPS, SSH to a controlled endpoint, package metadata lookup,
   and DNS TCP fallback. Treat unsupported general UDP/QUIC as a documented P1
   limitation, not a success.
7. Run the two-hour session while observing Android/Linux memory, CPU, counters,
   errors, and destination-redacted logs.
8. Independently exercise normal disconnect, repeated disconnect, SIGINT,
   SIGTERM, Android service stop, USB removal, daemon death, helper/tunnel death,
   and manual Wi-Fi restoration. Capture before/after state for every case.
9. Restore Wi-Fi manually, disconnect Teather, and verify no relay service, ADB
   forward, `teather0`, route, resolver, NetworkManager, policy-rule, or firewall
   residue remains.

## Closeout

Record E-002 for system-wide TCP/DNS behavior and E-003 for cleanup/failure
restoration in `docs/EXPERIMENTS.md`. Update `docs/PROJECT_STATUS.md` with exact
commands, outcomes, failures, and the next action. Any cleanup mismatch,
destination disclosure, resolver mutation, or NetworkManager mutation fails P1.

After P1 acceptance, stop. D-018 requires explicit P2 design discussion and owner
approval before general UDP, IPv6, broader DNS, suspend/resume, or protocol work.
Permanent release signing remains a separate pre-distribution gate under D-019.
