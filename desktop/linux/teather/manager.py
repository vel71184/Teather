from __future__ import annotations

import json
import os
import signal
import subprocess
import threading
import time
from pathlib import Path
from typing import Callable

from .adb import AdbClient, AdbDevice
from .android_status import AndroidStatus
from .config import ConfigStore
from .constants import (
    DNS_SENTINEL,
    INTERFACE_ADDRESS,
    INTERFACE_NAME,
    RELAY_PORT,
    ROUTE_METRIC,
    VIRTUAL_DNS_ROUTE,
)
from .dns_probe import probe_virtual_dns
from .errors import TeatherError
from .journal import Ownership, OwnershipJournal
from .networkmanager import NetworkManagerDns
from .preflight import evaluate_routes, parse_nameservers


class Manager:
    def __init__(
        self,
        config: ConfigStore | None = None,
        journal: OwnershipJournal | None = None,
        adb: AdbClient | None = None,
        helper: str = "/usr/libexec/teather-helper",
        resolver_path: Path = Path("/etc/resolv.conf"),
        process_factory: Callable[..., subprocess.Popen] = subprocess.Popen,
        dns_controller: NetworkManagerDns | None = None,
        dns_probe: Callable[[], dict[str, str]] = probe_virtual_dns,
        interface_snapshot: Callable[[], str] | None = None,
    ):
        self.config = config or ConfigStore()
        self.journal = journal or OwnershipJournal()
        self.adb = adb or AdbClient()
        self.helper = helper
        self.resolver_path = resolver_path
        self.process_factory = process_factory
        self.dns_controller = dns_controller or NetworkManagerDns(resolver_path=resolver_path)
        self.dns_probe = dns_probe
        self.interface_snapshot = interface_snapshot or self._system_interface_snapshot
        self._state = "disconnected"
        self._error_category = "none"
        self._message = "No active connection"
        self._active_id = ""
        self._active_serial: str | None = None
        self._tunnel: subprocess.Popen | None = None
        self._dns_ready = False
        self._lock = threading.RLock()
        self._devices: dict[str, AdbDevice] = {}
        self.on_status_changed: Callable[[dict], None] = lambda _status: None
        self.on_devices_changed: Callable[[list[dict]], None] = lambda _devices: None
        self.on_metrics_changed: Callable[[dict], None] = lambda _metrics: None

    def _emit_status(self) -> dict:
        status = self.get_status(refresh_android=False)
        self.on_status_changed(status)
        return status

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
            "tcp_supported": True,
            "dns_mode": "virtual",
            "dns_ready": self._dns_ready,
            "udp_supported": False,
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

    def preflight(self) -> None:
        result = evaluate_routes(
            self._run_json(["/usr/sbin/ip", "-j", "-4", "route", "show", "table", "main"]),
            self._run_json(["/usr/sbin/ip", "-j", "link", "show"]),
            self._run_json(["/usr/sbin/ip", "-j", "-4", "address", "show"]),
            self._run_json(["/usr/sbin/ip", "-j", "-4", "rule", "show"]),
        )
        if not result.safe:
            raise TeatherError(result.category, result.message)
        try:
            resolver = self.resolver_path.read_text(encoding="utf-8")
        except OSError as error:
            raise TeatherError("resolver-inspection", "Cannot inspect resolver state") from error
        if not parse_nameservers(resolver):
            raise TeatherError("resolver-unavailable", "No usable non-loopback nameserver is configured")
        self.dns_controller.preflight()

    def _system_interface_snapshot(self) -> str:
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
        route_values = {
            (route.get("dst", "default"), int(route.get("metric", 0)))
            for route in value["routes"]
        }
        if (
            len(addresses) != 1
            or addresses[0].get("local") != expected_address
            or int(addresses[0].get("prefixlen", -1)) != int(expected_prefix)
            or (VIRTUAL_DNS_ROUTE, 0) not in route_values
            or ("default", ROUTE_METRIC) not in route_values
        ):
            raise TeatherError("tunnel-start", "Teather interface state is incomplete or unexpected")
        return json.dumps(value, sort_keys=True, separators=(",", ":"))

    def _wait_interface_snapshot(self) -> str:
        deadline = time.monotonic() + 5
        last_error: Exception | None = None
        while time.monotonic() < deadline:
            try:
                snapshot = self.interface_snapshot()
                if snapshot:
                    return snapshot
            except Exception as error:
                last_error = error
            time.sleep(0.1)
        raise TeatherError("tunnel-start", "Teather interface did not become ready") from last_error

    def _cleanup_tunnel_dns(self, cleanup_errors: list[str]) -> None:
        try:
            self.dns_controller.restore_while_active()
        except Exception:
            # Interface removal is the authoritative fallback for temporary state.
            pass
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
        self._dns_ready = False
        try:
            self.dns_controller.ensure_no_residue()
        except Exception:
            cleanup_errors.append("resolver-state")

    def connect(self, device_id: str = "") -> dict:
        with self._lock:
            if self._state == "connected":
                if not device_id or device_id == self._active_id:
                    return self.get_status()
                raise TeatherError("already-connected", "Disconnect the active phone first")
            if self.journal.load() is not None:
                self._state = "error"
                self._error_category = "recovery-pending"
                self._message = "Journaled resources must be recovered before creating a new connection"
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
            try:
                self.preflight()
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
                if not android.running:
                    android_started = True
                    android = self.adb.start_relay(serial)
                if not android.compatible:
                    raise TeatherError("android-not-ready", "Android relay did not report compatible ready status")
                local_port = self.adb.add_forward(serial)
                self.journal.save(Ownership(selected_id, local_port, android_started))
                self._tunnel = self.process_factory(
                    ["pkexec", self.helper, "run", str(local_port)],
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
                    raise TeatherError("tunnel-start", detail or "Privileged tunnel helper exited")
                interface_before_dns = self._wait_interface_snapshot()
                self.dns_controller.apply()
                interface_after_dns = self.interface_snapshot()
                if interface_after_dns != interface_before_dns:
                    raise TeatherError(
                        "networkmanager-route-mutation",
                        "NetworkManager changed Teather's externally owned address or routes",
                    )
                self.dns_probe()
                self._dns_ready = True
                self._active_id = selected_id
                self._active_serial = serial
                self._state = "connected"
                self._message = "Connected; Teather DNS is ready and Wi-Fi may be disabled manually"
                return self._emit_status()
            except Exception as error:
                cleanup_errors: list[str] = []
                self._cleanup_tunnel_dns(cleanup_errors)
                if local_port is not None and serial is not None:
                    try:
                        self.adb.remove_forward(serial, local_port)
                    except Exception:
                        cleanup_errors.append("adb-forward")
                if android_started and serial is not None:
                    try:
                        self.adb.stop_relay(serial)
                    except Exception:
                        cleanup_errors.append("android-relay")
                if cleanup_errors and selected_id and (local_port is not None or android_started):
                    try:
                        self.journal.save(Ownership(selected_id, local_port, android_started))
                    except Exception:
                        cleanup_errors.append("ownership-journal")
                elif not cleanup_errors:
                    try:
                        self.journal.clear()
                    except Exception:
                        cleanup_errors.append("ownership-journal")
                self._tunnel = None
                self._state = "error"
                if cleanup_errors:
                    self._error_category = "recovery-pending"
                    self._message = (
                        f"{error}; cleanup could not be verified for " + ", ".join(cleanup_errors) +
                        "; run teather recover"
                    )
                    error = TeatherError("recovery-pending", self._message)
                else:
                    self._error_category = getattr(error, "category", "internal-error")
                    self._message = str(error)
                self._emit_status()
                raise error

    def disconnect(self) -> dict:
        with self._lock:
            ownership = self.journal.load()
            cleanup_errors: list[str] = []
            self._cleanup_tunnel_dns(cleanup_errors)
            serial = self._active_serial
            if ownership and serial is None:
                try:
                    self.discover()
                    device = self._devices.get(ownership.device_id)
                    serial = device.serial if device else None
                except TeatherError:
                    serial = None
            if ownership:
                if serial is None or self.config.device_id(serial) != ownership.device_id:
                    self._active_id = ""
                    self._active_serial = None
                    self._state = "error"
                    self._error_category = "recovery-pending"
                    self._message = "Owned ADB state is journaled; reconnect that phone and run teather recover"
                    return self._emit_status()
                if ownership.local_port is not None:
                    try:
                        self.adb.remove_forward(serial, ownership.local_port)
                    except Exception:
                        cleanup_errors.append("adb-forward")
                if ownership.android_started:
                    try:
                        self.adb.stop_relay(serial)
                    except Exception:
                        cleanup_errors.append("android-relay")
                if not cleanup_errors:
                    try:
                        self.journal.clear()
                    except Exception:
                        cleanup_errors.append("ownership-journal")
            if cleanup_errors:
                self._active_id = ""
                self._active_serial = None
                self._state = "error"
                self._error_category = "recovery-pending"
                self._message = (
                    "Cleanup could not be verified for " + ", ".join(cleanup_errors) +
                    "; inspect the ownership journal and run teather recover"
                )
                return self._emit_status()
            self._active_id = ""
            self._active_serial = None
            self._state = "disconnected"
            self._error_category = "none"
            self._message = "Disconnected; restore Wi-Fi manually if it is disabled"
            return self._emit_status()

    def recover(self) -> dict:
        with self._lock:
            self.dns_controller.recover()
            ownership = self.journal.load()
            if ownership:
                self.discover()
                device = self._devices.get(ownership.device_id)
                if device:
                    if ownership.local_port is not None:
                        self.adb.remove_forward(device.serial, ownership.local_port)
                    if ownership.android_started:
                        self.adb.stop_relay(device.serial)
                    self.journal.clear()
            result = self.diagnose()
            result["recovery_pending"] = bool(self.journal.load())
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

    def maybe_auto_connect(self) -> None:
        if self._state not in {"disconnected", "detected"}:
            return
        devices = self.discover()
        eligible = []
        for device in devices:
            if device["connected"] and device["approved"] and device["auto_connect"]:
                raw = self._devices[device["device_id"]]
                if self.adb.status(raw.serial).compatible:
                    eligible.append(device["device_id"])
        if len(eligible) == 1:
            self.connect(eligible[0])
        elif len(eligible) > 1:
            self._state = "detected"
            self._error_category = "selection-required"
            self._message = "Multiple auto-connect phones are eligible; select one locally"
            self._emit_status()

    def health_check(self) -> None:
        if self._state != "connected":
            return
        if self._tunnel is None or self._tunnel.poll() is not None:
            self.disconnect()
            if self._state == "disconnected":
                self._state = "error"
                self._error_category = "tunnel-exited"
                self._message = "Tunnel exited; Teather cleaned its owned resources"
                self._emit_status()
            return
        if not self.dns_controller.resolver_is_active():
            self.disconnect()
            self._state = "error"
            self._error_category = "resolver-unavailable"
            self._message = "Teather DNS disappeared; owned state was disconnected and restored"
            self._emit_status()

    def diagnose(self) -> dict:
        issues: list[str] = []
        for executable in ("adb", "pkexec", "/usr/sbin/ip"):
            found = Path(executable).exists() if executable.startswith("/") else any(
                (Path(directory) / executable).exists() for directory in ("/usr/bin", "/bin", str(Path.home() / ".local/bin"))
            )
            if not found:
                issues.append(f"missing-{Path(executable).name}")
        try:
            resolver = self.resolver_path.read_text(encoding="utf-8")
            nameservers = len(parse_nameservers(resolver))
        except OSError:
            nameservers = 0
            issues.append("resolver-unreadable")
        if nameservers == 0:
            issues.append("no-usable-nameserver")
        try:
            networkmanager_version = self.dns_controller.check_supported()
        except TeatherError as error:
            networkmanager_version = "unavailable"
            issues.append(error.category)
        return {
            "ready": not issues,
            "issues": ",".join(issues) if issues else "none",
            "usable_nameservers": nameservers,
            "networkmanager_version": networkmanager_version,
            "dns_integration": "temporary-active-device",
            "dns_ready": self._dns_ready,
            "recovery_guide": "/usr/share/doc/teather/RECOVERY.md.gz",
            "networkmanager_mutation": self._dns_ready,
            "resolver_mutation": self._dns_ready,
            "persistent_networkmanager_mutation": False,
            "direct_resolver_mutation": False,
            "firewall_mutation": False,
        }
