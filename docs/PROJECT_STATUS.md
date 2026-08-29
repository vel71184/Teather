# Project status

- **Snapshot date:** 2026-08-29
- **Lifecycle:** implementation / pre-alpha
- **Active milestone:** P1 — Linux USB Desktop validation
- **Runnable build:** Android `0.1.0-p1` and Debian package `0.1.0-2` pass source,
  isolated-VM, install, control, bounded-interface, privilege-drop, and cleanup
  gates; physical P1 is stopped at a failed DNS-retention gate

This is the canonical resume point. Update it at the end of every meaningful work
session so the next session starts from evidence instead of archaeology.

> **Fresh-session gate:** On the first prompt of a new Codex conversation,
> complete the mandatory read-only context pass, recommend a reasoning level, and
> stop before implementation or live operations. The current owner-reviewed P1
> DNS design is **GPT-5.6 Sol with Ultra** work because networking, security,
> cleanup, testing, and documentation can be reviewed independently. See
> [the repository agent instructions](../AGENTS.md#fresh-codex-session-gate).
> Within the same thread, Codex must also stop before a materially new phase when
> the recommended level changes in either direction.

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
bounded desktop, Android control, privileged helper, recovery, and package
surfaces are implemented and pass host-only checks. The disposable-VM Phase 1
package, D-Bus, real GNOME GUI/tray/fallback, watcher, lifecycle, and no-mutation
gate passed on 2026-08-26. The corrected privileged-helper/TUN matrix also passed
in the disposable VM that day. D-019 accepts Gradle's debug signing for private
P1 testing and defers a permanent release identity until distribution is being
considered. The debug APK is verified. On 2026-08-27 the physical run connected
the corrected bounded tunnel but disabling Wi-Fi removed the only usable
non-loopback IPv4 nameserver. Teather failed safely and restored owned state. The
current objective is an owner-reviewed DNS design; do not repeat the physical run
or change resolver state before approval.

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

1. Keep P1 active. E-002 failed at DNS retention; E-003 gained two physical safe-
   cleanup cases but remains incomplete. Do not advance to P2.
2. The phone is not needed and may remain disconnected. Do not repeat Phase 3,
   disable Wi-Fi again, or edit resolver/NetworkManager state.
3. Review DNS design choices with the owner, including security, persistence,
   cleanup, and failure behavior. Begin with the unapproved proposal in
   `docs/ARCHITECTURE.md`: temporary per-device NetworkManager DNS plus virtual
   DNS over UDP and TCP, with no persistent profile or direct `resolv.conf` edit.
   Record a new or amended decision and obtain explicit approval before
   implementation or another physical run.
4. Preserve Debian package `0.1.0-2` and its D-020 PolicyKit correction. The
   Phase 2 VM remains powered off unless a regression requires isolated testing.

Preserve the P1 implementation and isolated-validation fixes. Generated
`__pycache__` files, private VM evidence, signing keys, and build credentials are
not implementation artifacts and must not be staged.

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
- The exact P1 helper, route, virtual-DNS, trust, D-Bus, packaging, and recovery
  architecture is approved (D-015 through D-017).
- Work must stop for explicit planning and approval after P1, before P2 (D-018).
- Private P1 device testing uses debug signing; permanent signing is deferred
  until distribution is considered (D-019).
- The user manager permits its intended fixed PolicyKit transition while the
  helper/tunnel privilege drop remains strict (D-020).

See `docs/DECISIONS.md` for rationale and status.

## Important unknowns

- Provider classification/accounting behavior is unmeasured and cannot be
  generalized from one result.
- The target Debian host does not retain a usable non-loopback IPv4 nameserver
  after Wi-Fi is disabled. The approved no-resolver-mutation design therefore
  cannot pass P1 on this host. A replacement DNS design is unresolved. UDP
  strategy and IPv6 policy remain P2 questions and are not authorized as a P1
  workaround.
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

## P1 authorization and live-test boundary

The owner-approved implementation plan on 2026-08-25 resolves D-013 and authorizes
P1 source work. It does not authorize unbounded experimentation on the active
host: helper/network behavior must pass isolated tests first, and the physical
gate must capture before/after routes, rules, resolver, NetworkManager, and
firewall state. No P1 code may alter NetworkManager, resolver configuration,
firewall, policy rules, or physical interfaces.

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

When a P# milestone completes, also perform the repository-wide transition in
the `Milestone transition protocol` section of `AGENTS.md`. A milestone is not
closed until the roadmap, experiments, this resume point, agent priority, README,
next handoff/recovery documents, and affected technical guidance agree.

```markdown
### YYYY-MM-DD — short description

- Completed:
- Verified with:
- Files/areas changed:
- Decisions made:
- Milestone transition: not applicable | pending | completed
- Risks or failures:
- Next exact action:
```

## Work log

### 2026-08-29 — add fresh-session Codex reasoning gate

- Completed: documented a mandatory first-prompt, read-only reasoning-level gate
  plus a symmetric same-thread High-to-Ultra or Ultra-to-High transition gate
  across the agent instructions, README, current P1 handoff, development guide,
  and canonical resume point.
- Verified with: exact cross-document references and scope rules distinguish
  GPT-5.6 Sol with Ultra for separable repository-wide or cross-subsystem work
  from High for focused work with an accepted design and bounded verification.
- Files/areas changed: AGENTS.md, README.md, docs/PROJECT_STATUS.md,
  docs/P1_HANDOFF.md, and docs/DEVELOPMENT.md.
- Decisions made: the current P1 DNS design review is classified as Ultra; a
  later bounded implementation must trigger reassessment and may move to High.
  The gate selects execution mode only and does not authorize implementation, device
  use, network mutation, or bypass of another approval stop.
- Milestone transition: not applicable. P1 remains active.
- Risks or failures: Codex may not be able to observe its active selector setting,
  so it must recommend the level and wait for owner confirmation rather than
  assert that the setting is active.
- Next exact action: in a new Codex conversation, run the fresh-session gate; once
  the owner confirms Ultra and prompts again, continue the owner-reviewed P1 DNS
  design discussion without reconnecting the phone or changing resolver state.

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
