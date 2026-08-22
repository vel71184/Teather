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

**Status:** Accepted  
**Date:** 2026-08-22

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

**Status:** Accepted  
**Date:** 2026-08-22

### Decision

Prioritize the owner's devices and source-build workflow. Public distribution,
app-store review, installer polish, and universal compatibility are deferred.

### Consequences

- USB debugging and ADB are acceptable prototype prerequisites.
- One Linux distribution can be supported before portable packaging.
- Architecture boundaries should still permit later publication.

## D-003 — Begin with Android SOCKS5 plus a Linux companion over ADB

**Status:** Accepted  
**Date:** 2026-08-22

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

**Status:** Accepted  
**Date:** 2026-08-22

### Decision

Android owns upstream selection, pairing approval, authorized receivers, relay
state, and session metrics. Receiver components capture traffic and transport it;
they do not become independent product controllers.

## D-005 — Separate transport from relay semantics

**Status:** Accepted  
**Date:** 2026-08-22

### Decision

ADB, local Wi-Fi, Wi-Fi Direct, AOA, Bluetooth, and existing LAN are transport
adapters around the same conceptual relay/session layer.

### Consequences

- Transport-specific assumptions must not leak into destination flow handling.
- Every new transport has independent authentication and recovery tests.

## D-006 — Evaluate a WireGuard-compatible long-term endpoint

**Status:** Proposed  
**Date:** 2026-08-22

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

**Status:** Accepted  
**Date:** 2026-08-22

### Decision

Use Kotlin for Android lifecycle, permissions, foreground service, network
selection, and eventual Compose UI.

The networking core may be a native/shared library later; this decision does not
require all packet processing to be written in Kotlin.

## D-008 — Choose the permanent networking-core language after P0

**Status:** Open  
**Date:** 2026-08-22

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

**Status:** Accepted  
**Date:** 2026-08-22

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

**Status:** Open  
**Date:** 2026-08-22

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

