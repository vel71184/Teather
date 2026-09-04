# Contributing

Teather is currently a personal, private, pre-alpha project. Contributions should
reduce uncertainty or advance the active milestone rather than broaden the feature
list.

## Before starting

Read `docs/PROJECT_STATUS.md` (the resume point) and `AGENTS.md` (constraints and
safety gates). `docs/DECISIONS.md` says why past technical choices were made. If a
change belongs to a later roadmap milestone, add it to the parking lot instead of
building it early.

## Good initial contributions

- Reproducible, non-sensitive experiments.
- Android foreground-service and socket-lifecycle groundwork.
- Focused SOCKS5 parsing and tests.
- ADB transport helpers with safe failure handling.
- Redacted diagnostics.
- Documentation corrections that preserve accepted decisions.
- Tests for cleanup, cancellation, and malformed input.

## Changes requiring discussion first

- Root, bootloader, hidden API, or system-app requirements.
- A new tunnel protocol or cryptographic construction.
- A new privileged Linux component.
- Carrier-specific behavior or claims.
- Cloud services, accounts, analytics, or telemetry.
- Cross-platform UI frameworks.
- Public distribution or licensing changes.

## Pull request expectations

A change should include:

- A narrow statement of the problem.
- The chosen behavior and important alternatives.
- Tests appropriate to the layer.
- Exact verification commands and results.
- Network cleanup verification if routes, DNS, TUN, or firewall state changes.
- Documentation updates for decisions, experiments, architecture, or status.
- No secrets, identifiers, private captures, or unrelated generated files.

Use clear, imperative commit subjects. Draft pull requests are welcome for
experiments, but do not describe an unverified path as supported.

## Reporting experiment results

Use the template in `docs/EXPERIMENTS.md`. Record failures and inconclusive results
as carefully as successes. Redact provider account information and device IDs.

## License

Teather is licensed **GPL-3.0-or-later** (`LICENSE`, D-010). By submitting a
contribution you agree that it is licensed under the same terms — the project
uses inbound-equals-outbound licensing and has no separate CLA. Keep existing
copyright and license notices intact.
