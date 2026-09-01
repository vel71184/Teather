"""NetworkManager-native `teather0` ownership (D-022).

D-021 created `teather0` with raw `ip` commands in a privileged helper and then
asked NetworkManager to reapply DNS onto the resulting *externally-assumed*
connection. That reapply never propagated to `/etc/resolv.conf` (see E-002), so
D-022 makes NetworkManager create and own the interface from the start:

* an in-memory connection of type ``tun`` added with ``AddConnection2``'s
  in-memory flag — never written to ``/etc/NetworkManager/system-connections``,
  gone on a NetworkManager restart, and deleted explicitly on teardown (and by
  the next start's ``recover()`` after a SIGKILL) — satisfying D-014's
  non-persistence requirement;
* ``tun.owner``/``tun.group`` delegation so the unprivileged ``tun2proxy``
  process opens the device directly — no root helper, no ``pkexec``;
* additive, non-exclusive DNS: a *positive* ``ipv4.dns-priority`` and
  ``ignore-auto-dns=false`` so the physical link's resolver stays first in
  ``resolv.conf`` while it is present. Teather's sentinel is only consulted once
  the physical resolver is gone — the same automatic fallback the routing layer
  already does. This is the specific behaviour that keeps working Wi-Fi working.

Creating and activating an in-memory connection from an active local session
uses NetworkManager's ``settings.modify.own`` and ``network-control`` polkit
actions, both of which default to ``yes`` for such a session, so no additional
authentication prompt is expected.
"""

from __future__ import annotations

import ipaddress
import logging
import os
import time
from pathlib import Path
from typing import Protocol

from .constants import (
    CONNECTION_ID,
    DNS_PRIORITY,
    DNS_SENTINEL,
    INTERFACE_ADDRESS,
    INTERFACE_NAME,
    ROUTE_METRIC,
    TUN_MODE_TUN,
    VIRTUAL_DNS_ROUTE,
)
from .errors import TeatherError

log = logging.getLogger(__name__)

NETWORKMANAGER_BUS = "org.freedesktop.NetworkManager"
NETWORKMANAGER_PATH = "/org/freedesktop/NetworkManager"
NETWORKMANAGER_INTERFACE = "org.freedesktop.NetworkManager"
SETTINGS_PATH = "/org/freedesktop/NetworkManager/Settings"
SETTINGS_INTERFACE = "org.freedesktop.NetworkManager.Settings"
SETTINGS_CONNECTION_INTERFACE = "org.freedesktop.NetworkManager.Settings.Connection"
DEVICE_INTERFACE = "org.freedesktop.NetworkManager.Device"
ACTIVE_CONNECTION_INTERFACE = "org.freedesktop.NetworkManager.Connection.Active"
PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"

# NMActiveConnectionState
STATE_ACTIVATING = 1
STATE_ACTIVATED = 2

# NMSettingsAddConnection2Flags: in-memory (never written to disk) + do not
# autoconnect. AddConnection2 has no "volatile" flag, so teardown deletes the
# connection explicitly and next-start recover() removes a stale one.
ADD2_IN_MEMORY = 0x2
ADD2_BLOCK_AUTOCONNECT = 0x20

MINIMUM_VERSION = (1, 42)


class NetworkManagerTransport(Protocol):
    def version(self) -> str: ...

    def add_connection(self, connection: dict) -> str: ...

    def activate_connection(self, settings_path: str) -> str: ...

    def active_state(self, active_path: str) -> int: ...

    def device_path(self, interface: str) -> str: ...

    def device_active_connection(self, device_path: str) -> str: ...

    def active_connection_settings(self, active_path: str) -> str: ...

    def list_connections(self) -> list[str]: ...

    def connection_settings(self, settings_path: str) -> dict: ...

    def deactivate(self, active_path: str) -> None: ...

    def delete_connection(self, settings_path: str) -> None: ...

    def check_connectivity(self) -> int: ...


def _plain(value):
    """Recursively unpack a GLib.Variant tree to plain Python values."""
    try:
        from gi.repository import GLib
    except Exception:  # pragma: no cover - exercised only with PyGObject present
        GLib = None
    if GLib is not None and isinstance(value, GLib.Variant):
        return _plain(value.unpack())
    if isinstance(value, dict):
        return {key: _plain(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_plain(item) for item in value]
    return value


class GioNetworkManagerTransport:
    def __init__(self, timeout_ms: int = 5_000):
        self.timeout_ms = timeout_ms
        self._bus = None

    @staticmethod
    def _gi():
        import gi

        gi.require_version("Gio", "2.0")
        from gi.repository import Gio, GLib

        return Gio, GLib

    def _connection(self):
        if self._bus is None:
            Gio, _GLib = self._gi()
            self._bus = Gio.bus_get_sync(Gio.BusType.SYSTEM, None)
        return self._bus

    def _call(self, path: str, interface: str, method: str, parameters, reply_type: str):
        Gio, GLib = self._gi()
        try:
            return self._connection().call_sync(
                NETWORKMANAGER_BUS,
                path,
                interface,
                method,
                parameters,
                GLib.VariantType.new(reply_type),
                Gio.DBusCallFlags.NONE,
                self.timeout_ms,
                None,
            )
        except Exception as error:
            raise TeatherError(
                "networkmanager-unavailable",
                f"NetworkManager request {method} failed: {type(error).__name__}",
            ) from error

    def _get_property(self, path: str, interface: str, name: str):
        _Gio, GLib = self._gi()
        reply = self._call(
            path,
            PROPERTIES_INTERFACE,
            "Get",
            GLib.Variant("(ss)", (interface, name)),
            "(v)",
        )
        return reply.get_child_value(0).get_variant()

    def version(self) -> str:
        return self._get_property(NETWORKMANAGER_PATH, NETWORKMANAGER_INTERFACE, "Version").get_string()

    def add_connection(self, connection: dict) -> str:
        _Gio, GLib = self._gi()
        reply = self._call(
            SETTINGS_PATH,
            SETTINGS_INTERFACE,
            "AddConnection2",
            GLib.Variant(
                "(a{sa{sv}}ua{sv})",
                (connection, ADD2_IN_MEMORY | ADD2_BLOCK_AUTOCONNECT, {}),
            ),
            "(oa{sv})",
        )
        return reply.get_child_value(0).get_string()

    def activate_connection(self, settings_path: str) -> str:
        _Gio, GLib = self._gi()
        reply = self._call(
            NETWORKMANAGER_PATH,
            NETWORKMANAGER_INTERFACE,
            "ActivateConnection",
            GLib.Variant("(ooo)", (settings_path, "/", "/")),
            "(o)",
        )
        return reply.get_child_value(0).get_string()

    def active_state(self, active_path: str) -> int:
        return self._get_property(active_path, ACTIVE_CONNECTION_INTERFACE, "State").get_uint32()

    def device_path(self, interface: str) -> str:
        _Gio, GLib = self._gi()
        reply = self._call(
            NETWORKMANAGER_PATH,
            NETWORKMANAGER_INTERFACE,
            "GetDeviceByIpIface",
            GLib.Variant("(s)", (interface,)),
            "(o)",
        )
        return reply.get_child_value(0).get_string()

    def device_active_connection(self, device_path: str) -> str:
        return self._get_property(device_path, DEVICE_INTERFACE, "ActiveConnection").get_string()

    def active_connection_settings(self, active_path: str) -> str:
        return self._get_property(active_path, ACTIVE_CONNECTION_INTERFACE, "Connection").get_string()

    def list_connections(self) -> list[str]:
        _Gio, GLib = self._gi()
        reply = self._call(
            SETTINGS_PATH,
            SETTINGS_INTERFACE,
            "ListConnections",
            None,
            "(ao)",
        )
        return [str(path) for path in reply.get_child_value(0).unpack()]

    def connection_settings(self, settings_path: str) -> dict:
        _Gio, GLib = self._gi()
        reply = self._call(
            settings_path,
            SETTINGS_CONNECTION_INTERFACE,
            "GetSettings",
            None,
            "(a{sa{sv}})",
        )
        return _plain(reply.get_child_value(0))

    def deactivate(self, active_path: str) -> None:
        _Gio, GLib = self._gi()
        self._call(
            NETWORKMANAGER_PATH,
            NETWORKMANAGER_INTERFACE,
            "DeactivateConnection",
            GLib.Variant("(o)", (active_path,)),
            "()",
        )

    def check_connectivity(self) -> int:
        reply = self._call(
            NETWORKMANAGER_PATH,
            NETWORKMANAGER_INTERFACE,
            "CheckConnectivity",
            None,
            "(u)",
        )
        return int(reply.get_child_value(0).get_uint32())

    def delete_connection(self, settings_path: str) -> None:
        self._call(settings_path, SETTINGS_CONNECTION_INTERFACE, "Delete", None, "()")


class NetworkManagerConnection:
    """Owns the lifetime of the in-memory `teather0` NetworkManager connection."""

    def __init__(
        self,
        resolver_path: Path = Path("/etc/resolv.conf"),
        interface_path: Path = Path(f"/sys/class/net/{INTERFACE_NAME}"),
        transport: NetworkManagerTransport | None = None,
        timeout: float = 8.0,
    ):
        self.resolver_path = resolver_path
        self.interface_path = interface_path
        self.transport = transport or GioNetworkManagerTransport()
        self.timeout = timeout
        self._settings_path = ""
        self._active_path = ""
        self._armed = False
        self._baseline_nameservers: list[str] = []

    # -- version -----------------------------------------------------------

    @staticmethod
    def _version_tuple(value: str) -> tuple[int, int]:
        try:
            fields = value.split(".")
            return int(fields[0]), int(fields[1])
        except (ValueError, IndexError) as error:
            raise TeatherError("networkmanager-version", "Cannot parse the NetworkManager version") from error

    def check_supported(self) -> str:
        version = self.transport.version()
        if self._version_tuple(version) < MINIMUM_VERSION:
            raise TeatherError(
                "networkmanager-version",
                "Teather requires NetworkManager 1.42 or newer to own the teather0 connection",
            )
        return version

    # -- resolver helpers -------------------------------------------------

    def _nameservers(self) -> list[str]:
        try:
            resolver = self.resolver_path.read_text(encoding="utf-8")
        except FileNotFoundError:
            # No resolv.conf at all: treat as an empty resolver. This is a valid
            # standalone-mode starting point (no other internet, nothing has
            # written one yet); NetworkManager creates it when teather0 arms.
            resolver = ""
        except OSError as error:
            raise TeatherError("resolver-inspection", "Cannot inspect resolver state") from error
        result: list[str] = []
        for raw_line in resolver.splitlines():
            fields = raw_line.split("#", 1)[0].strip().split()
            if len(fields) != 2 or fields[0] != "nameserver":
                continue
            try:
                address = ipaddress.ip_address(fields[1].split("%", 1)[0])
            except ValueError:
                continue
            result.append(str(address))
        return result

    def _non_sentinel_nameservers(self) -> list[str]:
        return [server for server in self._nameservers() if server != DNS_SENTINEL]

    def resolver_has_sentinel(self) -> bool:
        try:
            return DNS_SENTINEL in self._nameservers()
        except TeatherError:
            return False

    def _wait_resolver(self, sentinel_present: bool) -> None:
        deadline = time.monotonic() + self.timeout
        while True:
            present = DNS_SENTINEL in self._nameservers()
            if present == sentinel_present:
                return
            if time.monotonic() >= deadline:
                if sentinel_present:
                    raise TeatherError("dns-not-ready", "NetworkManager did not publish the Teather DNS sentinel")
                raise TeatherError("dns-residue", "NetworkManager did not remove the Teather DNS sentinel")
            time.sleep(0.1)

    # -- preflight ------------------------------------------------------

    def preflight(self) -> None:
        self.check_supported()
        if self.interface_path.exists():
            raise TeatherError("interface-collision", "teather0 already exists; run teather recover")
        try:
            self.transport.device_path(INTERFACE_NAME)
        except TeatherError:
            pass
        else:
            raise TeatherError("interface-collision", "NetworkManager already tracks a teather0 device")
        if self.resolver_has_sentinel():
            raise TeatherError("dns-residue", "The Teather DNS sentinel is already present; run teather recover")
        self._baseline_nameservers = self._non_sentinel_nameservers()

    # -- connection building -------------------------------------------

    def _build_connection(self, uid: int, gid: int, armed: bool) -> dict:
        from gi.repository import GLib

        def variant(signature, value):
            return GLib.Variant(signature, value)

        address, prefix = INTERFACE_ADDRESS.split("/", 1)
        dns_network = ipaddress.ip_network(VIRTUAL_DNS_ROUTE)
        routes = [
            {
                "dest": variant("s", str(dns_network.network_address)),
                "prefix": variant("u", dns_network.prefixlen),
            }
        ]
        ipv4: dict = {
            "method": variant("s", "manual"),
            "address-data": variant(
                "aa{sv}", [{"address": variant("s", address), "prefix": variant("u", int(prefix))}]
            ),
            "ignore-auto-dns": variant("b", False),
            "never-default": variant("b", not armed),
        }
        if armed:
            routes.append(
                {
                    "dest": variant("s", "0.0.0.0"),
                    "prefix": variant("u", 0),
                    "metric": variant("u", ROUTE_METRIC),
                }
            )
            ipv4["dns-data"] = variant("as", [DNS_SENTINEL])
            ipv4["dns-priority"] = variant("i", DNS_PRIORITY)
        ipv4["route-data"] = variant("aa{sv}", routes)
        return {
            "connection": {
                "id": variant("s", CONNECTION_ID),
                "type": variant("s", "tun"),
                "interface-name": variant("s", INTERFACE_NAME),
                "autoconnect": variant("b", False),
            },
            "tun": {
                "mode": variant("u", TUN_MODE_TUN),
                "owner": variant("s", str(uid)),
                "group": variant("s", str(gid)),
                "pi": variant("b", False),
            },
            "ipv4": ipv4,
            "ipv6": {"method": variant("s", "disabled")},
        }

    # -- activation ---------------------------------------------------

    def _wait_active(self) -> None:
        deadline = time.monotonic() + self.timeout
        while True:
            state = self.transport.active_state(self._active_path)
            if state == STATE_ACTIVATED:
                return
            if state not in (STATE_ACTIVATING, STATE_ACTIVATED):
                raise TeatherError("networkmanager-activation", "NetworkManager could not activate teather0")
            if time.monotonic() >= deadline:
                raise TeatherError("networkmanager-activation", "NetworkManager did not finish activating teather0")
            time.sleep(0.1)

    def _wait_device(self, present: bool) -> None:
        deadline = time.monotonic() + self.timeout
        while True:
            exists = self.interface_path.exists()
            if exists == present:
                return
            if time.monotonic() >= deadline:
                if present:
                    raise TeatherError("networkmanager-device", "teather0 did not appear")
                raise TeatherError("interface-residue", "teather0 did not disappear after teardown")
            time.sleep(0.1)

    def _verify_additive(self) -> None:
        """Fail closed if arming Teather DNS replaced a physical resolver.

        Only meaningful when `preflight` recorded a baseline nameserver — i.e. a
        physical link was up. Then an armed `resolv.conf` must list that
        nameserver *and* the sentinel; sentinel-only would mean Teather made
        itself the exclusive resolver while Wi-Fi was still working, the exact
        D-021 failure D-022 exists to prevent. With no physical link (standalone
        mode) sentinel-only is the correct, expected state, so the caller skips
        this check.
        """

        remaining = self._non_sentinel_nameservers()
        if not remaining:
            raise TeatherError(
                "dns-exclusive",
                "Teather DNS unexpectedly replaced the existing resolver instead of adding to it",
            )

    def activate(self, armed: bool) -> None:
        uid, gid = os.getuid(), os.getgid()
        # AddAndActivateConnection cannot create a tun device on the fly, so add
        # the in-memory connection first, then activate it — NetworkManager
        # creates teather0 during activation.
        self._settings_path = self.transport.add_connection(self._build_connection(uid, gid, armed))
        self._armed = armed
        try:
            self._active_path = self.transport.activate_connection(self._settings_path)
        except TeatherError:
            try:
                self.transport.delete_connection(self._settings_path)
            except TeatherError:
                pass
            self._settings_path = ""
            self._armed = False
            raise
        self._wait_active()
        self._wait_device(present=True)
        if armed:
            self._wait_resolver(sentinel_present=True)
            if self._baseline_nameservers:
                self._verify_additive()
        log.info("teather0 activated (armed=%s, baseline_resolvers=%d)", armed, len(self._baseline_nameservers))

    def recheck_connectivity(self) -> None:
        """Ask NetworkManager to re-run its connectivity probe.

        After a standalone activation (Teather is the only link) NM stays at
        LIMITED/CONNECTED_SITE until its periodic check next runs, so GNOME
        Shell shows no network icon even though traffic and DNS work. Nudging
        the check makes the icon appear. Best effort — never fails a connect.
        """

        try:
            state = self.transport.check_connectivity()
            log.info("NetworkManager connectivity recheck -> state %s", state)
        except TeatherError as error:
            log.debug("connectivity recheck skipped: %s", error)

    def connection_is_active(self) -> bool:
        if not self._active_path:
            return False
        try:
            return self.transport.active_state(self._active_path) == STATE_ACTIVATED
        except TeatherError:
            return False

    # -- teardown ---------------------------------------------------

    def deactivate(self) -> None:
        if not self._active_path and not self._settings_path:
            return
        if self._active_path:
            try:
                self.transport.deactivate(self._active_path)
            except TeatherError:
                pass
        if self._settings_path:
            try:
                self.transport.delete_connection(self._settings_path)
            except TeatherError:
                # Already gone (e.g. NetworkManager restarted): in-memory only.
                pass
        self._wait_device(present=False)
        if self._armed:
            self._wait_resolver(sentinel_present=False)
        self._active_path = ""
        self._settings_path = ""
        self._armed = False

    # -- recovery -------------------------------------------------

    def _safe_list(self) -> list[str]:
        try:
            return self.transport.list_connections()
        except TeatherError:
            return []

    def _is_ours(self, settings: dict) -> bool:
        connection = settings.get("connection", {})
        tun = settings.get("tun", {})
        return (
            connection.get("id") == CONNECTION_ID
            and connection.get("type") == "tun"
            and str(tun.get("owner", "")) == str(os.getuid())
        )

    def recover(self) -> None:
        device = ""
        try:
            device = self.transport.device_path(INTERFACE_NAME)
        except TeatherError:
            device = ""

        active = ""
        settings_path = ""
        if device:
            try:
                active = self.transport.device_active_connection(device)
                if active and active != "/":
                    settings_path = self.transport.active_connection_settings(active)
            except TeatherError:
                active = ""
        if not settings_path:
            for candidate in self._safe_list():
                try:
                    found = self.transport.connection_settings(candidate)
                except TeatherError:
                    continue
                if found.get("connection", {}).get("id") == CONNECTION_ID:
                    settings_path = candidate
                    break

        if device or settings_path:
            if not settings_path:
                raise TeatherError(
                    "ambiguous-interface",
                    "teather0 exists outside NetworkManager; inspect ownership before recovery",
                )
            try:
                settings = self.transport.connection_settings(settings_path)
            except TeatherError as error:
                raise TeatherError("ambiguous-interface", "Cannot read the teather0 connection for recovery") from error
            if not self._is_ours(settings):
                raise TeatherError(
                    "ambiguous-interface",
                    "teather0 exists but is not a Teather-owned connection; inspect ownership",
                )
            if active and active != "/":
                try:
                    self.transport.deactivate(active)
                except TeatherError:
                    pass
            try:
                self.transport.delete_connection(settings_path)
            except TeatherError:
                pass
            self._wait_device(present=False)

        self._active_path = ""
        self._settings_path = ""
        self._armed = False
        if self.resolver_has_sentinel():
            raise TeatherError("dns-residue", "The Teather DNS sentinel remains after recovery")
        if device or settings_path:
            log.info("recover: removed a stale teather0 connection")
