from __future__ import annotations

import json
import logging
import signal
import socket
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable

from .adb import AdbClient, AdbDevice
from .config import ConfigStore
from .constants import (
    INTERFACE_ADDRESS,
    INTERFACE_NAME,
    RELAY_PORT,
    ROUTE_METRIC,
    UDPGW_SENTINEL,
    VIRTUAL_DNS_POOL,
    VIRTUAL_DNS_ROUTE,
)
from .dns_probe import probe_virtual_dns
from .errors import TeatherError
from .journal import Ownership, OwnershipJournal
from .networkmanager import NetworkManagerConnection
from .preflight import evaluate_routes, parse_nameservers

TUNNEL_PATH = "/usr/lib/teather/tun2proxy"

log = logging.getLogger(__name__)

# health_check runs on the daemon's ~3s poll. The cheap checks (adb device
# present, forward present, tunnel alive, teather0 active) run every cycle. The
# phone-relay probe is an `adb shell dumpsys` round-trip to the phone, so it
# runs only as a slow backstop — it exists purely to catch a relay that died
# while the USB link, the forward and tun2proxy all stayed up, which is rare
# (Android keeps a foreground service alive hard). ~2 min at a 3 s poll.
_RELAY_PROBE_EVERY = 40

# maybe_auto_connect stops retrying after this many consecutive failed connects
# and rests (cleanly disconnected) until something changes — a phone replug, a
# manual connect, or the pause elapsing. Without this a persistently failing
# connect (e.g. a wedged NetworkManager) would loop every 3 s forever.
_AUTOCONNECT_MAX_TRIES = 3
_AUTOCONNECT_PAUSE = 120.0


class Manager:
    def __init__(
        self,
        config: ConfigStore | None = None,
        journal: OwnershipJournal | None = None,
        adb: AdbClient | None = None,
        tunnel_path: str = TUNNEL_PATH,
        resolver_path: Path = Path("/etc/resolv.conf"),
        process_factory: Callable[..., subprocess.Popen] = subprocess.Popen,
        nm: NetworkManagerConnection | None = None,
        dns_probe: Callable[[], dict[str, str]] = probe_virtual_dns,
        interface_snapshot: Callable[[bool], str] | None = None,
        snapshot_timeout: float = 5.0,
    ):
        self.config = config or ConfigStore()
        self.journal = journal or OwnershipJournal()
        self.adb = adb or AdbClient()
        self.tunnel_path = tunnel_path
        self.resolver_path = resolver_path
        self.process_factory = process_factory
        self.nm = nm or NetworkManagerConnection(resolver_path=resolver_path)
        self.dns_probe = dns_probe
        self.interface_snapshot = interface_snapshot or self._system_interface_snapshot
        self.snapshot_timeout = snapshot_timeout
        self._state = "disconnected"
        self._error_category = "none"
        self._message = "No active connection"
        self._active_id = ""
        self._active_serial: str | None = None
        self._active_local_port: int | None = None
        self._active_upstream = ""
        self._tunnel: subprocess.Popen | None = None
        self._armed = False
        self._standalone = False
        self._dns_ready = False
        self._recovery_hint = ""
        self._last_drop = ""
        self._health_tick = 0
        self._reconcile_cooldown = 0.0
        self._autoconnect_tries = 0
        self._autoconnect_paused_until = 0.0
        self._autoconnect_seen: set[str] = set()
        self._relay_ok_at = 0.0
        self._lock = threading.RLock()
        self._devices: dict[str, AdbDevice] = {}
        self.on_status_changed: Callable[[dict], None] = lambda _status: None
        self.on_devices_changed: Callable[[list[dict]], None] = lambda _devices: None
        self.on_metrics_changed: Callable[[dict], None] = lambda _metrics: None

    def _emit_status(self) -> dict:
        status = self.get_status(refresh_android=False)
        self.on_status_changed(status)
        return status

    def emit_current_status(self) -> dict:
        """Re-push the current status. The daemon calls this once the D-Bus
        service (and its notifier) is wired, so a problem found by the startup
        session check is still surfaced."""
        with self._lock:
            return self._emit_status()

    def discover(self) -> list[dict]:
        remembered = self.config.devices()
        discovered: dict[str, AdbDevice] = {}
        for device in self.adb.devices():
            device_id = self.config.device_id(device.serial)
            discovered[device_id] = device
        self._devices = discovered
        result: list[dict] = []
        for device_id in sorted(set(discovered) | set(remembered)):
            device = discovered.get(device_id)
            saved = remembered.get(device_id)
            try:
                relay_state = self.adb.status(device.serial).lifecycle if device else "unavailable"
            except TeatherError:
                relay_state = "unknown"
            result.append({
                "device_id": device_id,
                "name": saved.name if saved else (device.model if device else "Android phone"),
                "approved": bool(saved and saved.approved),
                "auto_connect": bool(saved and saved.auto_connect),
                "connected": device is not None,
                "active": device_id == self._active_id,
                "relay_state": relay_state,
            })
        self.on_devices_changed(result)
        return result

    def _android_metrics(self) -> dict:
        if not self._active_serial:
            return {
                "active_sessions": 0,
                "bytes_client_to_internet": 0,
                "bytes_internet_to_client": 0,
                "accepted_clients": 0,
                "rejected_clients": 0,
            }
        status = self.adb.status(self._active_serial)
        self._note_relay_status(status)
        metrics = {
            "active_sessions": status.active_sessions,
            "bytes_client_to_internet": status.bytes_client_to_internet,
            "bytes_internet_to_client": status.bytes_internet_to_client,
            "accepted_clients": status.accepted_clients,
            "rejected_clients": status.rejected_clients,
        }
        self.on_metrics_changed(metrics)
        return metrics

    def get_status(self, refresh_android: bool = True) -> dict:
        metrics = self._android_metrics() if refresh_android else {
            "active_sessions": 0,
            "bytes_client_to_internet": 0,
            "bytes_internet_to_client": 0,
            "accepted_clients": 0,
            "rejected_clients": 0,
        }
        return {
            "api_version": 2,
            "state": self._state,
            "active_device_id": self._active_id,
            "error_category": self._error_category,
            "message": self._message,
            "recovery_hint": self._recovery_hint,
            "last_drop": self._last_drop,
            "tcp_supported": True,
            "dns_mode": "virtual",
            "dns_ready": self._dns_ready,
            "auto_failover": self.config.auto_failover(),
            "failover_armed": self._armed,
            "standalone": self._standalone,
            "upstream": self.config.upstream(),
            "active_upstream": self._active_upstream,
            "udp_supported": True,
            "ipv6_supported": False,
            **metrics,
        }

    def _select(self, device_id: str) -> tuple[str, AdbDevice]:
        self.discover()
        remembered = self.config.devices()
        if device_id:
            candidates = [device_id]
        else:
            candidates = [key for key in self._devices if key in remembered and remembered[key].approved]
        if not candidates:
            raise TeatherError("no-approved-device", "No approved Android phone is connected")
        if len(candidates) > 1:
            raise TeatherError("selection-required", "More than one approved phone is available")
        chosen = candidates[0]
        if chosen not in self._devices:
            raise TeatherError("device-unavailable", "The selected phone is not connected through ADB")
        if chosen not in remembered or not remembered[chosen].approved:
            raise TeatherError("approval-required", "Approve this phone locally before connecting")
        return chosen, self._devices[chosen]

    def _run_json(self, command: list[str]) -> str:
        try:
            result = subprocess.run(
                command, capture_output=True, text=True, timeout=5, check=False,
                env={"PATH": "/usr/sbin:/usr/bin:/sbin:/bin"},
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise TeatherError("route-inspection", f"Cannot inspect Linux networking: {type(error).__name__}") from error
        if result.returncode:
            raise TeatherError("route-inspection", "Linux route inspection failed")
        return result.stdout

    def preflight(self, armed: bool) -> None:
        result = evaluate_routes(
            self._run_json(["/usr/sbin/ip", "-j", "-4", "route", "show", "table", "all"]),
            self._run_json(["/usr/sbin/ip", "-j", "link", "show"]),
            self._run_json(["/usr/sbin/ip", "-j", "-4", "address", "show"]),
            self._run_json(["/usr/sbin/ip", "-j", "-4", "rule", "show"]),
        )
        if not result.safe:
            raise TeatherError(result.category, result.message)
        standalone = result.category == "standalone"
        self._standalone = standalone
        if standalone and not armed:
            # A dormant connection with no physical default carries no traffic and
            # would silently do nothing. Tell the user how to make it usable.
            raise TeatherError(
                "failover-disabled",
                "No other internet connection is present and automatic failover is off; "
                "run 'teather failover on' to use Teather as your only connection",
            )
        # With a physical link up, Teather must not become the sole resolver
        # (nm._verify_additive enforces this). Standalone + armed has no physical
        # resolver to sit behind: tun2proxy virtual DNS plus the phone-side
        # sentinel do the resolving, so a pre-existing nameserver is not required.
        try:
            resolver = self.resolver_path.read_text(encoding="utf-8")
        except OSError as error:
            if not standalone:
                raise TeatherError("resolver-inspection", "Cannot inspect resolver state") from error
            resolver = ""
        if not standalone and not parse_nameservers(resolver):
            raise TeatherError("resolver-unavailable", "No usable non-loopback nameserver is configured")
        self.nm.preflight()

    def _system_interface_snapshot(self, armed: bool) -> str:
        address = self._run_json(["/usr/sbin/ip", "-j", "-4", "address", "show", "dev", INTERFACE_NAME])
        routes = self._run_json(["/usr/sbin/ip", "-j", "-4", "route", "show", "dev", INTERFACE_NAME])
        try:
            value = {"address": json.loads(address), "routes": json.loads(routes)}
        except ValueError as error:
            raise TeatherError("route-inspection", "Cannot parse Teather interface state") from error
        expected_address, expected_prefix = INTERFACE_ADDRESS.split("/", 1)
        addresses = [
            info
            for entry in value["address"]
            for info in entry.get("addr_info", [])
            if info.get("family") == "inet"
        ]
        # Destinations must be exactly right. NetworkManager picks the metric for
        # the scope-link virtual-DNS route, so only the backup default's metric
        # is pinned.
        destinations = {route.get("dst", "default") for route in value["routes"]}
        default_metrics = {
            int(route.get("metric", 0))
            for route in value["routes"]
            if route.get("dst", "default") == "default"
        }
        expected_destinations = {VIRTUAL_DNS_ROUTE}
        if armed:
            expected_destinations.add("default")
        if (
            len(addresses) != 1
            or addresses[0].get("local") != expected_address
            or int(addresses[0].get("prefixlen", -1)) != int(expected_prefix)
            or destinations != expected_destinations
            or (armed and default_metrics != {ROUTE_METRIC})
        ):
            raise TeatherError("tunnel-start", "Teather interface state is incomplete or unexpected")
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    def _wait_interface_snapshot(self, armed: bool) -> str:
        deadline = time.monotonic() + self.snapshot_timeout
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                snapshot = self.interface_snapshot(armed)
                if snapshot:
                    return snapshot
            except Exception as error:
                last_error = error
            time.sleep(0.1)
        raise TeatherError("tunnel-start", "Teather interface did not become ready") from last_error

    def _tunnel_command(self, local_port: int) -> list[str]:
        # No --setup: NetworkManager already owns teather0's address, routes, and
        # DNS. tun2proxy only attaches to the tun.owner-delegated device and
        # moves packets, which needs no privilege.
        return [
            self.tunnel_path,
            "--proxy", f"socks5://127.0.0.1:{local_port}",
            "--tun", INTERFACE_NAME,
            "--dns", "virtual",
            "--virtual-dns-pool", VIRTUAL_DNS_POOL,
            # UDP is carried over the same SOCKS connection as framed datagrams
            # (badvpn "udpgw"); the phone's UdpGatewayServer terminates it. The
            # sentinel is a CONNECT target, never a route. More pooled gateway
            # connections keep streams warm for bursty UDP apps (e.g. cloud
            # gaming); a longer UDP timeout keeps their quieter control flows up.
            "--udpgw-server", UDPGW_SENTINEL,
            "--udpgw-connections", "16",
            "--udp-timeout", "30",
            "--mtu", "1500",
            "--tcp-timeout", "300",
            # A full-desktop failover easily exceeds 64 concurrent flows; the
            # phone-side SOCKS server allows 256 to match.
            "--max-sessions", "256",
            "--verbosity", "off",
            "--exit-on-fatal-error",
        ]

    def _stop_tunnel(self, cleanup_errors: list[str]) -> None:
        if self._tunnel is not None and self._tunnel.poll() is None:
            try:
                self._tunnel.send_signal(signal.SIGTERM)
                try:
                    self._tunnel.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    self._tunnel.kill()
                    self._tunnel.wait(timeout=2)
            except Exception:
                cleanup_errors.append("tunnel-process")
        self._tunnel = None

    def _cleanup_tunnel_nm(self, cleanup_errors: list[str]) -> None:
        self._stop_tunnel(cleanup_errors)
        self._dns_ready = False
        self._active_local_port = None
        try:
            self.nm.deactivate()
        except Exception:
            cleanup_errors.append("networkmanager-connection")
        self._armed = False
        self._standalone = False

    def connect(self, device_id: str = "") -> dict:
        with self._lock:
            if self._state == "connected":
                if not device_id or device_id == self._active_id:
                    return self.get_status()
                raise TeatherError("already-connected", "Disconnect the active phone first")
            # A leftover ownership journal or an error state from an earlier drop
            # would otherwise wedge every future connect. Try to clear it the
            # same way the daemon's periodic self-heal would before refusing.
            if self._load_journal_safe() is not None or self._state == "error":
                self._reconcile_locked(trigger="connect")
            if self._load_journal_safe() is not None:
                self._state = "error"
                self._error_category = "recovery-pending"
                self._message = (
                    "Teather still has leftover resources from an earlier session that it "
                    "could not clean up automatically."
                )
                self._recovery_hint = "Restart the background service:  systemctl --user restart teather.service"
                self._emit_status()
                raise TeatherError("recovery-pending", self._message)
            self._state = "connecting"
            self._error_category = "none"
            self._message = "Checking host and Android relay"
            self._emit_status()
            local_port: int | None = None
            android_started = False
            serial: str | None = None
            selected_id = ""
            armed = self.config.auto_failover()
            upstream = self.config.upstream()
            try:
                self.preflight(armed)
                selected_id, device = self._select(device_id)
                serial = device.serial
                if not self.adb.package_installed(serial):
                    raise TeatherError("android-app-missing", "Teather is not installed on the selected phone")
                android = self.adb.status(serial)
                if android.running and not android.compatible:
                    raise TeatherError(
                        "android-incompatible",
                        f"Android relay is running with incompatible schema or port; expected port {RELAY_PORT}",
                    )
                if android.running and not android.matches_upstream(upstream):
                    raise TeatherError(
                        "android-incompatible",
                        f"Android relay is already running on '{android.configured_upstream}'; "
                        f"stop it on the phone or run 'teather upstream {android.configured_upstream}'",
                    )
                if not android.running:
                    android_started = True
                    android = self.adb.start_relay(serial, upstream)
                if not android.compatible:
                    raise TeatherError("android-not-ready", "Android relay did not report compatible ready status")
                local_port = self.adb.add_forward(serial)
                self.journal.save(Ownership(selected_id, local_port, android_started))
                self._active_local_port = local_port
                self.nm.activate(armed)
                self._armed = armed
                self._wait_interface_snapshot(armed)
                self._tunnel = self.process_factory(
                    self._tunnel_command(local_port),
                    stdin=subprocess.DEVNULL,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.PIPE,
                    text=True,
                    env={"PATH": "/usr/bin:/bin"},
                )
                try:
                    exit_code = self._tunnel.wait(timeout=0.25)
                except subprocess.TimeoutExpired:
                    exit_code = None
                if exit_code is not None:
                    detail = self._tunnel.stderr.read(240).strip() if self._tunnel.stderr else ""
                    raise TeatherError("tunnel-start", detail or "Packet engine exited immediately")
                if armed:
                    self.dns_probe()
                    self._dns_ready = True
                    if self._standalone:
                        # No physical link: NetworkManager parks at LIMITED and
                        # GNOME shows no network icon until its connectivity
                        # probe next runs. Nudge it so the icon appears.
                        recheck = getattr(self.nm, "recheck_connectivity", None)
                        if callable(recheck):
                            recheck()
                    self._message = (
                        "Connected. Teather is your only internet path right now; Wi-Fi or Ethernet will take over automatically if one appears."
                        if self._standalone
                        else "Connected. Teather is the automatic backup path if Wi-Fi or Ethernet drops."
                    )
                else:
                    self._dns_ready = False
                    self._message = "Connected; failover is disabled, so Teather stays dormant until armed"
                self._active_id = selected_id
                self._active_serial = serial
                self._active_local_port = local_port
                self._active_upstream = upstream
                self._state = "connected"
                self._error_category = "none"
                self._recovery_hint = ""
                self._last_drop = ""
                self._health_tick = 0
                self._relay_ok_at = time.monotonic()
                log.info("connected: device=%s upstream=%s armed=%s standalone=%s port=%s",
                         selected_id[:12], upstream, armed, self._standalone, local_port)
                return self._emit_status()
            except Exception as error:
                log.warning("connect failed: %s", error)
                # If the relay may have been started but not yet journalled,
                # record it so the teardown below (and any later reconcile) can
                # still find and stop it.
                if android_started and selected_id and self._load_journal_safe() is None:
                    try:
                        self.journal.save(Ownership(selected_id, local_port, True))
                    except Exception:
                        pass
                clean, errors = self._release_owned(use_nm_scan=False)
                self._tunnel = None
                self._active_local_port = None
                self._state = "error"
                if not clean:
                    self._error_category = "recovery-pending"
                    self._message = (
                        f"Could not connect ({error}); cleanup of "
                        + ", ".join(sorted(set(errors)))
                        + " could not be confirmed."
                    )
                    if not self._recovery_hint:
                        self._recovery_hint = (
                            "Teather retries cleanup automatically; if it stays stuck, run:  "
                            "systemctl --user restart teather.service"
                        )
                    error = TeatherError("recovery-pending", self._message)
                else:
                    self._error_category = getattr(error, "category", "internal-error")
                    self._message = str(error)
                    if {"adb-forward", "android-relay"} & set(errors):
                        self._recovery_hint = (
                            "The phone-side relay may still be running; it won't block reconnecting."
                        )
                self._emit_status()
                raise error

    # -- shared teardown / self-heal ------------------------------------

    def _load_journal_safe(self) -> Ownership | None:
        try:
            return self.journal.load()
        except TeatherError as error:
            # A corrupt runtime journal helps nobody. It lives in /run, it is
            # ours, and its only job is to name resources to release — drop it
            # and fall back to inspecting live state.
            log.warning("ownership journal unreadable (%s); clearing it", error)
            try:
                self.journal.clear()
            except Exception:
                pass
            return None

    def _note_relay_status(self, status) -> None:
        """Remember the last time the phone relay was seen healthy so
        health_check can skip its own probe when a GUI is already polling."""
        if getattr(status, "compatible", False):
            self._relay_ok_at = time.monotonic()

    def _device_present(self, serial: str) -> bool:
        try:
            return any(device.serial == serial for device in self.adb.devices())
        except TeatherError:
            # ADB itself is unreachable — can't prove the phone is gone, so do
            # not declare it gone (the tunnel/forward checks will catch a real
            # break).
            return True

    def _forward_present(self, serial: str, port: int) -> bool:
        try:
            return port in self.adb.list_forwards(serial)
        except TeatherError:
            return True

    def _resolve_serial(self, ownership: Ownership | None) -> str | None:
        if self._active_serial is not None:
            return self._active_serial
        if ownership is None:
            return None
        try:
            self.discover()
        except TeatherError:
            return None
        device = self._devices.get(ownership.device_id)
        if device is None or self.config.device_id(device.serial) != ownership.device_id:
            return None
        return device.serial

    def _release_owned(self, *, use_nm_scan: bool, stop_relay: bool = False) -> tuple[bool, list[str]]:
        """Release every Teather-owned resource. Returns ``(clean, errors)``.

        The **host side** — the tun2proxy child and the in-memory ``teather0``
        connection with its route and DNS — is strict: ``clean`` is False and
        the ownership journal is kept until it is verified released
        (``AGENTS.md``: route/DNS state must be bounded and restored, and an
        unverifiable ``teather0`` is a real problem the user must see).

        The **phone side** — the loopback ADB forward and the relay app — is
        lenient: both die with the cable, neither is host state, and neither may
        ever wedge the next connect. A forward that will not remove is logged
        and surfaced as a hint, and the journal is still cleared once the host
        side is clean (the next connect re-derives phone state from ``adb``).

        ``stop_relay`` is True only for a user ``disconnect`` — the user wants
        everything gone. The self-heal paths (health-drop, reconcile, recover,
        a failed connect) leave a relay Teather started **running**: stopping it
        would defeat auto-reconnect, which will not start a stopped relay, so
        the self-heal would clean up and then sit there. A left-running relay is
        adopted on the next connect.

        ``use_nm_scan`` runs NetworkManager's ownership-verifying ``teather0``
        scan (for the daemon-restarted / lost-handles case). ``disconnect``
        leaves it off and relies on its live handles.
        """

        errors: list[str] = []
        ownership = self._load_journal_safe()
        serial = self._resolve_serial(ownership)
        phone_gone = (
            (serial is None and ownership is not None and self._active_serial is None)
            or (serial is not None and not self._device_present(serial))
        )

        self._cleanup_tunnel_nm(errors)
        if use_nm_scan:
            try:
                self.nm.recover()
                errors = [item for item in errors if item != "networkmanager-connection"]
            except TeatherError as error:
                log.warning("teardown: nm.recover refused: %s", error)
                if "networkmanager-connection" not in errors:
                    errors.append("networkmanager-connection")
                self._recovery_hint = (
                    "teather0 is still present and Teather can't confirm it owns it — "
                    "check:  nmcli con show teather0"
                )

        if ownership is not None and not phone_gone and serial is not None:
            if ownership.local_port is not None:
                try:
                    self.adb.remove_forward(serial, ownership.local_port)
                except Exception as error:
                    log.warning("teardown: remove_forward failed: %s", error)
                    errors.append("adb-forward")
            if ownership.android_started and stop_relay:
                try:
                    self.adb.stop_relay(serial)
                except Exception as error:
                    log.warning("teardown: stop_relay failed: %s", error)
                    errors.append("android-relay")

        host_clean = not ({"networkmanager-connection", "tunnel-process"} & set(errors))
        if ownership is not None and host_clean:
            try:
                self.journal.clear()
            except Exception:
                errors.append("ownership-journal")

        clean = host_clean and self._load_journal_safe() is None
        return clean, errors

    def _finish_teardown(self, clean: bool, errors: list[str], *, disconnected_message: str) -> dict:
        self._active_id = ""
        self._active_serial = None
        self._active_local_port = None
        self._active_upstream = ""
        phone_side = {"adb-forward", "android-relay"} & set(errors)
        if clean:
            self._state = "disconnected"
            self._error_category = "none"
            self._message = disconnected_message
            self._recovery_hint = (
                "Teather couldn't confirm the phone-side relay/bridge was released; "
                "it can't block reconnecting, but you can stop the relay from the phone if you want."
                if phone_side else ""
            )
        else:
            self._state = "error"
            self._error_category = "recovery-pending"
            self._message = (
                "Teather could not finish cleaning up: "
                + ", ".join(sorted(set(errors)))
                + "."
            )
            if not self._recovery_hint:
                self._recovery_hint = "Restart the background service:  systemctl --user restart teather.service"
        return self._emit_status()

    def disconnect(self) -> dict:
        with self._lock:
            log.info("disconnect requested (state=%s)", self._state)
            self._last_drop = ""
            clean, errors = self._release_owned(use_nm_scan=False, stop_relay=True)
            return self._finish_teardown(
                clean, errors,
                disconnected_message="Disconnected. Wi-Fi and Ethernet were never touched.",
            )

    def shutdown(self) -> None:
        """Teardown for the daemon stopping (SIGTERM / systemd restart). Releases
        the host side — tun2proxy, teather0, its route and DNS — so nothing
        dangles, but **leaves the phone relay running**: a daemon restart is not
        the user asking to disconnect, and the next start adopts the relay so
        the connection comes straight back. An explicit `teather disconnect`
        stops the relay; this does not."""
        with self._lock:
            log.info("shutdown teardown (state=%s)", self._state)
            clean, errors = self._release_owned(use_nm_scan=False)
            if not clean:
                log.warning("shutdown teardown incomplete: %s", sorted(set(errors)))

    def reconcile(self) -> None:
        """Periodic self-heal, run from the daemon poll loop. A cheap no-op
        unless there is leftover state (an error state, an ownership journal,
        or a teather0 interface) while nothing is connected."""

        with self._lock:
            self._reconcile_locked(trigger="poll")

    def _reconcile_locked(self, *, trigger: str) -> None:
        if self._state in {"connecting", "connected"}:
            return
        interface_path = getattr(self.nm, "interface_path", None)
        needs = (
            self._error_category == "recovery-pending"
            or self._load_journal_safe() is not None
            or bool(interface_path and interface_path.exists())
        )
        if not needs:
            return
        if trigger == "poll" and time.monotonic() < getattr(self, "_reconcile_cooldown", 0.0):
            return
        log.info("reconcile (%s): state=%s error=%s", trigger, self._state, self._error_category)
        clean, errors = self._release_owned(use_nm_scan=True)
        if clean:
            self._finish_teardown(
                clean, errors,
                disconnected_message="Teather cleared leftover resources from an earlier session and is ready to connect.",
            )
            log.info("reconcile: recovered to a clean disconnected state")
        else:
            self._reconcile_cooldown = time.monotonic() + 30.0
            self._finish_teardown(clean, errors, disconnected_message="")
            log.warning("reconcile: still not clean: %s", sorted(set(errors)))

    def set_upstream(self, upstream: str) -> dict:
        """Choose which Android transport the relay uses.

        While connected, this rebinds only the phone's relay upstream with no
        listener teardown — the `teather0` interface, the tunnel, routes, and DNS
        stay up, and so does the SOCKS listener. New connections use the new
        upstream; established sessions stay on the transport they opened on. It
        cannot change a relay Teather did not start (a manual relay is
        reconfigured on the phone).
        """

        with self._lock:
            self.config.set_upstream(upstream)
            if self._state != "connected" or self._active_upstream == upstream:
                return self.get_status()
            if not self._active_serial:
                raise TeatherError("upstream-unavailable", "No active phone to reconfigure")
            if self.journal.load() is None or not self.journal.load().android_started:
                raise TeatherError(
                    "manual-relay",
                    "Teather did not start this relay; change the upstream on the phone",
                )
            self._message = f"Switching relay upstream to {upstream}"
            self._emit_status()
            android = self.adb.reconfigure_relay(self._active_serial, upstream)
            if not android.compatible or not android.matches_upstream(upstream):
                self.disconnect()
                raise TeatherError("android-not-ready", f"Relay did not come back on '{upstream}'")
            self._active_upstream = upstream
            self._message = f"Connected; relay upstream is {upstream}"
            return self._emit_status()

    def recover(self) -> dict:
        with self._lock:
            log.info("recover requested (state=%s)", self._state)
            clean, errors = self._release_owned(use_nm_scan=True)
            self._finish_teardown(
                clean, errors,
                disconnected_message="Recovered leftover resources; ready to connect.",
            )
            if not clean and "networkmanager-connection" in errors:
                # An unverifiable teather0 is a real host-state problem the user
                # must see, not something to silently keep retrying.
                raise TeatherError(
                    "ambiguous-interface",
                    self._recovery_hint or "teather0 could not be confirmed as Teather-owned",
                )
            result = self.diagnose()
            result["recovery_pending"] = not clean
            return result

    def approve_device(self, device_id: str) -> dict:
        self.discover()
        device = self._devices.get(device_id)
        if not device:
            raise TeatherError("device-unavailable", "The phone must be connected to approve it")
        saved = self.config.approve(device_id, device.model)
        self.discover()
        return {"device_id": saved.device_id, "name": saved.name, "approved": True}

    def rename_device(self, device_id: str, name: str) -> dict:
        saved = self.config.rename(device_id, name)
        self.discover()
        return {"device_id": saved.device_id, "name": saved.name, "approved": saved.approved}

    def forget_device(self, device_id: str) -> dict:
        if device_id == self._active_id:
            raise TeatherError("device-active", "Disconnect the phone before forgetting it")
        self.config.forget(device_id)
        self.discover()
        return {"device_id": device_id, "forgotten": True}

    def set_auto_connect(self, device_id: str, enabled: bool) -> dict:
        saved = self.config.set_auto_connect(device_id, enabled)
        self.discover()
        return {"device_id": saved.device_id, "auto_connect": saved.auto_connect}

    def set_auto_failover(self, enabled: bool) -> dict:
        with self._lock:
            self.note_user_intent()
            self.config.set_auto_failover(enabled)
            if self._state == "connected" and self._armed != bool(enabled):
                active = self._active_id
                self.disconnect()
                if self._state == "disconnected":
                    self.connect(active)
            return {
                "auto_failover": self.config.auto_failover(),
                "failover_armed": self._armed,
            }

    def note_user_intent(self) -> None:
        """Clear the auto-connect backoff. Called on any deliberate user action
        (manual connect, approve, failover/auto-connect toggle) so a paused
        retry loop resumes immediately instead of waiting out the pause."""
        self._autoconnect_tries = 0
        self._autoconnect_paused_until = 0.0

    def maybe_auto_connect(self) -> None:
        if self._state not in {"disconnected", "detected"}:
            return
        if self._load_journal_safe() is not None:
            # Leftover state still pending; reconcile owns clearing it first.
            return
        devices = self.discover()
        eligible = []
        for device in devices:
            if device["connected"] and device["approved"] and device["auto_connect"]:
                raw = self._devices[device["device_id"]]
                try:
                    if self.adb.status(raw.serial).compatible:
                        eligible.append(device["device_id"])
                except TeatherError as error:
                    log.debug("auto-connect: status probe failed for a device: %s", error)

        # A change in which phones are eligible (a replug, an approval) is a
        # fresh situation — drop any backoff from the previous one.
        seen = set(eligible)
        if seen != self._autoconnect_seen:
            self._autoconnect_seen = seen
            self.note_user_intent()

        if len(eligible) > 1:
            self._state = "detected"
            self._error_category = "selection-required"
            self._message = "Two auto-connect phones are eligible — pick one in the Teather window."
            self._emit_status()
            return
        if len(eligible) != 1:
            return
        if time.monotonic() < self._autoconnect_paused_until:
            return

        try:
            log.info("auto-connecting to %s", eligible[0][:12])
            self.connect(eligible[0])
            self._autoconnect_tries = 0
        except TeatherError as error:
            self._autoconnect_tries += 1
            log.warning("auto-connect attempt %d failed: %s", self._autoconnect_tries, error)
            if self._autoconnect_tries >= _AUTOCONNECT_MAX_TRIES:
                self._autoconnect_tries = 0
                self._autoconnect_paused_until = time.monotonic() + _AUTOCONNECT_PAUSE
                self._message = (
                    f"Auto-connect failed {_AUTOCONNECT_MAX_TRIES} times ({error}). "
                    f"Paused for {int(_AUTOCONNECT_PAUSE // 60)} minutes — unplug/replug the phone "
                    "or press Connect to retry now."
                )
                self._recovery_hint = "Press Connect in the Teather window to retry immediately."
                self._emit_status()

    def health_check(self) -> None:
        """Detect an abnormal loss of the live connection and self-heal.

        Abnormal = anything other than the user asking to disconnect: the phone
        unplugged, the USB/ADB bridge dropped, tun2proxy died, NetworkManager
        dropped teather0, or the phone-side relay stopped. On any of these
        Teather releases its own resources and returns to a clean
        `disconnected` state so the daemon's auto-connect can bring it straight
        back when the phone reappears — no manual `teather recover` step.
        """

        if self._state != "connected":
            return
        self._health_tick += 1
        self._track_sole_path()
        serial = self._active_serial
        drop: tuple[str, str] | None = None
        if serial is not None and not self._device_present(serial):
            drop = ("phone-disconnected", "the phone was unplugged or lost its USB link")
        elif self._tunnel is None or self._tunnel.poll() is not None:
            drop = ("tunnel-exited", "the tunnel process stopped")
        elif not self.nm.connection_is_active():
            drop = ("connection-lost", "NetworkManager dropped the teather0 connection")
        elif (
            serial is not None
            and self._active_local_port is not None
            and not self._forward_present(serial, self._active_local_port)
        ):
            drop = ("relay-unreachable", "the USB bridge to the phone's relay disappeared")
        elif (
            serial is not None
            and self._health_tick % _RELAY_PROBE_EVERY == 0
            and time.monotonic() - self._relay_ok_at > _RELAY_PROBE_EVERY * 3 - 5
        ):
            # Slow backstop only, and skipped entirely when something else
            # (a GUI polling GetStatus) has confirmed the relay recently.
            try:
                status = self.adb.status(serial)
                self._note_relay_status(status)
                if not status.compatible:
                    drop = ("relay-stopped", "the relay app on the phone is no longer running")
            except TeatherError:
                drop = None

        if drop is None:
            return
        category, human = drop
        log.warning("health: lost the connection — %s (%s)", category, human)
        self._last_drop = category
        clean, errors = self._release_owned(use_nm_scan=False)
        if category == "phone-disconnected":
            tail = "Teather cleaned up; it reconnects automatically when the phone is plugged back in."
        elif category == "relay-stopped":
            tail = "Teather cleaned up. The relay on the phone stopped — press Connect, or start it from the phone, to resume."
        else:
            tail = "Teather cleaned up and is reconnecting automatically."
        self._finish_teardown(
            clean, errors,
            disconnected_message=f"Connection dropped — {human}. {tail}",
        )

    def _physical_default_present(self) -> bool | None:
        """True/False if a non-teather0 IPv4 default route exists; None if it
        can't be determined this tick (don't act on None)."""
        try:
            routes = json.loads(self._run_json(["/usr/sbin/ip", "-j", "-4", "route", "show", "default"]))
        except (TeatherError, ValueError):
            return None
        return any(
            isinstance(route, dict) and str(route.get("dev", "")) != INTERFACE_NAME
            for route in routes
        )

    def _track_sole_path(self) -> None:
        """While connected + armed, notice Wi-Fi/Ethernet coming or going so the
        `standalone` flag stays accurate and the user is told when their tether
        actually starts carrying everything (it matters for data usage)."""
        if not self._armed:
            return
        present = self._physical_default_present()
        if present is None:
            return
        now_sole = not present
        if now_sole == self._standalone:
            return
        self._standalone = now_sole
        if now_sole:
            self._message = (
                "Wi-Fi/Ethernet dropped — Teather is now carrying all traffic over the phone's cellular data."
            )
        else:
            self._message = "Wi-Fi/Ethernet is back; Teather dropped to standby."
        log.info("sole-path transition: standalone=%s", now_sole)
        self._emit_status()

    def diagnose(self) -> dict:
        issues: list[str] = []
        for executable in ("adb", "/usr/sbin/ip"):
            found = Path(executable).exists() if executable.startswith("/") else any(
                (Path(directory) / executable).exists() for directory in ("/usr/bin", "/bin", str(Path.home() / ".local/bin"))
            )
            if not found:
                issues.append(f"missing-{Path(executable).name}")
        if not Path(self.tunnel_path).exists():
            issues.append("missing-tun2proxy")
        try:
            resolver = self.resolver_path.read_text(encoding="utf-8")
            nameservers = len(parse_nameservers(resolver))
        except OSError:
            nameservers = 0
            issues.append("resolver-unreadable")
        if nameservers == 0:
            issues.append("no-usable-nameserver")
        try:
            networkmanager_version = self.nm.check_supported()
        except TeatherError as error:
            networkmanager_version = "unavailable"
            issues.append(error.category)
        return {
            "ready": not issues,
            "issues": ",".join(issues) if issues else "none",
            "usable_nameservers": nameservers,
            "networkmanager_version": networkmanager_version,
            "dns_integration": "networkmanager-native-tun",
            "dns_ready": self._dns_ready,
            "auto_failover": self.config.auto_failover(),
            "failover_armed": self._armed,
            "upstream": self.config.upstream(),
            "recovery_guide": "/usr/share/doc/teather/RECOVERY.md.gz",
            "networkmanager_mutation": self._state == "connected",
            "persistent_networkmanager_mutation": False,
            "direct_resolver_mutation": False,
            "firewall_mutation": False,
        }
