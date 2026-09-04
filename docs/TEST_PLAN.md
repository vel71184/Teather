# Test plan


## Executable P0 checks

Host-only verification:

```bash
make check
```

This runs JVM protocol/integration tests, Android lint, and a debug APK build.
With an authorized phone attached, the exact device gates are:

```bash
./desktop/linux/teather-p0 all
./desktop/linux/teather-p0 soak
./desktop/linux/teather-p0 stop
./desktop/linux/teather-p0 status
```

The `soak` command keeps one rate-limited SOCKS connection open for the entire
gate; it is not a loop of short requests. The helper never changes Linux routes,
resolver configuration, or firewall state. See `docs/P0_HANDOFF.md` for redacted
environment capture and failure isolation.

Teather modifies or depends on networking state across two devices. A successful
web request is necessary but insufficient; recovery and cleanup are first-class
correctness requirements.

## Test layers

### Unit tests

- SOCKS/protocol parsing and malformed input.
- Framing boundaries, partial reads, and partial writes.
- State-machine transitions and idempotent stop.
- Timeout and cancellation behavior.
- Configuration validation.
- Byte-counter overflow and concurrency.
- Route-plan generation without applying it.
- Redaction of logs and diagnostic output.

### Component tests

- Android service lifecycle without a receiver.
- Android upstream selection with unavailable or changing networks.
- Relay connection to controlled local test endpoints.
- ADB transport setup and teardown.
- Linux TUN creation and cleanup in an isolated namespace where possible.
- DNS proxy behavior against controlled records.

### End-to-end tests

- Linux application -> Teather -> public test endpoint.
- System-wide Linux TCP through TUN.
- UDP and DNS when implemented.
- IPv4-only, dual-stack, and degraded upstream cases.
- USB removal, service termination, process crash, suspend/resume, and phone
  screen-off behavior.
- Wi-Fi link loss and unauthorized-peer rejection when P3 exists.

## P0 test matrix

| Test | Expected result |
|---|---|
| Foreground service start/stop | State and notification remain consistent |
| Ten sequential proxied requests | All complete through selected upstream |
| Two simultaneous requests | Both complete without cross-talk |
| Thirty-minute transfer | No crash or unbounded memory growth |
| Invalid SOCKS version | Connection rejected safely |
| Destination timeout | Bounded failure with useful category |
| Android service stop | Active connections close promptly |
| USB removal | Transport failure is reported; no receiver mutation remains |
| Upstream unavailable | Clear failure; no unintended fallback if selection is strict |

## P1 network restoration matrix

**2026-08-29 (D-022 implemented, `0.1.0-4`):** the mechanism-specific rows below
now describe NetworkManager owning `teather0` as an in-memory `tun` connection
and additive DNS. Failover is automatic once the physical link's route and
resolver disappear; the `auto_failover` setting can hold Teather dormant
instead. The restoration requirements (idempotent stop, signal/crash/cable
recovery, no unrelated state mutation) are unchanged.

Capture relevant Linux state before and after each test.

**2026-08-31 (D-026, `0.1.0-11`):** the "required recovery" for an *abnormal*
loss is now stronger than "fails closed with recoverable state" — `teatherd`
must detect it within a few seconds, release its owned resources to a clean
`disconnected` state (not `error`), and let auto-connect reconnect once the
phone is reachable, with no manual `teather recover`. The host side stays
strict (an unverifiable `teather0` still stops with `ambiguous-interface`).
Fault-injection tested 2026-08-31: `systemctl restart`, `kill -9 tun2proxy`,
`adb kill-server`, phone unplug/replug, Wi-Fi off/on — all self-heal and
auto-reconnect. Phone reboot still to do.

**2026-09-01 (D-028/D-029/D-030, `0.1.0-12` / `0.1.0-p1.3`):** the loopback
SOCKS relay requires RFC 1929 auth with a per-run secret; `dumpsys` schema is 2.
Live-verified on the pilot phone: an unauthenticated `--socks5-hostname` client
is refused, `teather:<secret>@…` egresses on cellular (including over the
`teather0` failover route), a schema-1 client and a schema-2 relay refuse to
pair. `teather device install` installed the release-signed APK onto an appless
phone (`action: installed`) and no-op'd on a re-run ("already current"). 80 host
+ 27 Android unit tests. The release APK is signed with the project key
(`CN=Teather`), not the debug cert.

**2026-09-03 (`0.1.0-13`):** self-heal wedge fix. After a reboot with a stale
DNS sentinel in `resolv.conf` and no `teather0` connection, a failed
auto-connect latched `_error_category = "dns-residue"`; the poll-loop reconcile
only re-ran on `"recovery-pending"`, so it went dormant and the daemon stayed in
`error` with no automatic recovery. Reconcile now self-heals on any error state,
and `recover()` clears an orphaned sentinel via a NetworkManager DNS reload
(`Reload(0x2)`). Live: `teather recover` on the running daemon unwedged it
(`state: connected`, `standalone: true`, cellular egress). 82 host unit tests
(2 new). Regression to add to the fault matrix: reboot while a sentinel is
stranded in `resolv.conf`.

**2026-09-03 (`0.1.0-14` / `0.1.0-p1.4`):** appearance setting (Follow system /
Light / Dark) on the GTK client and the phone app. No behaviour change to the
relay, routing, or the status wire (schema still 2). 84 host + 30 Android unit
tests; `assembleRelease` and `lintVitalRelease` clean. Manual check still
pending: the GTK combo and the phone spinner switching themes in a live window
(owner does this after install).

**2026-09-03 (`0.1.0-16` / `0.1.0-p1.5`, D-031):** security-version layer. The
app reports `teather.status.security` (level 1); the wire schema is unchanged
(2), so pairing is unaffected. `teatherd` exposes `android_security` and
`security_update_available` in `GetStatus`; the GTK phone-app button is
state-driven and a one-time prompt fires when the bundle is ahead on security
version. 88 host (4 new) + 30 Android unit tests; `assembleRelease` /
`lintVitalRelease` clean. Manual check pending: the button states and the
security prompt against a real phone that is a version behind.

| Failure event | Required recovery |
|---|---|
| Normal stop | Teather routes, rules, TUN, and DNS removed |
| Repeated stop | No error that prevents future start |
| SIGINT | Same restoration as normal stop |
| SIGTERM | Same restoration as normal stop |
| Forced receiver crash | Next start detects and repairs owned residue; D-026: `reconcile()` also repairs it on the running daemon |
| Android service crash | Receiver exits or waits per policy; D-026: host detects `relay-stopped` and self-heals, prompts to restart the relay |
| Cable removal | Relay route withdrawn without touching unrelated state; D-026: detected as `phone-disconnected`, auto-reconnects on replug |
| tun2proxy / ADB forward drop | D-026: detected as `tunnel-exited` / `relay-unreachable`, self-heal + auto-reconnect in ~5 s |
| Linux suspend/resume | Reconnects or fails closed with recoverable state |
| Existing VPN active | Refuses unsafe route plan or follows documented coexistence |
| Teather starts while Wi-Fi is active | Wi-Fi route and resolver stay preferred and fully working; its NetworkManager state is unchanged |
| Wi-Fi is lost with failover armed | Traffic and DNS fail over to Teather automatically; no Teather-initiated change to any physical link |
| Wi-Fi is restored | Wi-Fi route and resolver become preferred again without restarting Teather |
| Wi-Fi is lost with failover off | Teather stays dormant (no default route, no DNS) until armed |
| `teatherd` process is killed / `systemctl restart` | Shutdown releases the host side but leaves the phone relay running; next start's session check clears residue and auto-connect adopts the relay (~5 s) |
| NetworkManager missing or older than 1.42 | Refuse before any connection is created |
| NetworkManager creates `teather0` with unexpected address/routes | Parity check fails; disconnect and restore owned state |
| UDP or TCP DNS readiness fails | Never report connected; deactivate the connection |
| Armed `resolv.conf` ends up sentinel-only while a physical link is up | `_verify_additive` fails closed; disconnect |

Do not automate a destructive route test on the developer's main session until it
passes in a network namespace or disposable VM where the scenario permits.

For P1, snapshot NetworkManager connection profiles and runtime state as well as
routes, rules, DNS, and firewall state. Only the in-memory `teather0` connection
may appear while active, and `/etc/NetworkManager/system-connections/` must stay
unchanged. Test the sequence: Teather ready, physical link lost, Teather traffic
and DNS succeed automatically, physical link restored, original path preferred
again. Recovery must not depend on the ongoing Internet connection or chat
session.

P1 DNS testing must distinguish IP reachability from hostname resolution. P0
`socks5h` proves remote resolution only for explicit proxy clients; it is not
evidence that applications captured transparently by a TUN can resolve names.
Record resolver state with the physical link present, lost, restored, after
receiver crash, and after cable removal. With the physical link present, its
resolver must be listed first. A passed IP-literal request with failed hostname
lookup is a DNS failure, not a successful Teather connection.

## Executable P1 checks

**2026-08-29 (D-022 implemented, `0.1.0-4`):** the items below describe the
NetworkManager-native `tun` ownership and additive DNS mechanism.

Host-only checks cover configuration permissions (including the `auto_failover`
setting), salted device trust, ambiguous multi-device selection, manager/CLI
state transitions, typed D-Bus responses, route/rule/collision preflight,
ownership journaling, redaction, the built connection dictionary, additive-vs-
exclusive DNS, stale-connection recovery, idempotent cleanup, and the D-029
APK-lockstep logic (`android_app_state` / `install_android`). Android JVM tests
cover relay state, schema-2 status serialization, SOCKS5 RFC 1929 auth
(accept / reject / refuse-no-auth), and udpgw truncated-frame rejection.

In a network namespace or disposable Debian 12 VM, prove:

- an active local session creates and activates the in-memory `tun` connection
  with no polkit prompt;
- `teather0`, its routes, and its DNS entry exist only while the connection is
  active;
- the physical default remains preferred over the metric-32000 backup;
- `tun2proxy --tun teather0` attaches unprivileged and converts
  host queries into SOCKS domain requests;
- with failover armed, `/etc/resolv.conf` lists the physical resolver first and
  `198.19.0.1` second — never the sentinel alone while a physical link is up;
- sentinel DNS answers controlled readiness queries over both UDP and RFC 1035
  TCP, with returned mappings restricted to `198.18.0.0/16`;
- normal disconnect deactivates and deletes the connection; `SIGKILL` of
  `teatherd` leaves it and the next start's `recover()` removes it, refusing a
  `teather0` it does not own;
- `/etc/NetworkManager/system-connections/` is unchanged and no direct resolver
  edit appears;
- pre-existing interface, overlapping route/address collision, nonstandard IPv4
  policy rules, VPN/split-default ambiguity, and an invalid loopback proxy port
  all fail in `preflight` before any NetworkManager call;
- `teatherd` and `tun2proxy` run with no capabilities, no supplementary groups,
  and `NoNewPrivs: 1`;
- SIGINT, SIGTERM, daemon death, and tunnel death remove all owned state.

Package tests install, upgrade, uninstall, and purge the amd64 Debian artifact.
They verify desktop/icon/D-Bus/systemd/recovery-guide placement, that no
`/usr/libexec/teather-helper` or polkit action is installed, that the user unit
sets `NoNewPrivileges=yes`, GUI operation without AppIndicator, tray operation
when available, optional login watching, preference preservation on uninstall,
and preference removal on purge.

Release Android device tests must show that ADB shell can start, query, and stop
the protected service while an ordinary test application receives a permission
denial. They also cover attach-without-restart, incompatible manual settings, and
the rule that disconnect stops only a Linux-started relay.

The physical P1 exit captures routes, rules, resolver, NetworkManager, and
firewall before and after every failure scenario. After Wi-Fi is manually
disabled, validate that the resolver contains only `198.19.0.1`, `dns_ready`
remains true, and controlled DNS probes pass over both UDP and TCP before
browsing. Exercise browser TCP fallback, Git, SSH, package retrieval, and DNS,
then run a two-hour session while observing errors and resource use. Any cleanup
mismatch, persistent NetworkManager mutation, competing nameserver, or
destination disclosure fails the milestone.

## Compatibility workloads

Once the relevant protocol exists, test:

- HTTP/1.1 and HTTP/2
- TLS with large and small transfers
- Git fetch over HTTPS
- SSH interactive and file transfer
- Package repository metadata lookup
- DNS UDP and TCP fallback
- QUIC/HTTP/3
- A representative voice/video UDP flow
- Long-lived idle connections
- Multiple concurrent short connections

The test plan does not require logging personal destinations. Use controlled or
well-known test endpoints and record only the metrics required by the experiment.

## Performance metrics

- Goodput in each direction
- Connection setup latency
- Added round-trip latency
- CPU usage on Android and receiver
- Android memory and per-flow growth
- Battery drain over a fixed interval
- Device temperature/thermal throttling observation
- Reconnect time
- Packet/error counts where the chosen stack exposes them

Performance gates should be based on the owner's practical needs after P0. Avoid
inventing impressive-looking targets before measuring the devices.

## Security tests

- Unauthenticated connection rejection on shared transports.
- Replay or stale-pairing rejection.
- Receiver revocation.
- Malformed and oversized frame handling.
- Connection and memory limits.
- No listening on unintended interfaces.
- No private key or destination leakage in normal logs.
- Dependency vulnerability scanning once manifests exist.
- Android exported-component review.
- Confirmation that `teatherd` requests nothing from NetworkManager beyond
  creating/activating/deleting the one in-memory `teather0` connection, and that
  no new polkit action or privileged helper has been introduced.

## Provider-behavior tests

These tests record the owner's observed service behavior; they do not establish a
universal bypass claim.

Compare, when permitted:

- direct phone application traffic;
- stock USB tethering;
- stock Wi-Fi hotspot;
- Teather application relay over ADB;
- Teather application relay over local-only Wi-Fi.

Record time window, byte counts, visible provider accounting category, and any
throttling observation. Do not store provider credentials or attempt to access
non-public provider systems.

## Release/checkpoint gate

Before tagging any checkpoint:

- All automated tests for implemented behavior pass (`make check` — 88 host + 30
  Android at `0.1.0-16` / `0.1.0-p1.5`).
- Required manual recovery tests pass.
- Experiment results are committed.
- Known failures are documented rather than hidden.
- Diagnostics are reviewed for sensitive output.
- Project status and decision log match the implementation.
- A tagged release APK is signed with the project key (D-030), not the debug
  cert; the `.deb` bundles that release APK.
