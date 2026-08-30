# Decision log

This file prevents important choices from dissolving into chat history. Accepted
decisions remain authoritative until superseded by a later entry.

Statuses:

- **Accepted:** current project direction.
- **Proposed:** plausible, but requires validation or owner approval.
- **Open:** a decision is needed later; do not silently assume an answer.
- **Rejected:** considered and intentionally not selected.
- **Superseded:** replaced by a newer numbered decision.

## D-001 — Keep the baseline unrooted

**Status:** Accepted · **Date:** 2026-08-22

### Decision

Teather's baseline will not require root, an unlocked bootloader, Magisk, hidden
Android APIs, or installation as a system application.

### Rationale

The target phone must retain its normal device-integrity posture and continue to
support Google Wallet/Pay. A root-enhanced mode may be reconsidered much later,
but cannot become a dependency of the main architecture.

### Consequences

- Teather cannot transparently convert Android's local-only hotspot into a kernel
  Internet router.
- Receiver traffic must use a proxy, a thin connector, or a standard userspace
  tunnel endpoint.
- Some USB gadget and Bluetooth PAN behaviors are unavailable to the baseline.

## D-002 — Optimize for a personal project first

**Status:** Accepted · **Date:** 2026-08-22

### Decision

Prioritize the owner's devices and source-build workflow. Public distribution,
app-store review, installer polish, and universal compatibility are deferred.

### Consequences

- USB debugging and ADB are acceptable prototype prerequisites.
- One Linux distribution can be supported before portable packaging.
- Architecture boundaries should still permit later publication.

## D-003 — Begin with Android SOCKS5 plus a Linux companion over ADB

**Status:** Accepted · **Date:** 2026-08-22

### Decision

The first vertical experiment uses an Android SOCKS5 relay reached through `adb
forward`. Linux begins with an application proxy and then adds TUN/tun2socks for
system-wide traffic.

### Rationale

This is the shortest path to validating upstream selection, provider behavior,
performance, and lifecycle without conflating those risks with Wi-Fi discovery or
a new tunnel protocol.

### Consequences

- P0 is TCP-first.
- ADB transport is not treated as the universal final interface.
- The SOCKS implementation must remain replaceable.

## D-004 — Keep Android as the control plane

**Status:** Accepted · **Date:** 2026-08-22

### Decision

Android owns upstream selection, pairing approval, authorized receivers, relay
state, and session metrics. Receiver components capture traffic and transport it;
they do not become independent product controllers.

## D-005 — Separate transport from relay semantics

**Status:** Accepted · **Date:** 2026-08-22

### Decision

ADB, local Wi-Fi, Wi-Fi Direct, AOA, Bluetooth, and existing LAN are transport
adapters around the same conceptual relay/session layer.

### Consequences

- Transport-specific assumptions must not leak into destination flow handling.
- Every new transport has independent authentication and recovery tests.

## D-006 — Evaluate a WireGuard-compatible long-term endpoint

**Status:** Proposed · **Date:** 2026-08-22

### Proposal

Run a WireGuard-compatible endpoint and userspace TCP/IP flow engine inside the
Android application. Receivers use established WireGuard clients where possible.

### Why it is not accepted yet

The project has not demonstrated Android-side flow termination, mobile receiver
compatibility, performance, battery behavior, or reliable UDP handling. P4 exists
specifically to accept or reject this proposal with evidence.

### Fallback

Retain a private authenticated relay protocol and provide thin Teather receivers.

**Clarification (2026-08-29):** this proposal is a major evolutionary step for
Teather, not its final architecture. WireGuard is now the de facto standard
tunnel primitive (mainline Linux kernel since 2020, mature first-party clients
on every target platform, and the base later mesh-VPN products such as
Tailscale were built on). The value of reaching standard-client compatibility
is that it removes the need for a custom receiver per platform and *opens up*
further evolution — it is not intended to be where the project's evolution
stops. See README's "Next major evolution, not the destination" and P5-P7 in
`docs/ROADMAP.md`, both of which already assume further work follows this
milestone.

## D-007 — Use Kotlin for Android platform integration

**Status:** Accepted · **Date:** 2026-08-22

### Decision

Use Kotlin for Android lifecycle, permissions, foreground service, network
selection, and eventual Compose UI.

The networking core may be a native/shared library later; this decision does not
require all packet processing to be written in Kotlin.

## D-008 — Choose the permanent networking-core language after P0

**Status:** Open · **Date:** 2026-08-22

### Candidates

- Go, favoring userspace WireGuard and gVisor/netstack reuse.
- Rust, favoring memory safety, native receiver integration, and packaging.
- Kotlin/JVM for the smallest initial Android-only relay, with later extraction.

### Decision criteria

- Reusable, maintained TCP/UDP flow engine.
- Android build and JNI/FFI complexity.
- Cross-platform receiver value.
- Performance, memory, cancellation, and debugging quality.
- Dependency and license compatibility.

## D-009 — Do not advertise guaranteed carrier invisibility

**Status:** Accepted · **Date:** 2026-08-22

### Decision

Teather may measure whether application-relayed traffic behaves differently from
stock tethering on the owner's connection. It will not claim universal bypass,
unmetered use, or undetectability, and will not build carrier-specific stealth or
fingerprint-camouflage features into the planned baseline.

### Rationale

Carrier behavior is outside the application's control, varies by network and
plan, and changes over time. Unsupported promises would make the architecture
brittle and the documentation misleading.

**Clarification (2026-08-29):** this decision constrains *promises and
features*, not the project's actual motivation. README's "Why this exists" now
states plainly that avoiding carrier tethering classification/surcharges — by
using an on-device relay whose traffic is structurally indistinguishable from
the phone's own app traffic, rather than NAT'd/forwarded hotspot traffic — is
the real primary goal, not an incidental side effect. Earlier documentation
drafts hedged away from stating that plainly; this note and the README rewrite
correct that. D-009 itself is unchanged: no guaranteed-bypass claims, and no
purpose-built stealth/fingerprint-camouflage features beyond what the relay
architecture already provides structurally.

## D-010 — Defer licensing until before public access

**Status:** Open · **Date:** 2026-08-22

### Decision needed

Select an explicit license before making the repository public. Until then, no
license file will be added and reuse/redistribution is not granted.

### Candidates to evaluate

- GPL-3.0 for reciprocal source distribution.
- Apache-2.0 for permissive reuse with an explicit patent grant.
- MPL-2.0 for file-level reciprocity.

The choice should reflect whether future commercial reuse without contributing
changes is acceptable.

## D-024 — Carry UDP with tun2proxy's udpgw feature and a phone-side gateway

**Status:** Accepted · **Date:** 2026-08-30

### Context

The owner directed a focused post-P1 track and asked for lightweight UDP —
enough for real-time services such as Shadow PC and QUIC — while keeping the
Android app a thin relay (no `VpnService`, no packet stack). The ADB link is
TCP-only, so UDP datagrams have to be framed over a TCP stream.

### Decision

Enable tun2proxy's built-in **`udpgw`** feature (its own default; disabled by
Teather's earlier `--no-default-features` build; adds no dependencies) and run it
with `--udpgw-server 240.0.0.1:1`. tun2proxy tunnels the udpgw stream through the
existing SOCKS proxy with that sentinel as the CONNECT target. The phone's
`Socks5Server` recognises the sentinel and hands the stream to a new
`UdpGatewayServer` instead of dialing out.

`UdpGatewayServer` speaks the badvpn udpgw framing (`LEN` · `FLAGS` · `CONN_ID` ·
optional SOCKS-style address · `DATA`). Per connection id it holds one
`DatagramSocket` bound to the **selected upstream** (shared `NetworkSelector`,
same transport as TCP), forwards each datagram, and frames replies back. A
connection id that reappears with a new destination is rebuilt so a reused
tun2proxy stream cannot leak an old flow's late packets. Idle connections close
on their own.

- No second ADB forward: UDP rides the one SOCKS port.
- No new Android permission, no `VpnService`, no L3 packet handling — the app
  stays an L4 relay (SOCKS for TCP, udpgw for UDP).
- The sentinel `240.0.0.1:1` is a CONNECT target only; it is never routed.
- `198.18.0.0/15` virtual-DNS names still resolve on the phone: tun2proxy
  reverses a virtual IP to its domain and the gateway re-resolves it on the
  upstream.

### Consequences

- The Debian package must ship a tun2proxy rebuilt with `--features udpgw`
  (`third_party/tun2proxy/build.sh`); `0.1.0-6` depends on it.
- IPv6 UDP is still refused (the tun is IPv4-only). General IPv6 stays deferred.
- Oversized inbound datagrams (> ~2 KB) are dropped rather than fragmented;
  acceptable for QUIC/game/DNS traffic.
- Not gated by D-018: this is the owner-directed lightweight-UDP item, not the
  broader P2 "protocol completeness" scope, which the owner has deprioritised.
- Needs a live phone test (Shadow PC or a QUIC workload) before it is proven.

## D-023 — Let the Linux client choose the phone's upstream transport

**Status:** Accepted · **Date:** 2026-08-30

### Decision

P1 no longer hard-codes `cellular`. `teather upstream <auto|cellular|wifi|
ethernet>` (also `SetUpstream` on D-Bus and a GUI dropdown) picks which of the
phone's networks the relay binds outbound sockets to. Default stays `cellular`.

The Android app already supported all four (`UpstreamPreference`,
`AndroidNetworkConnector`); only the Linux side needed to stop hard-coding
`cellular` and to accept a non-cellular `configured_upstream` in the relay
compatibility check.

### On-the-fly switching

Changing the upstream while connected rebinds **only the phone's relay
upstream**, with no teardown of anything. `teather0`, `tun2proxy`, the routes,
the DNS, and the ADB forward are untouched — they are upstream-agnostic — and so
is the SOCKS listener. New connections use the new transport; sessions already
established stay on the transport they opened on (a live TCP socket cannot move
anyway). No client sees a gap.

This is done by `RelayService`'s `ACTION_RECONFIGURE` (versionCode 3,
`0.1.0-p1.1`): `RelayRuntime.reconfigure()` swaps the live
`AndroidNetworkConnector`'s transport preference in place instead of going
through `RelayStartPolicy`, which still refuses a silent config change on a
running relay for `ACTION_START` (D-016). The Linux client drives it with
`adb … -a …RECONFIGURE`; the app's own upstream spinner uses the same path, so
the transport can also be changed from the phone while the relay runs. A port
change or a stopped relay still falls back to a full (re)start.

Teather will not change an upstream on a relay it did not start (a manual relay
is reconfigured on the phone).

### Consequences

- Using the phone's Wi-Fi is useful when the laptop cannot join that network
  directly (device caps, captive portal already cleared on the phone) or to
  avoid cellular data when the phone has Wi-Fi.
- `auto` delegates the choice to Android's own network scoring.
- This does not add UDP, IPv6, or any protocol behaviour — it is transport
  selection on the existing TCP + virtual-DNS relay, so it is not gated by
  D-018's P2 stop.

## D-022 — NetworkManager-native `tun` ownership replaces D-021's Reapply DNS mechanism

**Status:** Accepted · **Date:** 2026-08-29 (accepted 2026-08-29 after owner
delegated the decision; supersedes D-021's mechanism and the manual-only model
in D-014)

### Problem

D-021's disposable-VM retest (see E-002) confirmed the `network-control`
polkit gate works correctly from the guest's real active GNOME session, but
found a second, independent failure: NetworkManager's `Reapply()` call on
`teather0` accepts the DNS sentinel settings and reports success, yet
`/etc/resolv.conf` never reflects them, even when held for 25 seconds and
even after a manual `Reload(DNS)` call. This reproduced identically under
both TCG and KVM acceleration, ruling out a timing/environment fluke.

The likely cause: `teather0` is an *externally-assumed* NetworkManager
connection. Teather's privileged helper creates the interface and its
address/routes with raw `ip` commands, entirely outside NetworkManager's
connection API; NetworkManager only notices the interface afterward and
auto-generates a matching connection object marked
`sys-iface-state: 'external'`. `Reapply()` on that kind of connection appears
to update the stored profile without regenerating the live `IP4Config` that
NetworkManager's DNS manager actually reads. D-021's mechanism depends on a
code path NetworkManager does not fully support for assumed devices.

### Proposal

Instead of the helper creating the interface with raw `ip` commands and
letting NetworkManager discover it after the fact, create a proper
NetworkManager `tun`-type connection *before* activation, with:

- `tun.mode=tun`, `tun.owner`/`tun.group` set to the desktop user, so the
  kernel lets that unprivileged user attach to the persistent device
  directly (no root needed for this step at all).
- `ipv4.method=manual` with the same fixed `192.0.2.1/32` address and
  `198.18.0.0/15`/default-metric-32000 routes D-021/D-015 already specify.
- `ipv4.dns-data`, `ipv4.dns-priority`, `ipv4.ignore-auto-dns` set as part of
  the *same* connection profile NetworkManager fully manages from creation,
  not bolted on afterward — the normal, supported DNS-manager path.
- The connection marked transient/unsaved (in-memory only, never written to
  `/etc/NetworkManager/system-connections`), satisfying D-014's
  non-persistence requirement.

If this works as expected, the unprivileged manager process (already proven
to hold working, active-session `network-control` authorization) would
create and activate the connection itself via NetworkManager's D-Bus API.
The only remaining privileged step would be opening the resulting
already-owned persistent TUN device and handing its fd to `tun2proxy` —
likely shrinking `teather-helper.c` substantially, since most of its current
route/rule/collision-parsing logic exists only because Teather duplicates
IP/route bookkeeping NetworkManager would otherwise own directly.

### Privilege trade-off — resolved 2026-08-29

The old custom polkit action (`io.github.vel71184.teather.configure-tunnel`)
was deliberately narrow: exactly one fixed typed command running a setuid-root
helper, matching the threat model's preference for "a minimal helper with a
fixed typed API." Relying on NetworkManager's own
`settings.modify.own`/`network-control` authorization instead is broader *in
principle* — it is not scoped to only `teather0`.

The owner delegated this decision. It was resolved in favour of the
NetworkManager-native mechanism, because "broader in principle" is narrower in
practice:

- The unprivileged `teatherd` runs as the desktop user. Holding
  `network-control` lets it do nothing it could not already do by invoking
  `nmcli`; there is no privilege *gain*, only a capability the user already
  has.
- The mechanism it replaces was a **setuid-root C helper** — a genuine
  local-root surface. Phase 2's own matrix found three argument-parsing
  defects in that 350-line helper. Removing it removes that entire class of
  bug.
- `settings.modify.own` and `network-control` both default to `yes` for an
  active local session, so the normal path needs **no** authentication prompt,
  unlike the old `pkexec` action (which also broke because `auth_admin_keep`
  grants expire mid-session — see E-002).
- It satisfies the "lightest mechanism" engineering rule: the helper, its
  polkit action, its man page, and the C route/rule/collision parser are all
  deleted. The equivalent refusal checks already exist in
  `desktop/linux/teather/preflight.py` and stay there.

The threat model is updated accordingly (`docs/THREAT_MODEL.md`,
"Privilege escalation on Linux").

### Prototype result — 2026-08-29

Prototyped in the disposable VM via `nmcli` from the real active GNOME
session (outside the repository; not yet implemented in shipped source):

```
nmcli connection add type tun ifname teather0 con-name teather0-proto \
  save no \
  tun.mode tun tun.owner 1000 tun.group 1000 tun.pi no \
  ipv4.method manual ipv4.addresses 192.0.2.1/32 \
  ipv4.dns 198.19.0.1 ipv4.dns-priority -32768 ipv4.ignore-auto-dns yes \
  ipv6.method disabled connection.autoconnect no
nmcli connection up teather0-proto
```

Result: full success on every count.

- The interface came up with exactly the specified `192.0.2.1/32` address.
- `/etc/resolv.conf` immediately read `nameserver 198.19.0.1` — **only** the
  sentinel, correctly excluding the existing DHCP nameserver — the exact
  outcome D-021's `Reapply()` mechanism could never produce.
- An unprivileged Python process (uid 1000, no capabilities) successfully
  opened `/dev/net/tun` and attached to the already-existing `teather0` via
  `TUNSETIFF`, confirming `tun.owner` delegation works for handing the
  descriptor to `tun2proxy` without a root helper.
- `save no` genuinely kept the connection in-memory only —
  `/etc/NetworkManager/system-connections/` stayed empty throughout.
- Teardown (`connection down` + `connection delete`) left the host
  byte-for-byte back to baseline: no `teather0`, `resolv.conf` back to the
  original nameserver, `nmcli connection show` back to the original two
  connections.

This confirms the root-cause hypothesis above and validates the proposed
replacement mechanism end-to-end in this environment. It does not yet cover
route configuration beyond the base address (the `198.18.0.0/15` DNS-pool
route and the metric-32000 default still need adding to the same `nmcli`
invocation, straightforward extensions of `ipv4.routes`), collision/refusal
checks equivalent to the current helper's validation matrix, or the
privileged-helper shrink itself.

### Second finding: D-021's DNS model is exclusive when it should be additive

Independent of the NM-native-tun mechanism above, re-examining the owner's
intent surfaced a mismatch with D-021 itself, not just its buggy
implementation. D-021 sets DNS priority to `-32768` (NetworkManager's
*exclusive* range — this device's DNS servers replace all others) and
`ignore-auto-dns=true`, applied as soon as `teather0` exists. D-014 requires
"the owner manually disables [Wi-Fi] ... when choosing Teather." Together,
this means: even when it worked, D-021 would make Teather's virtual DNS the
*only* resolver the instant `teather0` connects, regardless of whether
Wi-Fi is still up and still the preferred route — new DNS lookups would
resolve into Teather's virtual pool and tunnel through it even while Wi-Fi
was fine. That is a manual-switch model with a DNS side effect, not the
"Wi-Fi stays default while present, Teather is silent standby, automatic
takeover only once Wi-Fi truly disappears" model the owner actually wants
(the same relationship as two coexisting links like Ethernet and Wi-Fi,
where the OS picks the default and falls back automatically).

The fix is simpler than D-021's exclusive mechanism: use a **positive**
(non-exclusive) `ipv4.dns-priority` for Teather's sentinel — worse than
Wi-Fi's default DNS priority — and do **not** set `ignore-auto-dns`.
Prototyped and confirmed in the VM: with `ipv4.dns-priority 32767` and no
`ignore-auto-dns`, `/etc/resolv.conf` correctly listed *both* nameservers,
the primary connection's first and the Teather sentinel second:

```
# Generated by NetworkManager
nameserver 10.0.2.3
nameserver 198.19.0.1
```

This is standard multi-homed DNS behavior (the same thing that happens when
you plug in a second, lower-priority network): while the primary resolver
is reachable, the OS resolver (glibc, per `resolv.conf` nameserver order)
uses it first and real traffic stays on the primary route because
resolution returns real, directly-routable addresses. Only when the
primary nameserver becomes unreachable does resolution fall through to
Teather's sentinel, which is exactly when Teather's default route
(deliberately worse metric, per D-014/D-015 — unchanged by this proposal)
also becomes the only one left. Routing-level fallback already works this
way with no changes needed; DNS should follow the same additive,
priority-ordered model instead of forcing exclusivity.

**Resolved (2026-08-29):** default behavior is automatic failover — Teather
becomes the active path the moment Wi-Fi's route/resolver actually disappears,
with no manual toggle required to reach that point, mirroring Ethernet/Wi-Fi
failover. However, unlike a free always-on Ethernet link, the phone's upstream
may be metered cellular data, and the owner's plan can change from unlimited to
capped at any time without a code change. So automatic failover itself must be
a user-facing setting, on by default, that the owner can switch off in favor of
requiring manual confirmation before Teather becomes active. This supersedes
D-014's "the owner manually disables/restores" as the *only* model — manual
control remains available as an explicit opt-out, not the default. Wi-Fi/
Ethernet themselves are still never touched by Teather either way; only
whether Teather activates automatically once they're gone is configurable.
Not yet implemented: the setting itself, its storage location (likely
`~/.config/teather/config.json`, already mode-0600 per D-017), and how the
manager's `connect()` state machine checks it before proceeding when a
physical link disappears.

### Implemented in shipped source — 2026-08-29 (package `0.1.0-4`)

- `desktop/linux/teather/networkmanager.py` rewritten from a `Reapply` DNS
  helper into `NetworkManagerConnection`. It **adds** an in-memory `tun`
  connection with `AddConnection2` (flags `IN_MEMORY | BLOCK_AUTOCONNECT`),
  **then** `ActivateConnection` — NetworkManager creates `teather0` during
  activation. (`AddAndActivateConnection`/`…2` cannot create a tun device on
  the fly: they return `UnknownDevice`. Confirmed in the VM.) On teardown it
  deactivates and deletes the connection; the next start's `recover()` deletes
  a stale one after a SIGKILL. `AddConnection2` has no "volatile" flag, so this
  explicit delete + recover is how non-persistence is guaranteed; the
  connection is never written to `/etc/NetworkManager/system-connections`.
  `_verify_additive()` fails the connection closed if arming the sentinel ever
  leaves it as the *only* resolver while the physical link is still up.
- `desktop/linux/helper/teather-helper.c`, its route test,
  `packaging/polkit/…`, and `packaging/man/teather-helper.8` deleted. The
  packet engine is spawned directly by `teatherd` as the desktop user as
  `tun2proxy --tun teather0 …` (no `--setup`; that flag is bare and requires
  root), attaching to the `tun.owner`-delegated device.
- `packaging/systemd/teather.service` restores `NoNewPrivileges=yes` and adds
  further sandboxing; `packaging/debian/control` drops the `pkexec` dependency.
- Additive DNS: `DNS_PRIORITY` moved from `-32768` (exclusive) to `32050`
  (positive, non-exclusive) and `ignore-auto-dns` is `false`.
- Auto-failover setting (`config.auto_failover()`, default on) with
  `SetAutoFailover` on D-Bus, `teather failover on|off`, and a GTK checkbox.
  Off = the connection is created with no default route and no DNS (dormant)
  until armed.

The pre-D-022 tree remains on `archive/d021-reapply-dns-approach` (commit
`c78d45f`).

### VM validation — 2026-08-29/30 (phone-free parts pass)

Run in the disposable Debian 12 GNOME VM against the real
`NetworkManagerConnection` code, from `teatherd`'s actual context (a
`systemd --user` transient service):

- **No polkit prompt.** From the user-manager context, polkit's
  `CheckAuthorization` for `network-control` returns `(authorized=True,
  challenge=False)` — the "implicit inactive: yes" path. `settings.modify.own`
  is `yes` there too. (An SSH session is *not* authorized — correctly — but
  `teatherd` is not an SSH session.) D-021's `pkexec` / `auth_admin_keep` /
  active-GNOME-session requirement is gone.
- **Additive DNS.** Armed, with the QEMU NIC up: `/etc/resolv.conf` =
  `10.0.2.3`, `fec0::3`, `198.19.0.1` — physical first, sentinel last.
- **Automatic failover.** `nmcli device disconnect eth0` → `resolv.conf` =
  `198.19.0.1` only, default route = `teather0` only. DNS keeps resolving
  through the sentinel (a ~1 s blip during NM's route teardown, then steady).
  Reconnecting the NIC restores the physical resolver/route on top.
- **Unprivileged packet engine.** `tun2proxy --tun teather0` attaches as
  uid 1000 with `CapEff: 0000000000000000`; `teather0` carrier comes up;
  virtual DNS returns `198.18.0.0/16` addresses and a TCP connection to one
  reaches the controlled loopback SOCKS server.
- **In-memory / teardown.** `/etc/NetworkManager/system-connections/` stays
  empty; deactivate + delete returns routes, `resolv.conf`, and the `nmcli`
  inventory to exact baseline.
- **Crash recovery.** A leaked `teather0` (handles dropped, simulating SIGKILL)
  is found and removed by a fresh instance's `recover()`; idempotent.
- **Dormant mode.** `auto_failover` off → connection active but no default
  route and no DNS entry.

### End-to-end with the phone — 2026-08-30, passed

The owner's phone (Samsung `SM S266V`, Verizon LTE) was passed through into the
same VM over USB. `teather connect` ran the full path — Android relay start,
ADB forward, NetworkManager-created `teather0`, unprivileged `tun2proxy` — and
`curl --interface teather0` reached the Internet with the phone's cellular IP
(`203.0.113.10`), not the host's. With the VM's link up, ordinary traffic
used it and `resolv.conf` had the physical resolver first; disconnecting the
link failed DNS and routing over to Teather automatically (real sites returned
HTTP 200 over cellular), and reconnecting restored the physical path with
Teather still connected. ~12 minutes connected over cellular showed no memory
growth (teatherd ~25 MB steady). `teather disconnect` and a `kill -9` of
`tun2proxy` both returned the host to exact baseline and stopped the Android
relay. Full detail: `docs/P1_HANDOFF.md` "Phase 3" and the 2026-08-30
`docs/PROJECT_STATUS.md` work-log entry.

Still open for P1 sign-off: a literal two-hour session, the GUI/tray lifecycle
against `0.1.0-4`, and the repo-wide closeout.

## Adding or changing a decision

Append a numbered entry with status, date, decision, and why — don't rewrite an
old one to hide a path that was tried. When replacing an accepted decision, mark
the old one superseded and point to the new one.


## D-011 — Pin the initial Android identity and toolchain

**Status:** Accepted · **Date:** 2026-08-22

### Decision

P0 uses application ID and namespace `io.github.vel71184.teather`, minimum API
26, compile API 37, target API 36, Android Gradle plugin 9.1.1, Gradle 9.3.1, and
JDK 17. The Gradle distribution and wrapper JAR checksums are verified.

### Rationale

API 26 matches the later local-only-hotspot floor while keeping the P0 code small.
Compiling with API 37 validates against the current stable SDK. Targeting API 36
deliberately avoids conflating Android 17's new local-network permission boundary
with an ADB-to-loopback experiment; that boundary must be handled and tested when
P3 opens a Wi-Fi listener.

### Consequences

- P0 does not claim Android 17 LAN-listener readiness.
- A future target-SDK change requires device tests and a decision/status update.
- The package identity should be treated as stable; changing it produces a
  distinct installed application.

## D-012 — Permit ADB lifecycle control only in debug builds

**Status:** Superseded by D-016 · **Date:** 2026-08-22

### Decision

The main/release manifest keeps `RelayService` unexported. The debug manifest
overrides only that service lifecycle to exported so the checked-in ADB helper can
start P0 without brittle UI automation. The relay listener remains fixed to
Android loopback in every variant.

### Rationale

A personal-first ADB experiment should be reproducible from one command, but an
exported production relay service would be unnecessary attack surface.

### Consequences

- Any local app can request lifecycle actions from an installed debug build; use
  it only for development.
- Android loopback is reachable by other local apps, so no-auth SOCKS remains a
  controlled P0 experiment and must be stopped after testing.
- This exception cannot be copied into release or Wi-Fi variants.
- Receiver authentication is required before promotion beyond P0 and before any
  future non-loopback listener.

## D-013 — Require owner approval before Linux network integration

**Status:** Accepted · **Date:** 2026-08-24

### Decision

P0 must end after its relay is stopped, cleanup is verified, and its evidence is
recorded. Before any P1 implementation or live command that creates a TUN device
or changes Linux routes, policy rules, DNS, firewall state, or network services,
the owner and implementer must review the exact design and the owner must approve
proceeding. Passing P0 does not implicitly authorize P1.

### Rationale

The development conversation itself depends on the laptop's current Internet
connection. An incomplete route or DNS transition could disconnect the owner at
the same time that recovery guidance is needed. Design review and an independent
recovery path therefore precede implementation, not merely deployment.

### Consequences

- The review must identify every intended host-network mutation, tunnel-recursion
  prevention, saved-state handling, and cleanup behavior for normal stop, error,
  signal, Android service loss, and cable removal.
- The review must provide exact, local recovery commands that do not depend on
  Teather, Internet access, or access to the ongoing chat.
- P1 implementation remains a hard stop until the owner explicitly approves the
  reviewed plan. No same-session transition from a successful P0 soak is assumed.
- Live-network testing must capture before/after route, rule, DNS, and firewall
  state and treat any cleanup mismatch as a failure.

## D-014 — Present Teather as a secondary virtual Linux interface

**Status:** Accepted · **Date:** 2026-08-24

### Decision

P1's first Linux mode presents Teather as a non-persistent virtual interface,
tentatively named `teather0`, over the USB/ADB relay. Its default route has lower
preference than every existing physical default. Wi-Fi and Ethernet remain
configured and preferred while available; the owner manually disables or restores
those links when choosing Teather.

The receiver may create, update, and remove only Teather-owned TUN, route, and
scoped-DNS state. It must not issue NetworkManager write operations, create a
persistent NetworkManager profile, disable an existing connection, delete or
replace an existing default route, overwrite `/etc/resolv.conf`, rewrite another
link's DNS, or flush firewall state.

### Rationale

The initial daily need is predictable manual selection, not automatic takeover or
load balancing. If Teather fails while Wi-Fi is enabled, Wi-Fi should remain
untouched. If Teather fails after the owner disables Wi-Fi, re-enabling Wi-Fi
should restore the pre-existing path without depending on Teather cleanup.

### Consequences

- This mode is a virtual Linux network interface, not Android RNDIS/NCM or stock
  USB tethering. Stock, unrooted Android applications cannot reliably own USB
  Ethernet gadget mode.
- Connection bonding, load balancing, and multipath remain out of scope.
- TUN lifecycle must be non-persistent so process death removes the interface and
  attached routes. Any separate Teather-owned state remains journaled and
  idempotently removable.
- Read-only NetworkManager inspection is allowed for preflight and verification;
  mutation is not.
- The exact route preference and DNS mechanism remain subject to D-013 review.
  If safe scoped DNS cannot be proven on the host, P1 implementation remains
  blocked.
- A live Teather route does not prove DNS works: disabling Wi-Fi may remove its
  resolver or leave an unreachable LAN-only resolver. P0's `socks5h` behavior
  covers explicit proxy clients, not transparent system-wide resolution.
- P1 initially covers TCP plus DNS. UDP-dependent applications remain a later
  milestone and must not be described as fully supported Internet traffic.

**Resolution note (2026-08-25):** D-015 fixed the route, virtual-DNS, helper, and
resolver design and satisfied D-013 for source implementation and isolated tests.
The conditional blocker language above records the pre-approval state; it is not
the current resume status.

**DNS resolution note (2026-08-27, revised 2026-08-29):** D-021 first narrowed
the no-write prohibition to a temporary `Reapply` on `teather0`; that mechanism
was then disproven. **D-022 supersedes it:** NetworkManager creates and owns one
in-memory, non-persistent `tun` connection for `teather0`. Persistent profiles,
direct `/etc/resolv.conf` edits, and any change to a physical link's connection,
routes, or DNS remain forbidden.

**Automatic-failover note (2026-08-29):** D-022 supersedes "the owner manually
disables or restores it" as the only model. Automatic failover to Teather once
Wi-Fi's route/resolver actually disappears is now the default, user-togglable
behavior — see D-022's resolved open question. Wi-Fi/Ethernet remain untouched
by Teather in either mode; only whether Teather activates itself automatically
once they're gone is configurable.

## D-015 — Approve the bounded P1 Linux USB desktop architecture

**Status:** Accepted · **Date:** 2026-08-25

### Decision

The owner approved P1 implementation from the reviewed plan. P1 is one Debian
12/GNOME desktop client with a per-user D-Bus daemon, GTK 3 window, optional
Ayatana tray indicator, CLI, a fixed polkit-mediated helper, and pinned
`tun2proxy` 0.8.3. The helper alone opens a non-persistent TUN and installs the
two interface-bound routes described in D-014. It then permanently drops all
privilege before executing the packet engine.

The receiver uses `adb -s DEVICE forward tcp:0 tcp:1080`, journals the exact
allocated forward and Android-service ownership in a mode-0600 runtime file, and
cleans only resources proved to be its own. It never logs a raw ADB serial; saved
devices use a locally salted hash.

P1 uses tun2proxy virtual DNS and IPv4 only. It does not configure a nameserver.
Connection requires at least one usable non-loopback IPv4 resolver after the owner has
disabled Wi-Fi. If none remains, Teather disconnects without editing resolver
state and the DNS design returns to review. General UDP and IPv6 are unsupported.

### Fixed Linux mutations

- Open `/dev/net/tun` with `IFF_TUN | IFF_NO_PI`; never enable persistence.
- Create only `teather0`, address it `192.0.2.1/32`, set MTU 1500, and bring it up.
- Add `198.18.0.0/15 dev teather0` for virtual-DNS addresses.
- Add `default dev teather0 metric 32000` so existing physical defaults remain
  preferred.
- Make no NetworkManager, resolver, firewall, policy-rule, physical-interface,
  or persistent-profile changes.

**Validation correction (2026-08-26):** disposable-VM packet testing found that
tun2proxy 0.8.3 ignores its CLI's `false` packet-information setting on Linux and
unconditionally strips a four-byte PI header. That is incompatible with the
approved `IFF_NO_PI` descriptor and caused virtual DNS to time out without
leaving network residue. A second minimal pinned patch now makes the engine honor
its existing packet-information argument. The fixed mutation and privilege model
above is unchanged.

**DNS replacement note (2026-08-27):** D-021 superseded only this decision's
no-nameserver/no-NetworkManager portions after the physical resolver gate failed.

**Mechanism replacement note (2026-08-29):** D-022 supersedes the
"fixed polkit-mediated helper" and "helper alone opens a non-persistent TUN"
parts of this decision. NetworkManager now creates and owns `teather0` (address,
routes, DNS) as an in-memory `tun` connection, and `tun2proxy` attaches to the
`tun.owner`-delegated device unprivileged. There is no setuid-root helper. The
*intent* of this decision is unchanged and still authoritative: exactly
`teather0` at `192.0.2.1/32` MTU 1500, `198.18.0.0/15`, a metric-32000 backup
default (only when failover is armed), no change to any physical link, and the
same refusal conditions — now enforced in `preflight.py` instead of C.

### Refusal conditions

The helper refuses an existing `teather0`, address or overlapping virtual-DNS
route collisions, any nonstandard IPv4 policy rule, another VPN or split-default
policy that makes route preference ambiguous, an existing
default whose metric cannot remain preferred, invalid `PKEXEC_UID`, invalid
proxy ports, unexpected arguments, or an untrusted executable path. Ambiguous
pre-existing state is reported and never deleted automatically.

### Consequences

- D-013's approval gate is satisfied for source implementation and isolated
  tests. Live host-network testing still follows the physical acceptance steps
  and captures before/after state.
- Wi-Fi selection remains a manual owner action.
- Closing the inherited TUN descriptor is the primary cleanup mechanism; an
  offline recovery guide covers inspection and explicit repair.
- A single active phone is supported even though several approved phones may be
  remembered.

## D-016 — Protect release ADB control with Android's DUMP permission

**Status:** Accepted · **Date:** 2026-08-25

### Decision

The one application `io.github.vel71184.teather` exports its relay service in
release builds with `android.permission.DUMP`. Authorized ADB shell can send the
application-namespaced start and stop actions and query a versioned, machine-
readable `dumpsys` status. Ordinary applications cannot invoke the component.
The loopback SOCKS listener remains unreachable from physical interfaces.

Linux attaches to an already-running compatible relay without restarting it,
refuses incompatible manual settings, and stops Android only when its journal
records that Linux started the relay.

### Consequences

- This supersedes D-012's debug-only lifecycle exception.
- Status contains lifecycle, port, upstream choice and availability, aggregate
  counters, and coarse errors, but no destinations or device/subscriber data.
- Device tests must prove ADB shell access and ordinary-application denial for a
  release build.

## D-017 — Publish one stable Linux manager API

**Status:** Accepted · **Date:** 2026-08-25

### Decision

`teatherd` owns detection and connection state and publishes a single versioned
D-Bus manager used by both GTK and CLI clients. It is D-Bus activated by default;
an optional systemd user unit provides login watching. Methods return typed
dictionaries and include `GetStatus`, `ListDevices`, `Connect`, `Disconnect`,
`ApproveDevice`, `RenameDevice`, `ForgetDevice`, `SetAutoConnect`, and `Diagnose`.
Status, device, and metric changes are signals.

Plugging in a phone detects it only. Auto-connect is limited to an approved
device whose compatible Android relay is already running. Local confirmation is
required for first approval and ambiguous multi-device selection.

### Consequences

- Python 3.11, PyGObject, GTK 3, and Ayatana AppIndicator are the P1 desktop
  stack. The window remains usable without tray support.
- The first package targets Debian 12 amd64 and preserves per-user preferences on
  uninstall, removing them only on purge.
- Rich GUI history, broad polish, and daily-driver onboarding remain P5 work.

## D-018 — Stop for explicit planning before P2

**Status:** Accepted · **Date:** 2026-08-25

### Decision

After P1 physical acceptance and evidence recording, work stops for an explicit
P2 design discussion and approval. No research-heavy investigation or
implementation of general UDP, IPv6, broader DNS behavior, suspend/resume, or
protocol changes begins automatically.

## D-019 — Defer permanent release signing during private P1 testing

**Status:** Accepted · **Date:** 2026-08-27

### Decision

Use Gradle's automatically signed debug APK for the private P1 physical
experiment. Do not create or configure a permanent Teather release identity
until the owner is considering distribution. Before phone work, verify the debug
APK signature, versionCode 2, and versionName `0.1.0-p1`.

### Consequences

- Android still receives a signed APK; this decision defers only the permanent
  production identity.
- A later release-signed build cannot update an installation signed by the debug
  certificate. The owner accepts a clean uninstall/reinstall and possible loss of
  local application state at that transition.
- The debug certificate is insecure by design and must never be represented as a
  public-release credential.
- Release-key creation, protected storage, backup, and release-build verification
  become an explicit pre-distribution gate rather than a P1 exit criterion.

## D-020 — Permit the user manager's fixed PolicyKit launch boundary

**Status:** Superseded by D-022 · **Date:** 2026-08-27 (superseded 2026-08-29)

**Supersession note (2026-08-29):** D-022 removes the setuid-root `pkexec`
helper entirely, so the reason `teatherd` needed `NoNewPrivileges=no` is gone.
Package `0.1.0-4` restores `NoNewPrivileges=yes` and adds further sandboxing;
the regression test now asserts the opposite of what it did under D-020. The
rest of this entry is retained as history.

### Decision

The `teatherd` user unit must set `NoNewPrivileges=no` so its intended child
`pkexec /usr/libexec/teather-helper run PORT` can cross the PolicyKit boundary.
Package `0.1.0-1` incorrectly set `NoNewPrivileges=yes`; Linux therefore blocked
setuid operation before PolicyKit could authorize the fixed helper. Package
`0.1.0-2` corrects the unit and adds a regression test for the active directives.

Keep `ProtectSystem=strict`, `ProtectHome=read-only`, `PrivateTmp=yes`, and the
two narrow writable paths on the unprivileged daemon. PolicyKit still binds the
action to the root-owned helper path. The helper validates its caller and fixed
typed request, creates only the approved non-persistent state, then drops UID,
GID, groups, capabilities, and applies `NoNewPrivs: 1` before executing
`tun2proxy`.

### Consequences

- The daemon itself does not gain privilege; the desktop's normal PolicyKit
  authentication remains required for the fixed helper.
- A regression test must reject reintroducing `NoNewPrivileges=yes` while the
  architecture depends on setuid-root `pkexec`.
- Physical validation proved the packet engine runs as the desktop UID/GID with
  no supplementary groups or capabilities and `NoNewPrivs: 1`.
- The first failed launch left no TUN, route, ADB forward, or ownership journal.

## D-021 — Use temporary per-device NetworkManager DNS for P1

**Status:** Superseded by D-022 · **Date:** 2026-08-27 (superseded 2026-08-29)

### Decision

The owner approved a narrow exception to D-014/D-015's original no-write DNS
boundary. While `teather0` exists, the unprivileged manager uses NetworkManager's
active-device `Reapply` API with `PRESERVE_EXTERNAL_IP` to advertise only
`198.19.0.1`, priority `-32768`, and ignored automatic DNS. It never edits
`/etc/resolv.conf` directly, creates a persistent profile, changes another link,
or enables a global DNS plugin.

Keep `198.18.0.0/15` routed through Teather, allocate virtual mappings only from
`198.18.0.0/16`, and reserve `198.19.0.1` as the collision-free DNS sentinel.
Virtual DNS must answer both UDP and RFC 1035 TCP. Connection is not ready until
the resolver contains only the sentinel, the external address/routes are
unchanged, and both probes pass.

### Consequences

- Debian depends on NetworkManager 1.42 or newer.
- Normal cleanup restores the original applied connection before interface
  removal; next-start recovery asks NetworkManager to regenerate DNS only when a
  stale sentinel exists and no ambiguous `teather0` remains.
- Any persistence, competing nameserver, route/address change, or cleanup residue
  fails closed and fails P1.
- General UDP, IPv6, private application DoH, and automatic Wi-Fi control remain
  outside P1.

**Disproven in the disposable-VM matrix (2026-08-29):** this mechanism was
implemented as designed, but `Reapply` does not actually propagate the DNS
settings to `/etc/resolv.conf` for `teather0`'s externally-assumed connection
type. **D-022 is now Accepted and implemented (package `0.1.0-4`)**; it makes
NetworkManager create and own `teather0` from the start and uses an additive,
non-exclusive DNS priority. The D-021 implementation is preserved on branch
`archive/d021-reapply-dns-approach` (commit `c78d45f`).
