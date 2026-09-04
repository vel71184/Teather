from __future__ import annotations

import json
import os
import sys
from pathlib import Path

from . import __file__ as _pkg_file
from .dbus_client import DbusClient


def _installed_code_mtime() -> float:
    """Newest mtime among the installed teather*.py files. A `dpkg -i` rewrites
    them, so a jump means a package upgrade happened under a running window."""
    try:
        package = Path(_pkg_file).resolve().parent
        return max((p.stat().st_mtime for p in package.glob("*.py")), default=0.0)
    except OSError:
        return 0.0

THEME_CHOICES = ("system", "light", "dark")
THEME_LABELS = {"system": "Follow system", "light": "Light", "dark": "Dark"}


def _gui_prefs_path() -> Path:
    base = os.environ.get("XDG_CONFIG_HOME") or (Path.home() / ".config")
    return Path(base) / "teather" / "gui.json"


def _load_gui_prefs() -> dict:
    try:
        data = json.loads(_gui_prefs_path().read_text(encoding="utf-8"))
    except (OSError, ValueError):
        return {}
    return data if isinstance(data, dict) else {}


def _save_gui_prefs(prefs: dict) -> None:
    path = _gui_prefs_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(json.dumps(prefs, sort_keys=True), encoding="utf-8")
    except OSError:
        pass


def _read_theme() -> str:
    theme = _load_gui_prefs().get("theme", "system")
    return theme if theme in THEME_CHOICES else "system"


def _write_theme(theme: str) -> None:
    prefs = _load_gui_prefs()
    prefs["theme"] = theme if theme in THEME_CHOICES else "system"
    _save_gui_prefs(prefs)


class TeatherWindow:
    def __init__(self):
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import GLib, Gtk
        self.GLib, self.Gtk = GLib, Gtk
        self.app = None
        self.client = DbusClient()
        self._app_state = None
        self._app_checked_for = None
        self._security_nagged = False
        self._code_stamp = _installed_code_mtime()
        self._theme_guard = False
        self._apply_theme(_read_theme())
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

        self.update_banner = Gtk.Button(
            label="A Teather update is installed — click to restart this window"
        )
        self.update_banner.get_style_context().add_class("suggested-action")
        self.update_banner.connect("clicked", lambda *_: self._restart_self())
        self.update_banner.set_no_show_all(True)
        box.pack_start(self.update_banner, False, False, 0)

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

        appearance_row = Gtk.Box(spacing=8)
        appearance_row.pack_start(Gtk.Label(label="Appearance:", xalign=0), False, False, 0)
        self.theme = Gtk.ComboBoxText()
        for name in THEME_CHOICES:
            self.theme.append(name, THEME_LABELS[name])
        self.theme.set_active_id(_read_theme())
        self.theme.connect("changed", self._set_theme)
        appearance_row.pack_start(self.theme, False, False, 0)
        box.pack_start(appearance_row, False, False, 0)

        self.hint = Gtk.Label(xalign=0, wrap=True, selectable=True)
        self.hint.get_style_context().add_class("dim-label")
        box.pack_start(self.hint, False, False, 0)

        self.metrics = Gtk.Label(xalign=0, selectable=True)
        box.pack_start(self.metrics, False, False, 0)
        tools = Gtk.Box(spacing=8)
        diagnostics = Gtk.Button(label="Diagnostics")
        diagnostics.connect("clicked", self._diagnose)
        tools.pack_start(diagnostics, True, True, 0)
        self.phone_app_button = Gtk.Button(label="Phone app…")
        self.phone_app_button.connect("clicked", self._phone_app)
        tools.pack_start(self.phone_app_button, True, True, 0)
        box.pack_start(tools, False, False, 0)
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

    def _actionable_app_status(self):
        """The current phone-app status if it warrants an install, else None."""
        status = (self._app_state or {}).get("status")
        return status if status in ("missing", "outdated") else None

    def _check_phone_app(self, device_id):
        """One on-demand AndroidAppState probe (an adb round-trip — never on the
        poll loop). Caches the result and restyles the button."""
        try:
            self._app_state = self.client.call("AndroidAppState", "(s)", (device_id,))
        except Exception:
            self._app_state = None
        self._app_checked_for = device_id
        self._refresh_phone_app_button()

    def _refresh_phone_app_button(self):
        state = self._app_state or {}
        status = state.get("status")
        bundled = state.get("bundled_version_code", 0)
        installed = state.get("installed_version_code", 0)
        security = bool(state.get("bundled_security", 0) > state.get("installed_security", 0)
                        and state.get("installed_security", 0))
        css = self.phone_app_button.get_style_context()
        for name in ("suggested-action", "destructive-action"):
            css.remove_class(name)
        if status == "missing":
            label, sensitive, cls = f"Install app (v{bundled})", True, "suggested-action"
        elif status == "outdated" and security:
            label, sensitive, cls = f"Security update (v{installed}→v{bundled})", True, "destructive-action"
        elif status == "outdated":
            label, sensitive, cls = f"Update app (v{installed}→v{bundled})", True, "suggested-action"
        elif status == "current":
            label, sensitive, cls = f"App up to date (v{installed})", False, None
        elif status == "ahead":
            label, sensitive, cls = "Phone app is newer", False, None
        else:
            label, sensitive, cls = "Phone app…", status is None, None
        self.phone_app_button.set_label(label)
        self.phone_app_button.set_sensitive(sensitive)
        if cls:
            css.add_class(cls)

    def _phone_app(self, *_args):
        selected = self._selected()
        device_id = (selected or {}).get("device_id", "")
        if self._actionable_app_status() is None:
            self._check_phone_app(device_id)
            state = self._app_state or {}
            self.detail.set_text({
                "current": f"The phone app is up to date (version {state.get('installed_version_code', 0)}).",
                "ahead": "The phone app is newer than this package bundles.",
                "no-device": "Connect exactly one phone (or pick it in the list) first.",
                "no-bundle": "This package does not bundle a phone app.",
            }.get(state.get("status"), "Checked the phone app."))
            if self._actionable_app_status() is None:
                return
        self._install_phone_app(device_id)

    def _install_phone_app(self, device_id):
        state = self._app_state or {}
        status = state.get("status")
        bundled = state.get("bundled_version_code", 0)
        verb = "Update" if status == "outdated" else "Install"
        try:
            connected = self.client.call("GetStatus").get("state") == "connected"
        except Exception:
            connected = False
        prompt = f"{verb} the Teather app (version {bundled}) on the phone now?"
        if connected:
            prompt += (
                "\n\nTeather will disconnect for the install and reconnect afterwards — "
                "if the phone is your only link, expect a short outage."
            )
        dialog = self.Gtk.MessageDialog(
            transient_for=self.window, modal=True,
            message_type=self.Gtk.MessageType.QUESTION, buttons=self.Gtk.ButtonsType.YES_NO,
            text=prompt,
        )
        response = dialog.run()
        dialog.destroy()
        if response != self.Gtk.ResponseType.YES:
            return
        try:
            if connected:
                self.client.call("Disconnect")
            result = self.client.call("InstallAndroid", "(s)", (device_id,))
            self.detail.set_text(
                f"Phone app is now version {result.get('version_code')} "
                f"({result.get('action', 'installed')})."
            )
            if connected:
                self.client.call("Connect", "(s)", (device_id,))
        except Exception as error:
            self.detail.set_text(str(error))
        self._security_nagged = False
        self._check_phone_app(device_id)
        self.refresh()

    _APP_ERRORS = ("android-app-missing", "android-incompatible", "android-not-ready")

    def _sync_phone_app(self, status, devices):
        connected = [d["device_id"] for d in devices if d.get("connected")]
        device_id = connected[0] if len(connected) == 1 else ""

        # Re-probe only when the phone changed or an app-related error appeared
        # for one we have not checked — never every refresh (it is an adb call).
        app_error = status.get("error_category") in self._APP_ERRORS
        if device_id and (device_id != self._app_checked_for
                          or (app_error and self._actionable_app_status() is None)):
            self._check_phone_app(device_id)
        elif not device_id and self._app_checked_for is not None:
            self._app_state = None
            self._app_checked_for = None
            self._refresh_phone_app_button()

        if status.get("security_update_available"):
            if not self._security_nagged:
                self._security_nagged = True
                self._prompt_security_update(device_id)
        else:
            self._security_nagged = False

    def _prompt_security_update(self, device_id):
        dialog = self.Gtk.MessageDialog(
            transient_for=self.window, modal=True,
            message_type=self.Gtk.MessageType.WARNING, buttons=self.Gtk.ButtonsType.YES_NO,
            text="A security update is available for the phone app.",
        )
        dialog.format_secondary_text(
            "The Teather app on the phone is behind on a security-relevant fix. "
            "Install the update now? Teather will disconnect briefly and reconnect."
        )
        response = dialog.run()
        dialog.destroy()
        if response == self.Gtk.ResponseType.YES:
            if self._app_state is None:
                self._check_phone_app(device_id)
            self._install_phone_app(device_id)

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

    def _apply_theme(self, theme):
        settings = self.Gtk.Settings.get_default()
        if settings is None:
            return
        if theme == "dark":
            settings.set_property("gtk-application-prefer-dark-theme", True)
        elif theme == "light":
            settings.set_property("gtk-application-prefer-dark-theme", False)
        else:
            settings.reset_property("gtk-application-prefer-dark-theme")

    def _set_theme(self, widget):
        if self._theme_guard:
            return
        theme = widget.get_active_id() or "system"
        _write_theme(theme)
        self._apply_theme(theme)

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
            self._sync_phone_app(status, devices)
        except Exception as error:
            self.state.set_text("State: unavailable")
            self.detail.set_text(str(error))
        if _installed_code_mtime() > self._code_stamp + 1:
            self.update_banner.show()
        return self.GLib.SOURCE_CONTINUE

    def _restart_self(self):
        os.execv(sys.executable, [sys.executable, os.path.realpath(sys.argv[0])])

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
    """Single-instance wrapper. Launching `teather-gtk` again takes over any
    running instance (ALLOW_REPLACEMENT | REPLACE) rather than re-presenting it,
    so a window left open from before a package upgrade is replaced by one
    running the new code instead of silently keeping the old code."""

    def __init__(self):
        import gi
        gi.require_version("Gtk", "3.0")
        from gi.repository import Gio, Gtk
        self.Gtk = Gtk
        self.app = Gtk.Application(
            application_id="io.github.vel71184.Teather",
            flags=Gio.ApplicationFlags.ALLOW_REPLACEMENT | Gio.ApplicationFlags.REPLACE,
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
