# Project status

**Snapshot date:** 2026-08-22  
**Lifecycle:** planning / pre-alpha  
**Active milestone:** P0 — Android relay over USB/ADB  
**Runnable build:** none yet

This is the canonical resume point. Update it at the end of every meaningful work
session so the next session starts from evidence instead of archaeology.

## North star

An unrooted Android phone hosts an authenticated Internet relay. A receiver uses
that relay over a replaceable local transport, with Android retaining control of
upstream selection, pairing, status, and session metrics.

## Current objective

Prove the smallest vertical path:

```text
Linux browser -> local SOCKS port -> ADB forwarding -> Android relay
              -> selected Android upstream -> Internet
```

This experiment answers the first gating questions:

- Can the app reliably choose and use the desired Android upstream?
- Can traffic enter the application through ADB while cellular remains usable?
- Does the target connection behave differently from stock tethering?
- Is performance sufficient to justify system-wide routing work?

## Next concrete actions

1. Record the non-sensitive target environment in experiment E-001:
   - phone model;
   - Android version and build family;
   - Linux distribution and version;
   - desktop environment;
   - NetworkManager or other network manager;
   - ADB version;
   - provider name and relevant plan behavior, without account identifiers.
2. Create the minimum Android application and foreground relay service.
3. Bind a development SOCKS5 endpoint to the ADB-forwarded loopback path.
4. Verify one proxied TCP request from Linux through cellular.
5. Record throughput, latency, battery/thermal observations, failure behavior,
   and provider accounting observations.

## Confirmed decisions

- The baseline will not require root or bootloader modification.
- The project is personal-first and source-oriented.
- Linux is the first receiver platform.
- USB/ADB is the first development transport.
- The first relay is SOCKS5; the first receiver test is not a custom VPN.
- Android remains the long-term control plane.
- Wi-Fi and WireGuard compatibility are later milestones, not P0 requirements.

See `docs/DECISIONS.md` for rationale and status.

## Important unknowns

- Target phone, Android version, Linux environment, and provider are not yet
  recorded in the repository.
- The minimum supported Android API level is undecided.
- The permanent networking core language is undecided.
- UDP strategy for the initial SOCKS path is unproven.
- A userspace WireGuard endpoint on the phone is an architectural hypothesis, not
  an implemented feature.
- IPv6 policy is undecided and must be measured before choosing pass-through,
  translation, or intentional disablement during early milestones.
- Repository license is undecided.

## Explicitly not in progress

- Graphical desktop UI
- Polished Android onboarding
- Wi-Fi Direct
- Android Open Accessory USB
- Bluetooth
- Windows or macOS receivers
- Android or iOS receivers
- Multi-client sessions
- App-store packaging
- Carrier-specific behavior modules

## Evidence recorded so far

No Teather implementation experiments have been completed. Prior architectural
discussion is captured in the README and decision log, but it is not validation.

## Session closeout template

Replace this section's values or append a dated entry below after each session.

```markdown
### YYYY-MM-DD — short description

- Completed:
- Verified with:
- Files/areas changed:
- Decisions made:
- Risks or failures:
- Next exact action:
```

## Work log

### 2026-08-22 — repository initialized

- Completed: project intent, scope, architecture hypothesis, roadmap, decision
  log, development rules, experiment template, test plan, and threat model.
- Verified with: documentation review only; no runtime validation exists.
- Decisions made: no-root baseline and USB/ADB-first proof of concept.
- Risks or failures: all networking behavior remains untested.
- Next exact action: fill in E-001's environment and implement the minimal Android
  TCP relay.

