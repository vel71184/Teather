from __future__ import annotations

import logging

from .constants import INTERFACE
from .errors import TeatherError

log = logging.getLogger("teather.notify")

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
    <method name="SetUpstream"><arg type="s" direction="in"/><arg type="a{{sv}}" direction="out"/></method>
    <method name="AndroidAppState"><arg type="s" direction="in"/><arg type="a{{sv}}" direction="out"/></method>
    <method name="InstallAndroid"><arg type="s" direction="in"/><arg type="a{{sv}}" direction="out"/></method>
    <method name="Diagnose"><arg type="a{{sv}}" direction="out"/></method>
    <method name="SessionHistory"><arg type="aa{{sv}}" direction="out"/></method>
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
        self._notified_state = ""
        self._notification_id = 0
        self._notify_close_source = 0
        manager.on_status_changed = self._on_status
        manager.on_devices_changed = lambda value: self._signal(
            "DevicesChanged", "(aa{sv})", ([dict_variant(GLib, item) for item in value],),
        )
        manager.on_metrics_changed = lambda value: self._signal("MetricsChanged", "(a{sv})", (dict_variant(GLib, value),))

    def _signal(self, name, signature, body):
        self.connection.emit_signal(None, self.object_path, INTERFACE, name, self.GLib.Variant(signature, body))

    def _on_status(self, value: dict) -> None:
        self._signal("StatusChanged", "(a{sv})", (dict_variant(self.GLib, value),))
        self._maybe_notify(value)

    def _maybe_notify(self, status: dict) -> None:
        """Fire a desktop notification on a meaningful transition so the user
        sees drops and self-heals even with the window closed and no tray."""

        state = str(status.get("state", ""))
        sole = bool(status.get("standalone"))
        key = f"{state}:{sole}" if state == "connected" else state
        if key == self._notified_state:
            return
        previous, self._notified_state = self._notified_state, key
        summary = body = ""
        transient = False
        if state == "connected":
            if previous.startswith("connected:") and previous != key:
                # Wi-Fi/Ethernet came or went while Teather stayed up.
                summary = "Teather is now your only connection" if sole else "Wi-Fi/Ethernet is back"
                body = str(status.get("message", ""))
                transient = True
            else:
                reconnected = previous in ("error", "disconnected")
                summary = "Teather reconnected" if reconnected else "Teather connected"
                body = str(status.get("message", ""))
                transient = not reconnected  # a first connect is expected; a recovery is worth keeping
        elif state == "disconnected" and status.get("last_drop"):
            summary = "Teather connection dropped"
            body = str(status.get("message", ""))
        elif state == "error":
            summary = "Teather needs attention"
            body = str(status.get("message", ""))
            if status.get("recovery_hint"):
                body = f"{body}\n{status['recovery_hint']}"
        if not summary:
            return
        GLib = self.GLib
        # This desktop (GNOME) only raises a banner for critical urgency; normal
        # urgency lands silently in the shade. Everything Teather sends here is a
        # state change the user should see, so all of it is urgency 2. Passing
        # the previous id replaces in place, so there is only ever one Teather
        # notification. Critical banners do not self-expire on GNOME, so for
        # everything except "needs attention" the daemon closes the banner
        # itself after a few seconds — a toast, no click to clear.
        hints = {
            "urgency": GLib.Variant("y", 2),
            "desktop-entry": GLib.Variant("s", "teather"),
        }
        if transient:
            hints["transient"] = GLib.Variant("b", True)
        try:
            reply = self.connection.call_sync(
                "org.freedesktop.Notifications", "/org/freedesktop/Notifications",
                "org.freedesktop.Notifications", "Notify",
                GLib.Variant(
                    "(susssasa{sv}i)",
                    ("Teather", self._notification_id, "network-vpn", summary, body, [], hints, 0),
                ),
                GLib.VariantType.new("(u)"), self.Gio.DBusCallFlags.NONE, 2000, None,
            )
            self._notification_id = int(reply.get_child_value(0).get_uint32())
        except Exception as error:
            log.debug("desktop notification not delivered: %s", error)
            return
        self._cancel_scheduled_close()
        if state != "error":
            self._notify_close_source = GLib.timeout_add_seconds(
                8, self._close_notification, self._notification_id,
            )

    def _cancel_scheduled_close(self) -> None:
        if self._notify_close_source:
            try:
                self.GLib.source_remove(self._notify_close_source)
            except Exception:
                pass
            self._notify_close_source = 0

    def _close_notification(self, notification_id: int) -> bool:
        self._notify_close_source = 0
        try:
            self.connection.call_sync(
                "org.freedesktop.Notifications", "/org/freedesktop/Notifications",
                "org.freedesktop.Notifications", "CloseNotification",
                self.GLib.Variant("(u)", (notification_id,)),
                None, self.Gio.DBusCallFlags.NONE, 2000, None,
            )
        except Exception as error:
            log.debug("could not close notification %s: %s", notification_id, error)
        return False  # GLib.SOURCE_REMOVE

    def _call(self, _connection, _sender, _path, _interface, method, parameters, invocation):
        try:
            arguments = parameters.unpack()
            methods = {
                "GetStatus": lambda: self.manager.get_status(),
                "ListDevices": lambda: self.manager.discover(),
                "Connect": lambda: (self.manager.note_user_intent(), self.manager.connect(arguments[0]))[1],
                "Disconnect": self.manager.disconnect,
                "ApproveDevice": lambda: self.manager.approve_device(arguments[0]),
                "RenameDevice": lambda: self.manager.rename_device(arguments[0], arguments[1]),
                "ForgetDevice": lambda: self.manager.forget_device(arguments[0]),
                "SetAutoConnect": lambda: self.manager.set_auto_connect(arguments[0], arguments[1]),
                "SetAutoFailover": lambda: self.manager.set_auto_failover(arguments[0]),
                "SetUpstream": lambda: self.manager.set_upstream(arguments[0]),
                "AndroidAppState": lambda: self.manager.android_app_state(arguments[0]),
                "InstallAndroid": lambda: (
                    self.manager.note_user_intent(), self.manager.install_android(arguments[0])
                )[1],
                "Diagnose": self.manager.diagnose,
                "SessionHistory": self.manager.session_history,
            }
            result = methods[method]()
            if method in ("ListDevices", "SessionHistory"):
                invocation.return_value(self.GLib.Variant("(aa{sv})", ([dict_variant(self.GLib, item) for item in result],)))
            else:
                invocation.return_value(self.GLib.Variant("(a{sv})", (dict_variant(self.GLib, result),)))
        except TeatherError as error:
            invocation.return_dbus_error(f"{INTERFACE}.Error.{error.category.replace('-', '_')}", str(error))
        except Exception:
            invocation.return_dbus_error(f"{INTERFACE}.Error.Internal", "Internal Teather error")
