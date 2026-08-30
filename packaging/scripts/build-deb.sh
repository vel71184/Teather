#!/bin/sh
set -eu

repo=$(CDPATH= cd -- "$(dirname -- "$0")/../.." && pwd)
version=0.1.0-6
source_date_epoch=1787788800
stage=$(mktemp -d)
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
root="$stage/teather_${version}_amd64"
tunnel="$repo/build/p1/tun2proxy"
package="$repo/build/p1/teather_${version}_amd64.deb"

[ "$(dpkg --print-architecture)" = amd64 ] || {
  echo "P1 packaging currently supports only an amd64 build host" >&2
  exit 1
}

# Rebuild unless a cached binary already has the udpgw feature Teather now needs
# (D-024). The build is reproducible, so a rebuild is cheap to verify.
if [ ! -x "$tunnel" ] || ! "$tunnel" --help 2>&1 | grep -q -- '--udpgw-server'; then
  rm -f "$tunnel"
  "$repo/third_party/tun2proxy/build.sh" "$tunnel"
fi

install -d "$root/DEBIAN" "$root/usr/bin" "$root/usr/lib/python3/dist-packages" \
  "$root/usr/lib/teather" "$root/usr/share/applications" \
  "$root/usr/share/icons/hicolor/scalable/apps" "$root/usr/share/dbus-1/services" \
  "$root/usr/lib/systemd/user" \
  "$root/usr/share/doc/teather" "$root/usr/share/man/man1"
install -m 0644 "$repo/packaging/debian/control" "$root/DEBIAN/control"
install -m 0755 "$repo/packaging/debian/postrm" "$root/DEBIAN/postrm"
install -d "$root/usr/lib/python3/dist-packages/teather"
for source in "$repo"/desktop/linux/teather/*.py; do
  install -m 0644 "$source" "$root/usr/lib/python3/dist-packages/teather/"
done
install -m 0755 "$repo/desktop/linux/bin/teather" "$root/usr/bin/teather"
install -m 0755 "$repo/desktop/linux/bin/teatherd" "$root/usr/bin/teatherd"
install -m 0755 "$repo/desktop/linux/bin/teather-gtk" "$root/usr/bin/teather-gtk"
install -m 0755 "$tunnel" "$root/usr/lib/teather/tun2proxy"
strip --remove-section=.comment "$root/usr/lib/teather/tun2proxy"
install -m 0644 "$repo/packaging/teather.desktop" "$root/usr/share/applications/teather.desktop"
install -m 0644 "$repo/desktop/linux/resources/icons/teather.svg" \
  "$root/usr/share/icons/hicolor/scalable/apps/teather.svg"
install -m 0644 "$repo/packaging/dbus/io.github.vel71184.Teather1.service" \
  "$root/usr/share/dbus-1/services/io.github.vel71184.Teather1.service"
install -m 0644 "$repo/packaging/systemd/teather.service" "$root/usr/lib/systemd/user/teather.service"
install -m 0644 "$repo/packaging/debian/copyright" "$root/usr/share/doc/teather/copyright"
gzip -n -9 -c "$repo/packaging/debian/changelog" > "$root/usr/share/doc/teather/changelog.Debian.gz"
gzip -n -9 -c "$repo/docs/P1_RECOVERY.md" > "$root/usr/share/doc/teather/RECOVERY.md.gz"
for manual in "$repo"/packaging/man/*.1; do
  gzip -n -9 -c "$manual" > "$root/usr/share/man/man1/$(basename "$manual").gz"
done
find "$root" -type d -exec chmod 0755 {} +
(
  cd "$root"
  find usr -type f -print0 | LC_ALL=C sort -z | xargs -0 md5sum > DEBIAN/md5sums
)
find "$root" -exec touch -h --date="@$source_date_epoch" {} +
export SOURCE_DATE_EPOCH="$source_date_epoch"
dpkg-deb --root-owner-group --build "$root" "$package"
echo "$package"
