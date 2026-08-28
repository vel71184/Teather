from __future__ import annotations

from .constants import BUS_NAME, INTERFACE, OBJECT_PATH


class DbusClient:
    def __init__(self):
        import gi
        gi.require_version("Gio", "2.0")
        from gi.repository import Gio, GLib
        self.Gio, self.GLib = Gio, GLib
        self.proxy = Gio.DBusProxy.new_for_bus_sync(
            Gio.BusType.SESSION,
            Gio.DBusProxyFlags.NONE,
            None,
            BUS_NAME,
            OBJECT_PATH,
            INTERFACE,
            None,
        )

    def call(self, method: str, signature: str | None = None, arguments: tuple = ()):
        parameters = self.GLib.Variant(signature, arguments) if signature else None
        result = self.proxy.call_sync(method, parameters, self.Gio.DBusCallFlags.NONE, 30_000, None)
        return self._unpack(result)[0]

    def _unpack(self, value):
        if isinstance(value, self.GLib.Variant):
            return self._unpack(value.unpack())
        if isinstance(value, dict):
            return {key: self._unpack(item) for key, item in value.items()}
        if isinstance(value, tuple):
            return tuple(self._unpack(item) for item in value)
        if isinstance(value, list):
            return [self._unpack(item) for item in value]
        return value
