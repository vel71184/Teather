# P1 offline Linux recovery

These commands do not require Internet access. Restore Wi-Fi manually from the
GNOME menu before or after inspection; Teather never disables or restores it.

First stop the per-user daemon and inspect exact Teather-owned state:

```bash
systemctl --user stop teather.service
ip -details link show teather0
ip -4 address show dev teather0
ip -4 route show dev teather0
adb forward --list
```

The interface is non-persistent. Stopping the daemon/helper normally closes its
TUN descriptor and removes `teather0` with both interface-bound routes. If it is
still present, find the process holding `/dev/net/tun` before changing anything:

```bash
sudo lsof /dev/net/tun
ps -ef | grep '[t]eather\|[t]un2proxy'
```

Terminate only the identified Teather helper/tunnel process. Re-inspect the
interface and routes. Never delete an unexpected or ambiguously owned
`teather0`. If no process owns it and the ownership is certain, the exact manual
removal is:

```bash
sudo ip link delete teather0
```

Use `teather recover` with the phone reconnected to remove only the ADB forward
recorded in Teather's mode-0600 ownership journal. For manual recovery, copy the
exact `tcp:PORT` entry shown by `adb forward --list` and the correct phone from
that same line; do not remove all forwards:

```bash
adb -s DEVICE forward --remove tcp:PORT
```

Do not save `DEVICE` in a file or support log. Finish by restoring Wi-Fi manually
and verifying that Teather did not mutate other network subsystems:

```bash
ip -4 route show table all
ip rule show
cat /etc/resolv.conf
nmcli --fields NAME,UUID,TYPE,DEVICE connection show
sudo nft list ruleset
```

If any before/after route, rule, resolver, NetworkManager, or firewall snapshot
differs beyond the disappearance of `teather0` and its two routes, stop the P1
test and record the mismatch as a failure.
