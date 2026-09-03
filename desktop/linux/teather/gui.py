from __future__ import annotations

from .dbus_client import DbusClient


class TeatherWindow:
    def __init__(self):
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import GLib, Gtk
        self.GLib, self.Gtk = GLib, Gtk
        self.app = None
        self.client = DbusClient()
        self.window = Gtk.Window(title="Teather")
        self.window.set_icon_name("teather")
        self.window.set_default_size(520, 430)
        self.window.connect("delete-event", self._delete)
        box = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10, margin=16)
        self.window.add(box)

        title = Gtk.Label()
        title.set_markup("<span size='xx-large' weight='bold'>Teather</span>")
        title.set_xalign(0)
        box.pack_start(title, False, False, 0)
        self.state = Gtk.Label(xalign=0, wrap=True)
        box.pack_start(self.state, False, False, 0)
        note = Gtk.Label(xalign=0, wrap=True)
        note.set_markup(
            "<small>Closing this window does not disconnect Teather — the background "
            "service keeps running and reconnects on its own. Reopen from the tray, or "
            "run <tt>teather-gtk</tt> again.</small>"
        )
        note.get_style_context().add_class("dim-label")
        box.pack_start(note, False, False, 0)

        self.devices = Gtk.ListStore(str, str, bool, bool, str)
        self.selector = Gtk.ComboBox.new_with_model(self.devices)
        renderer = Gtk.CellRendererText()
        self.selector.pack_start(renderer, True)
        self.selector.add_attribute(renderer, "text", 1)
        box.pack_start(self.selector, False, False, 0)

        actions = Gtk.Box(spacing=8)
        self.connect_button = Gtk.Button(label="Connect")
        self.connect_button.connect("clicked", self._connect)
        actions.pack_start(self.connect_button, True, True, 0)
        disconnect = Gtk.Button(label="Disconnect")
        disconnect.connect("clicked", lambda *_: self._call("Disconnect"))
        actions.pack_start(disconnect, True, True, 0)
        box.pack_start(actions, False, False, 0)

        device_actions = Gtk.Box(spacing=8)
        approve = Gtk.Button(label="Approve")
        approve.connect("clicked", self._approve)
        device_actions.pack_start(approve, True, True, 0)
        rename = Gtk.Button(label="Rename")
        rename.connect("clicked", self._rename)
        device_actions.pack_start(rename, True, True, 0)
        forget = Gtk.Button(label="Forget")
        forget.connect("clicked", self._forget)
        device_actions.pack_start(forget, True, True, 0)
        self.autoconnect = Gtk.CheckButton(label="Auto-connect when relay is already running")
        self.autoconnect.connect("toggled", self._auto_connect)
        device_actions.pack_start(self.autoconnect, True, True, 0)
        box.pack_start(device_actions, False, False, 0)

        self.failover = Gtk.CheckButton(
            label="Automatic failover: carry traffic once Wi-Fi/Ethernet is lost"
        )
        self._failover_guard = False
        self.failover.connect("toggled", self._set_failover)
        box.pack_start(self.failover, False, False, 0)

        upstream_row = Gtk.Box(spacing=8)
        upstream_row.pack_start(Gtk.Label(label="Phone upstream:", xalign=0), False, False, 0)
        self._upstreams = ["auto", "cellular", "wifi", "ethernet"]
        self.upstream = Gtk.ComboBoxText()
        for name in self._upstreams:
            self.upstream.append_text(name)
        self._upstream_guard = False
        self.upstream.connect("changed", self._set_upstream)
        upstream_row.pack_start(self.upstream, False, False, 0)
        box.pack_start(upstream_row, False, False, 0)

        self.hint = Gtk.Label(xalign=0, wrap=True, selectable=True)
        self.hint.get_style_context().add_class("dim-label")
        box.pack_start(self.hint, False, False, 0)

        self.metrics = Gtk.Label(xalign=0, selectable=True)
        box.pack_start(self.metrics, False, False, 0)
        diagnostics = Gtk.Button(label="Diagnostics")
        diagnostics.connect("clicked", self._diagnose)
        box.pack_start(diagnostics, False, False, 0)
        self.detail = Gtk.Label(xalign=0, yalign=0, selectable=True, wrap=True)
        box.pack_start(self.detail, True, True, 0)

        self.indicator = self._create_indicator()
        GLib.timeout_add_seconds(1, self.refresh)
        self.refresh()

    def _create_indicator(self):
        try:
            import gi
            gi.require_version("AyatanaAppIndicator3", "0.1")
            from gi.repository import AyatanaAppIndicator3
            indicator = AyatanaAppIndicator3.Indicator.new(
                "teather", "teather", AyatanaAppIndicator3.IndicatorCategory.SYSTEM_SERVICES,
            )
            indicator.set_status(AyatanaAppIndicator3.IndicatorStatus.ACTIVE)
            menu = self.Gtk.Menu()
            self.tray_status = self.Gtk.MenuItem(label="Status: starting")
            self.tray_status.set_sensitive(False)
            menu.append(self.tray_status)
            for label, callback in (
                ("Connect", self._connect), ("Disconnect", lambda *_: self._call("Disconnect")),
                ("Open", lambda *_: self.present()),
                ("Quit", lambda *_: self.app.quit() if self.app is not None else self.Gtk.main_quit()),
            ):
                item = self.Gtk.MenuItem(label=label)
                item.connect("activate", callback)
                menu.append(item)
            menu.show_all()
            indicator.set_menu(menu)
            return indicator
        except Exception:
            self.tray_status = None
            return None

    def _selected(self):
        iterator = self.selector.get_active_iter()
        if iterator is None:
            return None
        return {
            "device_id": self.devices[iterator][0], "name": self.devices[iterator][1],
            "approved": self.devices[iterator][2], "auto_connect": self.devices[iterator][3],
        }

    def _call(self, method, signature=None, arguments=()):
        try:
            result = self.client.call(method, signature, arguments)
            self.detail.set_text(str(result.get("message", "Done")))
        except Exception as error:
            self.detail.set_text(str(error))
        self.refresh()

    def _connect(self, *_args):
        selected = self._selected()
        self._call("Connect", "(s)", ((selected or {}).get("device_id", ""),))

    def _approve(self, *_args):
        selected = self._selected()
        if not selected:
            return
        dialog = self.Gtk.MessageDialog(
            transient_for=self.window, modal=True, message_type=self.Gtk.MessageType.QUESTION,
            buttons=self.Gtk.ButtonsType.YES_NO,
            text=f"Approve {selected['name']} for Teather on this computer?",
        )
        response = dialog.run()
        dialog.destroy()
        if response == self.Gtk.ResponseType.YES:
            self._call("ApproveDevice", "(s)", (selected["device_id"],))

    def _forget(self, *_args):
        selected = self._selected()
        if selected:
            self._call("ForgetDevice", "(s)", (selected["device_id"],))

    def _rename(self, *_args):
        selected = self._selected()
        if not selected:
            return
        dialog = self.Gtk.Dialog(
            title="Rename phone", transient_for=self.window, modal=True,
        )
        dialog.add_buttons(
            self.Gtk.STOCK_CANCEL, self.Gtk.ResponseType.CANCEL,
            self.Gtk.STOCK_OK, self.Gtk.ResponseType.OK,
        )
        entry = self.Gtk.Entry(text=selected["name"])
        entry.set_activates_default(True)
        dialog.get_content_area().pack_start(entry, True, True, 12)
        dialog.set_default_response(self.Gtk.ResponseType.OK)
        dialog.show_all()
        response = dialog.run()
        name = entry.get_text()
        dialog.destroy()
        if response == self.Gtk.ResponseType.OK:
            self._call("RenameDevice", "(ss)", (selected["device_id"], name))

    def _auto_connect(self, widget):
        selected = self._selected()
        if selected and widget.get_active() != selected["auto_connect"]:
            self._call("SetAutoConnect", "(sb)", (selected["device_id"], widget.get_active()))

    def _diagnose(self, *_args):
        self._call("Diagnose")

    def _set_failover(self, widget):
        if self._failover_guard:
            return
        self._call("SetAutoFailover", "(b)", (widget.get_active(),))

    def _set_upstream(self, widget):
        if self._upstream_guard:
            return
        name = widget.get_active_text()
        if name:
            self._call("SetUpstream", "(s)", (name,))

    def refresh(self):
        try:
            status = self.client.call("GetStatus")
            devices = self.client.call("ListDevices")
            current = self._selected()
            self.devices.clear()
            selected_index = 0
            for index, device in enumerate(devices):
                self.devices.append([
                    device["device_id"], device["name"], device["approved"],
                    device["auto_connect"], device["relay_state"],
                ])
                if current and current["device_id"] == device["device_id"]:
                    selected_index = index
            if devices:
                self.selector.set_active(selected_index)
                selected = self._selected()
                self.autoconnect.set_active(bool(selected and selected["auto_connect"]))
            self.state.set_text(f"State: {status['state']} — {status['message']}")
            self.hint.set_text(status.get("recovery_hint", "") or "")
            if self.tray_status is not None:
                self.tray_status.set_label(f"Status: {status['state']}")
            self._failover_guard = True
            self.failover.set_active(bool(status.get("auto_failover", True)))
            self._failover_guard = False
            self._upstream_guard = True
            want = status.get("upstream", "cellular")
            if want in self._upstreams:
                self.upstream.set_active(self._upstreams.index(want))
            self._upstream_guard = False
            if status.get("standalone") and status.get("failover_armed"):
                armed = "sole path"
            elif status.get("failover_armed"):
                armed = "armed"
            else:
                armed = "dormant"
            active_up = status.get("active_upstream") or status.get("upstream", "cellular")
            self.metrics.set_text(
                f"Active sessions: {status['active_sessions']}\n"
                f"Phone → Internet: {status['bytes_client_to_internet']} bytes\n"
                f"Internet → Phone: {status['bytes_internet_to_client']} bytes\n"
                f"Upstream: {active_up}   Failover: {armed}\n"
                "P1 coverage: TCP + virtual DNS; general UDP and IPv6 unsupported"
            )
        except Exception as error:
            self.state.set_text("State: unavailable")
            self.detail.set_text(str(error))
        return self.GLib.SOURCE_CONTINUE

    def _delete(self, *_args):
        # Never tear down the connection here — the daemon owns it. With a tray
        # icon we can hide and stay reachable; without one, closing ends only
        # this window (re-run teather-gtk to see status again).
        if self.indicator is not None:
            self.window.hide()
            return True
        if self.app is not None:
            self.app.quit()
        else:
            self.Gtk.main_quit()
        return False

    def present(self):
        self.window.show_all()
        self.window.present()


class TeatherApplication:
    """Single-instance wrapper: launching teather-gtk again re-presents the
    existing window instead of starting another process."""

    def __init__(self):
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gio, Gtk
        self.Gtk = Gtk
        self.app = Gtk.Application(
            application_id="io.github.vel71184.Teather",
            flags=Gio.ApplicationFlags.FLAGS_NONE,
        )
        self.app.connect("activate", self._activate)
        self.window = None

    def _activate(self, _app):
        if self.window is None:
            self.window = TeatherWindow()
            self.window.app = self.app
            self.app.add_window(self.window.window)
        self.window.present()

    def run(self, argv):
        return self.app.run(argv)


def main() -> int:
    import sys
    import gi
    gi.require_version("Gtk", "3.0")
    from gi.repository import GLib
    # Match the Wayland app_id / X11 WM_CLASS to teather.desktop so the shell's
    # window switcher and dock find our icon instead of the generic fallback.
    # Without this the id defaults to the "teather-gtk" binary name.
    GLib.set_prgname("teather")
    return TeatherApplication().run(sys.argv)


if __name__ == "__main__":
    raise SystemExit(main())
