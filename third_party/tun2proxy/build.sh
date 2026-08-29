#!/bin/sh
set -eu

version=v0.8.3
archive=tun2proxy-v0.8.3.tar.gz
checksum=1366ada8ffc7d1eb1956934696cfdb54d6fb6253e71061c28ae416474b2f3b5f
lock_checksum=943f4f9d7d489e93b722b1b9493e07c43aacb24d2e449b7aaba3fbfff0642e99
script_dir=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
output=${1:-"$script_dir/../../build/p1/tun2proxy"}
work=$(mktemp -d)
trap 'rm -rf -- "$work"' EXIT HUP INT TERM

curl --fail --silent --show-error --location \
  "https://github.com/tun2proxy/tun2proxy/archive/refs/tags/$version.tar.gz" \
  --output "$work/$archive"
actual=$(sha256sum "$work/$archive" | awk '{print $1}')
[ "$actual" = "$checksum" ] || {
  echo "tun2proxy source checksum mismatch" >&2
  exit 1
}

tar -xzf "$work/$archive" -C "$work"
patch -d "$work/tun2proxy-0.8.3" -p1 < "$script_dir/patches/0001-accept-tun-fd-without-tun.patch"
patch -d "$work/tun2proxy-0.8.3" -p1 < "$script_dir/patches/0002-honor-linux-packet-information-setting.patch"
patch -d "$work/tun2proxy-0.8.3" -p1 < "$script_dir/patches/0003-support-virtual-dns-over-tcp.patch"
actual_lock=$(sha256sum "$script_dir/Cargo.lock" | awk '{print $1}')
[ "$actual_lock" = "$lock_checksum" ] || {
  echo "tun2proxy checked-in dependency lock checksum mismatch" >&2
  exit 1
}
install -m 0644 "$script_dir/Cargo.lock" "$work/tun2proxy-0.8.3/Cargo.lock"
export CARGO_HOME=${CARGO_HOME:-"$work/cargo-home"}
export CARGO_TARGET_DIR="$work/target"
export RUSTFLAGS="-C link-arg=-Wl,--build-id=none -C debuginfo=0 --remap-path-prefix=$work=/usr/src/teather"
export CARGO_PROFILE_RELEASE_STRIP=symbols
cargo +1.90.0 build \
  --manifest-path "$work/tun2proxy-0.8.3/Cargo.toml" \
  --locked --release --no-default-features --bin tun2proxy-bin
binary="$work/target/release/tun2proxy-bin"
timestamps=$(LC_ALL=C grep -aoE '[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}' "$binary")
timestamp_count=$(printf '%s\n' "$timestamps" | wc -l)
timestamp_unique_count=$(printf '%s\n' "$timestamps" | sort -u | wc -l)
[ "$timestamp_count" -eq 3 ] && [ "$timestamp_unique_count" -eq 1 ] || {
  echo "unexpected tun2proxy embedded build timestamps ($timestamp_count total, $timestamp_unique_count unique)" >&2
  printf '%s\n' "$timestamps" >&2
  exit 1
}
build_timestamp=$(printf '%s\n' "$timestamps" | sed -n '1p')
BUILD_TIMESTAMP="$build_timestamp" LC_ALL=C perl -0pi -e \
  '$old = quotemeta $ENV{"BUILD_TIMESTAMP"}; s/$old/2026-07-23 00:00:00/g' "$binary"
install -D -m 0755 "$binary" "$output"
"$output" --version
