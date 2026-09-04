# P1 offline Linux recovery

These commands do not require Internet access. Teather never disables or restores
Wi-Fi or Ethernet; if the phone path is gone, re-enabling the physical link
restores connectivity on its own.

Under D-022 (package `0.1.0-4`) NetworkManager owns `teather0` as an in-memory,
non-persistent `tun` connection. Normal disconnect, tunnel death, and the next
`teatherd` start all remove it. It is never written to
`/etc/NetworkManager/system-connections`.

**Since D-026 (`0.1.0-11`) you rarely need any of this.** An abnormal loss of
the connection — the phone unplugged, the USB/ADB bridge dropped, tun2proxy
exited, NetworkManager dropped `teather0`, the relay stopped — is now detected
within a few seconds; `teatherd` releases its own resources and reconnects on
its own once the phone is reachable, and it clears a wedged state on its poll
loop without a manual `teather recover`. First look at the log:

```bash
tail -n 100 ~/.local/state/teather/teatherd.log
journalctl --user -u teather -n 100
```

`teather status` shows `recovery_hint` when there is a concrete step to take.
The one case that still needs a hand is a `teather0` that `teatherd` cannot
confirm it owns (`ambiguous-interface` / "needs attention" notification): try
`systemctl --user restart teather.service` first, and only if that does not
clear it, work through the manual steps below.

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

`teather recover` (with the phone reconnected) does exactly this plus releases
the ADB forward recorded in Teather's mode-0600 ownership journal — but note
that since D-026 `teatherd` already runs the same routine on every poll and on
startup, so a service restart usually suffices. Never delete a `teather0` whose
`tun.owner` is not you, or one that appears in
`/etc/NetworkManager/system-connections` — that is not Teather's.

If the connection is already gone but `/etc/resolv.conf` still lists
`198.19.0.1`, ask NetworkManager to regenerate its resolver file. Since
`0.1.0-13` `teatherd`'s own `recover()` does this automatically when the
sentinel is orphaned (no `teather0` to delete), so a service restart normally
clears it; the manual form is:

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
