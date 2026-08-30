from __future__ import annotations

from .constants import INTERFACE
from .errors import TeatherError

INTROSPECTION_XML = f"""
<node>
  <interface name="{INTERFACE}">
    <method name="GetStatus"><arg type="a{{sv}}" direction="out"/></method>
    <method name="ListDevices"><arg type="aa{{sv}}" direction="out"/></method>
    <method name="Connect"><arg type="s" direction="in"/><arg type="a{{sv}}" direction="out"/></method>
    <method name="Disconnect"><arg type="a{{sv}}" direction="out"/></method>
    <method name="ApproveDevice"><arg type="s" direction="in"/><arg type="a{{sv}}" direction="out"/></method>
    <method name="RenameDevice"><arg type="s" direction="in"/><arg type="s" direction="in"/><arg type="a{{sv}}" direction="out"/></method>
    <method name="ForgetDevice"><arg type="s" direction="in"/><arg type="a{{sv}}" direction="out"/></method>
    <method name="SetAutoConnect"><arg type="s" direction="in"/><arg type="b" direction="in"/><arg type="a{{sv}}" direction="out"/></method>
    <method name="SetAutoFailover"><arg type="b" direction="in"/><arg type="a{{sv}}" direction="out"/></method>
    <method name="Diagnose"><arg type="a{{sv}}" direction="out"/></method>
    <signal name="StatusChanged"><arg type="a{{sv}}"/></signal>
    <signal name="DevicesChanged"><arg type="aa{{sv}}"/></signal>
    <signal name="MetricsChanged"><arg type="a{{sv}}"/></signal>
  </interface>
</node>
"""


def _gi():
    import gi
    gi.require_version("Gio", "2.0")
    from gi.repository import Gio, GLib
    return Gio, GLib


def value_variant(GLib, value):
    if isinstance(value, bool):
        return GLib.Variant("b", value)
    if isinstance(value, int):
        return GLib.Variant("t", max(0, value))
    return GLib.Variant("s", str(value))


def dict_variant(GLib, value: dict):
    return {key: value_variant(GLib, item) for key, item in value.items()}


class ManagerDbusService:
    def __init__(self, manager, connection, object_path):
        self.manager = manager
        self.connection = connection
        self.object_path = object_path
        Gio, GLib = _gi()
        self.Gio, self.GLib = Gio, GLib
        node = Gio.DBusNodeInfo.new_for_xml(INTROSPECTION_XML)
        self.registration_id = connection.register_object(
            object_path, node.interfaces[0], self._call, None, None,
        )
        manager.on_status_changed = lambda value: self._signal("StatusChanged", "(a{sv})", (dict_variant(GLib, value),))
        manager.on_devices_changed = lambda value: self._signal(
            "DevicesChanged", "(aa{sv})", ([dict_variant(GLib, item) for item in value],),
        )
        manager.on_metrics_changed = lambda value: self._signal("MetricsChanged", "(a{sv})", (dict_variant(GLib, value),))

    def _signal(self, name, signature, body):
        self.connection.emit_signal(None, self.object_path, INTERFACE, name, self.GLib.Variant(signature, body))

    def _call(self, _connection, _sender, _path, _interface, method, parameters, invocation):
        try:
            arguments = parameters.unpack()
            methods = {
                "GetStatus": lambda: self.manager.get_status(),
                "ListDevices": lambda: self.manager.discover(),
                "Connect": lambda: self.manager.connect(arguments[0]),
                "Disconnect": self.manager.disconnect,
                "ApproveDevice": lambda: self.manager.approve_device(arguments[0]),
                "RenameDevice": lambda: self.manager.rename_device(arguments[0], arguments[1]),
                "ForgetDevice": lambda: self.manager.forget_device(arguments[0]),
                "SetAutoConnect": lambda: self.manager.set_auto_connect(arguments[0], arguments[1]),
                "SetAutoFailover": lambda: self.manager.set_auto_failover(arguments[0]),
                "Diagnose": self.manager.diagnose,
            }
            result = methods[method]()
            if method == "ListDevices":
                invocation.return_value(self.GLib.Variant("(aa{sv})", ([dict_variant(self.GLib, item) for item in result],)))
            else:
                invocation.return_value(self.GLib.Variant("(a{sv})", (dict_variant(self.GLib, result),)))
        except TeatherError as error:
            invocation.return_dbus_error(f"{INTERFACE}.Error.{error.category.replace('-', '_')}", str(error))
        except Exception:
            invocation.return_dbus_error(f"{INTERFACE}.Error.Internal", "Internal Teather error")
