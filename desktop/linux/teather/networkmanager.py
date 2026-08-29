from __future__ import annotations

import time
from pathlib import Path
from typing import Protocol

from .constants import DNS_PRIORITY, DNS_SENTINEL, INTERFACE_NAME
from .errors import TeatherError
from .preflight import parse_nameservers


NETWORKMANAGER_BUS = "org.freedesktop.NetworkManager"
NETWORKMANAGER_PATH = "/org/freedesktop/NetworkManager"
NETWORKMANAGER_INTERFACE = "org.freedesktop.NetworkManager"
DEVICE_INTERFACE = "org.freedesktop.NetworkManager.Device"
PROPERTIES_INTERFACE = "org.freedesktop.DBus.Properties"
PRESERVE_EXTERNAL_IP = 0x1
RELOAD_DNS_RC = 0x2


class NetworkManagerTransport(Protocol):
    def version(self) -> str: ...

    def device_for_interface(self, interface: str) -> str: ...

    def get_applied_connection(self, device_path: str) -> tuple[dict, int]: ...

    def reapply(self, device_path: str, settings: dict, version: int) -> None: ...

    def reload_dns(self) -> None: ...


def _settings_mapping(settings_variant) -> dict:
    """Copy a{sa{sv}} while retaining every leaf's D-Bus variant type."""
    return {
        section: {
            key: settings_variant.lookup_value(section, None).lookup_value(key, None)
            for key in settings_variant.lookup_value(section, None).keys()
        }
        for section in settings_variant.keys()
    }


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

    def version(self) -> str:
        _Gio, GLib = self._gi()
        reply = self._call(
            NETWORKMANAGER_PATH,
            PROPERTIES_INTERFACE,
            "Get",
            GLib.Variant("(ss)", (NETWORKMANAGER_INTERFACE, "Version")),
            "(v)",
        )
        return reply.get_child_value(0).get_variant().get_string()

    def device_for_interface(self, interface: str) -> str:
        _Gio, GLib = self._gi()
        reply = self._call(
            NETWORKMANAGER_PATH,
            NETWORKMANAGER_INTERFACE,
            "GetDeviceByIpIface",
            GLib.Variant("(s)", (interface,)),
            "(o)",
        )
        return reply.get_child_value(0).get_string()

    def get_applied_connection(self, device_path: str) -> tuple[dict, int]:
        _Gio, GLib = self._gi()
        reply = self._call(
            device_path,
            DEVICE_INTERFACE,
            "GetAppliedConnection",
            GLib.Variant("(u)", (0,)),
            "(a{sa{sv}}t)",
        )
        return _settings_mapping(reply.get_child_value(0)), reply.get_child_value(1).get_uint64()

    def reapply(self, device_path: str, settings: dict, version: int) -> None:
        _Gio, GLib = self._gi()
        self._call(
            device_path,
            DEVICE_INTERFACE,
            "Reapply",
            GLib.Variant("(a{sa{sv}}tu)", (settings, version, PRESERVE_EXTERNAL_IP)),
            "()",
        )

    def reload_dns(self) -> None:
        _Gio, GLib = self._gi()
        self._call(
            NETWORKMANAGER_PATH,
            NETWORKMANAGER_INTERFACE,
            "Reload",
            GLib.Variant("(u)", (RELOAD_DNS_RC,)),
            "()",
        )


class NetworkManagerDns:
    def __init__(
        self,
        resolver_path: Path = Path("/etc/resolv.conf"),
        interface_path: Path = Path(f"/sys/class/net/{INTERFACE_NAME}"),
        transport: NetworkManagerTransport | None = None,
        timeout: float = 5.0,
    ):
        self.resolver_path = resolver_path
        self.interface_path = interface_path
        self.transport = transport or GioNetworkManagerTransport()
        self.timeout = timeout
        self._device_path = ""
        self._original_settings: dict | None = None
        self._applied = False

    @staticmethod
    def _version_tuple(value: str) -> tuple[int, int]:
        try:
            fields = value.split(".")
            return int(fields[0]), int(fields[1])
        except (ValueError, IndexError) as error:
            raise TeatherError("networkmanager-version", "Cannot parse the NetworkManager version") from error

    def check_supported(self) -> str:
        version = self.transport.version()
        if self._version_tuple(version) < (1, 42):
            raise TeatherError(
                "networkmanager-version",
                "Teather requires NetworkManager 1.42 or newer for safe temporary DNS",
            )
        return version

    def preflight(self) -> None:
        self.check_supported()
        if DNS_SENTINEL in self._nameservers():
            raise TeatherError("dns-residue", "Teather DNS is already present; run teather recover")

    def _nameservers(self) -> list[str]:
        try:
            return parse_nameservers(self.resolver_path.read_text(encoding="utf-8"))
        except OSError as error:
            raise TeatherError("resolver-inspection", "Cannot inspect resolver state") from error

    def _wait_nameservers(self, expected_active: bool) -> None:
        deadline = time.monotonic() + self.timeout
        while True:
            nameservers = self._nameservers()
            matches = nameservers == [DNS_SENTINEL] if expected_active else DNS_SENTINEL not in nameservers
            if matches:
                return
            if time.monotonic() >= deadline:
                category = "dns-not-ready" if expected_active else "dns-residue"
                message = (
                    "NetworkManager did not install only the Teather DNS endpoint"
                    if expected_active
                    else "NetworkManager did not remove the Teather DNS endpoint"
                )
                raise TeatherError(category, message)
            time.sleep(0.1)

    def _wait_device(self) -> str:
        deadline = time.monotonic() + self.timeout
        last_error: TeatherError | None = None
        while time.monotonic() < deadline:
            try:
                return self.transport.device_for_interface(INTERFACE_NAME)
            except TeatherError as error:
                last_error = error
                time.sleep(0.1)
        raise TeatherError(
            "networkmanager-device",
            "NetworkManager did not observe the temporary Teather interface",
        ) from last_error

    @staticmethod
    def _with_teather_dns(settings: dict) -> dict:
        from gi.repository import GLib

        if "ipv4" not in settings:
            raise TeatherError("networkmanager-settings", "The Teather interface has no applied IPv4 settings")
        updated = {section: dict(values) for section, values in settings.items()}
        ipv4 = updated["ipv4"]
        ipv4["dns"] = GLib.Variant("au", [])
        ipv4["dns-data"] = GLib.Variant("as", [DNS_SENTINEL])
        ipv4["dns-priority"] = GLib.Variant("i", DNS_PRIORITY)
        ipv4["ignore-auto-dns"] = GLib.Variant("b", True)
        return updated

    def apply(self) -> None:
        self._device_path = self._wait_device()
        settings, version = self.transport.get_applied_connection(self._device_path)
        self._original_settings = settings
        self.transport.reapply(self._device_path, self._with_teather_dns(settings), version)
        self._applied = True
        self._wait_nameservers(expected_active=True)

    def resolver_is_active(self) -> bool:
        try:
            return self._nameservers() == [DNS_SENTINEL]
        except TeatherError:
            return False

    def restore_while_active(self) -> None:
        if not self._applied or not self._device_path or self._original_settings is None:
            return
        self.transport.reapply(self._device_path, self._original_settings, 0)
        self._wait_nameservers(expected_active=False)
        self._applied = False

    def ensure_no_residue(self) -> None:
        if DNS_SENTINEL not in self._nameservers():
            self._applied = False
            return
        if self.interface_path.exists():
            raise TeatherError("dns-residue", "Teather DNS remains while teather0 still exists")
        self.transport.reload_dns()
        self._wait_nameservers(expected_active=False)
        self._applied = False

    def recover(self) -> None:
        if DNS_SENTINEL not in self._nameservers():
            return
        if self.interface_path.exists():
            raise TeatherError(
                "ambiguous-interface",
                "Teather DNS and teather0 remain; inspect ownership before recovery",
            )
        self.transport.reload_dns()
        self._wait_nameservers(expected_active=False)
