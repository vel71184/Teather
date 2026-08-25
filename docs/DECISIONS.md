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

## Adding or changing a decision

1. Append a new numbered entry; do not rewrite history to hide a discarded path.
2. State status, date, decision, rationale, and consequences.
3. If replacing an accepted decision, mark it superseded and link the new entry.
4. Update README, architecture, roadmap, and project status where affected.


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

**Status:** Accepted · **Date:** 2026-08-22

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
