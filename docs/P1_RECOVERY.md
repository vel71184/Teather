# P1 offline Linux recovery

These commands do not require Internet access. Teather never disables or restores
Wi-Fi or Ethernet; if the phone path is gone, re-enabling the physical link
restores connectivity on its own.

Under D-022 (package `0.1.0-4`) NetworkManager owns `teather0` as an in-memory,
non-persistent `tun` connection. Normal disconnect, tunnel death, and the next
`teatherd` start all remove it. It is never written to
`/etc/NetworkManager/system-connections`.

First stop the per-user daemon and inspect exact Teather-owned state:

```bash
systemctl --user stop teather.service
nmcli --fields NAME,UUID,TYPE,DEVICE connection show | grep -i teather || echo "no teather0 connection"
ip -details link show teather0 2>/dev/null || echo "no teather0 interface"
ip -4 address show dev teather0 2>/dev/null
ip -4 route show dev teather0 2>/dev/null
adb forward --list
grep -n '198\.19\.0\.1' /etc/resolv.conf || echo "no Teather DNS sentinel"
```

If `teather0` is still present, confirm it is Teather's before removing it. It is
Teather's only if the connection id is `teather0`, the type is `tun`, and
`tun.owner` is your user id:

```bash
nmcli -f connection.id,connection.type,tun.owner connection show teather0
id -u
```

If all three match, deactivate and delete the in-memory connection:

```bash
nmcli connection down teather0
nmcli connection delete teather0
```

`teather recover` (with the phone reconnected) does exactly this plus removes the
ADB forward recorded in Teather's mode-0600 ownership journal. Never delete a
`teather0` whose `tun.owner` is not you, or one that appears in
`/etc/NetworkManager/system-connections` — that is not Teather's.

If the connection is already gone but `/etc/resolv.conf` still lists
`198.19.0.1`, ask NetworkManager to regenerate its resolver file:

```bash
nmcli general reload dns-rc
grep -n '198\.19\.0\.1' /etc/resolv.conf || echo "sentinel cleared"
```

Never edit `/etc/resolv.conf` by hand.

For a leftover ADB forward, copy the exact `tcp:PORT` entry and the correct phone
from `adb forward --list`; do not remove all forwards:

```bash
adb -s DEVICE forward --remove tcp:PORT
```

Do not save `DEVICE` in a file or support log. Finish by verifying Teather
changed nothing else:

```bash
ip -4 route show table all
ip rule show
cat /etc/resolv.conf
nmcli --fields NAME,UUID,TYPE,DEVICE connection show
sudo nft list ruleset
```

If any before/after route, rule, resolver, NetworkManager, or firewall snapshot
differs beyond the disappearance of `teather0`, its routes, and its DNS entry,
stop the P1 test and record the mismatch as a failure.
