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

Capture relevant Linux state before and after each test.

| Failure event | Required recovery |
|---|---|
| Normal stop | Teather routes, rules, TUN, and DNS removed |
| Repeated stop | No error that prevents future start |
| SIGINT | Same restoration as normal stop |
| SIGTERM | Same restoration as normal stop |
| Forced receiver crash | Next start detects and repairs owned residue |
| Android service crash | Receiver exits or waits according to explicit policy |
| Cable removal | Relay route is withdrawn without deleting unrelated state |
| Linux suspend/resume | Reconnects or fails closed with recoverable state |
| Existing VPN active | Refuses unsafe route plan or follows documented coexistence |

Do not automate a destructive route test on the developer's main session until it
passes in a network namespace or disposable VM where the scenario permits.

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
- Linux privileged-helper API validation when introduced.

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

- All automated tests for implemented behavior pass.
- Required manual recovery tests pass.
- Experiment results are committed.
- Known failures are documented rather than hidden.
- Diagnostics are reviewed for sensitive output.
- Project status and decision log match the implementation.
