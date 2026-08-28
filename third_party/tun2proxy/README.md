# tun2proxy build input

P1 pins upstream `tun2proxy` v0.8.3 (`e271de1`) and the GitHub tag archive
checksum in `SHA256SUMS`. The tag omits `Cargo.lock`, so the build resolves once,
checks the generated lockfile against the separately pinned checksum, and then
builds locked. It applies two audited source patches and uses Rust 1.90.0
with default features disabled so the UDP gateway binary is not included. Rust
1.90 is required because the tag's unconstrained graph now includes dependencies
whose minimum is newer than the crate's declared Rust 1.85 floor.

Upstream embeds the same wall-clock build time in three locations in release
artifacts. The build uses path remapping, omits the linker build ID and debug
symbols, verifies that exactly three identical timestamps are present, and
mechanically normalizes only that value to the v0.8.3 release date. This is
build-output normalization, not an additional source patch.

The patch fixes an upstream CLI validation defect: `--tun-fd` is parsed but was
rejected unless `--tun` was also supplied. Those flags conflict, so unpatched
0.8.3 cannot use Teather's inherited-descriptor privilege boundary.

The second patch fixes an upstream Linux descriptor mismatch: the CLI requests
no packet-information header, but 0.8.3 ignores that value and tells its TUN
wrapper to strip four bytes. Teather creates its inherited descriptor with
`IFF_NO_PI`, so the unpatched engine corrupts every IPv4 packet before parsing.
The patch honors tun2proxy's existing packet-information API argument.

Upstream project and MIT license: https://github.com/tun2proxy/tun2proxy
