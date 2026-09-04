# Security policy

Teather is pre-alpha and has no supported release. Networking, routing, and
authentication behavior should be assumed incomplete until a milestone explicitly
states otherwise.

## Reporting a vulnerability

Report suspected vulnerabilities through **GitHub private vulnerability
reporting** (the "Report a vulnerability" button on the repository's Security
tab). Do not open a public issue, and do not include exploitable details,
private keys, provider data, device identifiers, or unredacted diagnostics in
one.

If private reporting is unavailable, contact the repository owner
(`vel71184` on GitHub) and wait for an acknowledged private channel before
sending details.

Useful reports include:

- Affected commit or version.
- Component and transport involved.
- Minimal reproduction using synthetic data.
- Expected and observed behavior.
- Security impact.
- Whether the issue is reachable only through ADB or through a shared network.
- A redacted log if needed.

## Particularly sensitive areas

- Authentication and receiver pairing. The loopback SOCKS relay requires a
  per-run RFC 1929 secret the phone publishes only in its `DUMP`-protected
  status (D-028); flaws in generating, comparing, or exposing that secret matter.
- Listeners exposed beyond Android loopback.
- SOCKS/tunnel/udpgw protocol parsers.
- The Android release signing key (D-030) and `keystore.properties` handling.
- The `teather.status.security` comparison (D-031): a wrong result suppresses
  the prompt that tells a user to install a security update.
- Android upstream selection and leakage.
- Linux route, DNS, firewall, and TUN cleanup.
- The NetworkManager connection scope Teather requests (it must stay limited to
  creating, activating, and deleting the one in-memory `teather0` connection).
- Private-key storage and configuration QR codes.
- Diagnostic exports and packet captures.

## Supported versions

There are currently no supported versions or releases. Security fixes should be
applied to the active development branch and documented in the project status.
