from __future__ import annotations

import signal

from .constants import BUS_NAME, OBJECT_PATH
from .dbus_service import ManagerDbusService
from .manager import Manager


def main() -> int:
    import gi
    gi.require_version("Gio", "2.0")
    from gi.repository import Gio, GLib

    loop = GLib.MainLoop()
    manager = Manager()
    service = None

    try:
        manager.recover()
    except Exception:
        # An unsafe or ambiguous journal remains for explicit `teather recover`.
        pass

    def bus_acquired(connection, _name):
        nonlocal service
        service = ManagerDbusService(manager, connection, OBJECT_PATH)

    owner_id = Gio.bus_own_name(
        Gio.BusType.SESSION, BUS_NAME, Gio.BusNameOwnerFlags.NONE,
        bus_acquired, None, lambda *_args: loop.quit(),
    )

    def poll():
        try:
            manager.health_check()
            manager.maybe_auto_connect()
        except Exception:
            pass
        return GLib.SOURCE_CONTINUE

    GLib.timeout_add_seconds(3, poll)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: (loop.quit(), False)[1])
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, lambda: (loop.quit(), False)[1])
    try:
        loop.run()
    finally:
        try:
            manager.disconnect()
        finally:
            Gio.bus_unown_name(owner_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
