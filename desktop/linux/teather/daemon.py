from __future__ import annotations

import logging
import signal

from .constants import BUS_NAME, OBJECT_PATH
from .dbus_service import ManagerDbusService
from .logging_setup import configure_logging
from .manager import Manager

log = logging.getLogger("teather.daemon")


def main() -> int:
    import gi
    gi.require_version("Gio", "2.0")
    from gi.repository import Gio, GLib

    configure_logging()
    log.info("teatherd starting")

    loop = GLib.MainLoop()
    manager = Manager()
    service = None

    # Startup session check: verify / clean up any leftover state from a crash
    # or a previous run before we accept connections.
    try:
        result = manager.recover()
        if result.get("recovery_pending"):
            log.warning("startup session check: leftover state could NOT be cleared — needs attention")
        else:
            log.info("startup session check: clean; awaiting connection")
    except Exception:
        log.exception("startup session check: could not complete (see above); will retry on the poll loop")

    def bus_acquired(connection, _name):
        nonlocal service
        service = ManagerDbusService(manager, connection, OBJECT_PATH)
        log.info("D-Bus name %s acquired", BUS_NAME)
        # Push whatever the startup session check left, now that the notifier
        # and any GUI can hear it.
        try:
            manager.emit_current_status()
        except Exception:
            log.exception("could not emit startup status")

    def name_lost(*_args):
        log.error("lost D-Bus name %s; exiting", BUS_NAME)
        loop.quit()

    owner_id = Gio.bus_own_name(
        Gio.BusType.SESSION, BUS_NAME, Gio.BusNameOwnerFlags.NONE,
        bus_acquired, None, name_lost,
    )

    def poll():
        try:
            manager.reconcile()
            manager.health_check()
            manager.maybe_auto_connect()
        except Exception:
            log.exception("poll cycle raised")
        return GLib.SOURCE_CONTINUE

    GLib.timeout_add_seconds(3, poll)
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGTERM, lambda: (loop.quit(), False)[1])
    GLib.unix_signal_add(GLib.PRIORITY_DEFAULT, signal.SIGINT, lambda: (loop.quit(), False)[1])
    try:
        loop.run()
    finally:
        log.info("teatherd stopping; releasing host resources (relay left for next start)")
        try:
            manager.shutdown()
        except Exception:
            log.exception("shutdown teardown failed")
        finally:
            Gio.bus_unown_name(owner_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
