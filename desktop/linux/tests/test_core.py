from __future__ import annotations

import io
import ipaddress
import json
import os
import stat
import struct
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from teather.adb import AdbClient, AdbDevice
from teather.android_status import AndroidStatus, parse_android_status
from teather.cli import build_parser
from teather.config import ConfigStore
from teather.constants import DNS_SENTINEL, VIRTUAL_DNS_POOL, VIRTUAL_DNS_ROUTE
from teather.dbus_service import INTROSPECTION_XML
from teather.dns_probe import _answer_address, _query
from teather.errors import TeatherError
from teather.journal import Ownership, OwnershipJournal
from teather.manager import Manager
from teather.networkmanager import NetworkManagerDns
from teather.preflight import evaluate_routes, parse_nameservers


SERIAL_ONE = "SERIAL-ONE-PRIVATE"
SERIAL_TWO = "SERIAL-TWO-PRIVATE"


def compatible_status(**changes):
    values = {
        "schema": 1,
        "lifecycle": "running",
        "bound_port": 1080,
        "configured_port": 1080,
        "configured_upstream": "cellular",
    }
    values.update(changes)
    return AndroidStatus(**values)


class FakeAdb:
    def __init__(
        self, states=None, multiple=False, fail_remove=False, fail_stop=False,
        fail_start=False,
    ):
        self.states = states or {SERIAL_ONE: compatible_status()}
        self.multiple = multiple
        self.fail_remove = fail_remove
        self.fail_stop = fail_stop
        self.fail_start = fail_start
        self.started = []
        self.stopped = []
        self.removed = []
        self.forwards = []

    def devices(self):
        result = [AdbDevice(SERIAL_ONE, "Phone one")]
        if self.multiple:
            result.append(AdbDevice(SERIAL_TWO, "Phone two"))
            self.states.setdefault(SERIAL_TWO, compatible_status())
        return result

    def status(self, serial):
        return self.states[serial]

    def package_installed(self, _serial):
        return True

    def start_relay(self, serial):
        self.started.append(serial)
        if self.fail_start:
            raise TeatherError("adb-failed", "simulated start uncertainty")
        self.states[serial] = compatible_status()
        return self.states[serial]

    def stop_relay(self, serial):
        self.stopped.append(serial)
        if self.fail_stop:
            raise TeatherError("adb-failed", "simulated stop failure")

    def add_forward(self, serial):
        self.forwards.append(serial)
        return 45678

    def remove_forward(self, serial, port):
        self.removed.append((serial, port))
        if self.fail_remove:
            raise TeatherError("adb-failed", "simulated forward cleanup failure")


class FakeProcess:
    def __init__(self, *_args, **_kwargs):
        self.running = True
        self.stderr = None

    def wait(self, timeout=None):
        if self.running and timeout == 0.25:
            raise subprocess.TimeoutExpired("helper", timeout)
        self.running = False
        return 0

    def poll(self):
        return None if self.running else 0

    def send_signal(self, _signal):
        self.running = False

    def kill(self):
        self.running = False


class FailedProcess(FakeProcess):
    def __init__(self, *_args, **_kwargs):
        super().__init__()
        self.running = False
        self.stderr = io.StringIO("simulated helper failure")

    def wait(self, timeout=None):
        return 1

    def poll(self):
        return 1


class FakeDnsController:
    def __init__(self, resolver):
        self.resolver = resolver
        self.applied = False

    def preflight(self):
        return None

    def check_supported(self):
        return "1.42.4"

    def apply(self):
        self.resolver.write_text("nameserver 198.19.0.1\n")
        self.applied = True

    def restore_while_active(self):
        if self.applied:
            self.resolver.write_text("nameserver 1.1.1.1\n")
        self.applied = False

    def ensure_no_residue(self):
        if "198.19.0.1" in self.resolver.read_text():
            raise TeatherError("dns-residue", "simulated residue")

    def recover(self):
        self.ensure_no_residue()

    def resolver_is_active(self):
        return self.resolver.read_text() == "nameserver 198.19.0.1\n"


class FakeNetworkManagerTransport:
    def __init__(self, resolver):
        from gi.repository import GLib

        self.resolver = resolver
        self.settings = {"ipv4": {"method": GLib.Variant("s", "manual")}}
        self.reapplied = []
        self.reloads = 0

    def version(self):
        return "1.42.4"

    def device_for_interface(self, interface):
        self.interface = interface
        return "/org/freedesktop/NetworkManager/Devices/7"

    def get_applied_connection(self, _device_path):
        return self.settings, 41

    def reapply(self, _device_path, settings, version):
        self.reapplied.append((settings, version))
        dns = settings["ipv4"].get("dns-data")
        if dns is not None and dns.unpack() == ["198.19.0.1"]:
            self.resolver.write_text("nameserver 198.19.0.1\n")
        else:
            self.resolver.write_text("nameserver 1.1.1.1\n")

    def reload_dns(self):
        self.reloads += 1
        self.resolver.write_text("nameserver 1.1.1.1\n")


class OldNetworkManagerTransport(FakeNetworkManagerTransport):
    def version(self):
        return "1.40.2"


class StuckNetworkManagerTransport(FakeNetworkManagerTransport):
    def reapply(self, _device_path, settings, version):
        self.reapplied.append((settings, version))
        self.resolver.write_text("nameserver 198.19.0.1\n")


class StorageTests(unittest.TestCase):
    def test_config_hashes_serial_and_uses_mode_0600(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config" / "config.json"
            store = ConfigStore(path)
            first = store.device_id(SERIAL_ONE)
            self.assertEqual(first, store.device_id(SERIAL_ONE))
            self.assertNotIn(SERIAL_ONE, path.read_text())
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)
            store.approve(first, "My phone")
            self.assertNotIn(SERIAL_ONE, path.read_text())

    def test_config_rejects_permissive_mode(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text('{"schema":1,"salt":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=","devices":{}}')
            path.chmod(0o644)
            with self.assertRaises(TeatherError) as caught:
                ConfigStore(path)
            self.assertEqual(caught.exception.category, "unsafe-storage")

    def test_journal_round_trip_has_no_raw_serial(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "runtime" / "ownership.json"
            journal = OwnershipJournal(path)
            ownership = Ownership("a" * 64, 45678, True)
            journal.save(ownership)
            self.assertEqual(journal.load(), ownership)
            self.assertNotIn("SERIAL", path.read_text())
            self.assertEqual(stat.S_IMODE(path.stat().st_mode), 0o600)

    def test_journal_can_track_an_android_start_without_a_forward(self):
        with tempfile.TemporaryDirectory() as directory:
            journal = OwnershipJournal(Path(directory) / "runtime" / "ownership.json")
            ownership = Ownership("b" * 64, None, True)
            journal.save(ownership)
            self.assertEqual(journal.load(), ownership)


class StatusAndPreflightTests(unittest.TestCase):
    def test_user_service_allows_the_intended_pkexec_boundary(self):
        service = (
            Path(__file__).resolve().parents[3] / "packaging" / "systemd" / "teather.service"
        ).read_text(encoding="utf-8")
        directives = {
            line.strip() for line in service.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        self.assertIn("NoNewPrivileges=no", directives)
        self.assertNotIn("NoNewPrivileges=yes", directives)
        self.assertIn("ProtectSystem=strict", service)
        self.assertIn("ProtectHome=read-only", service)

    def test_adb_errors_redact_the_raw_serial(self):
        result = subprocess.CompletedProcess(
            ["adb"], 1, stdout="", stderr=f"device {SERIAL_ONE} unavailable",
        )
        with patch("teather.adb.subprocess.run", return_value=result):
            with self.assertRaises(TeatherError) as caught:
                AdbClient(executable="adb")._run(["shell", "false"], serial=SERIAL_ONE)
        self.assertNotIn(SERIAL_ONE, str(caught.exception))

    def test_status_parser_ignores_surrounding_dumpsys_text(self):
        status = parse_android_status(
            "header\nteather.status.version=1\nlifecycle=running\nbound_port=1080\n"
            "configured_port=1080\nconfigured_upstream=cellular\nbytes_internet_to_client=42\n"
        )
        self.assertTrue(status.compatible)
        self.assertEqual(status.bytes_internet_to_client, 42)

    def test_status_compatibility_includes_requested_upstream(self):
        self.assertFalse(compatible_status(configured_upstream="default").compatible)
        self.assertFalse(compatible_status(configured_port=2080).compatible)

    def test_missing_schema_is_stopped_and_incompatible(self):
        self.assertFalse(parse_android_status("Service not found").compatible)

    def test_route_preflight_accepts_preferred_physical_default(self):
        routes = json.dumps([{"dst": "default", "dev": "wlan0", "metric": 600}])
        self.assertTrue(evaluate_routes(routes).safe)

    def test_route_preflight_refuses_collisions_vpn_and_split_default(self):
        self.assertEqual(evaluate_routes("[]", '[{"ifname":"teather0"}]').category, "interface-collision")
        vpn = json.dumps([{"dst": "default", "dev": "tun0", "metric": 50}])
        self.assertEqual(evaluate_routes(vpn).category, "vpn-active")
        split = json.dumps([{"dst": "0.0.0.0/1", "dev": "eth0"}, {"dst": "default", "dev": "eth0"}])
        self.assertEqual(evaluate_routes(split).category, "split-default")
        overlap = json.dumps([{"dst": "198.0.0.0/8", "dev": "eth0"}, {"dst": "default", "dev": "eth0"}])
        self.assertEqual(evaluate_routes(overlap).category, "route-collision")
        policy = json.dumps([{"priority": 1000, "src": "all", "table": "100"}])
        self.assertEqual(evaluate_routes(json.dumps([{"dst": "default", "dev": "eth0"}]), rule_json=policy).category, "policy-routing")

    def test_nameserver_gate_excludes_loopback(self):
        self.assertEqual(parse_nameservers("nameserver 127.0.0.53\nnameserver 1.1.1.1\n"), ["1.1.1.1"])
        self.assertEqual(parse_nameservers("nameserver ::1\n"), [])
        self.assertEqual(parse_nameservers("nameserver 2001:4860:4860::8888\n"), [])

    def test_dns_probe_accepts_only_addresses_from_the_mapping_pool(self):
        identifier = 0x5445
        query = _query(identifier)
        answer = (
            struct.pack("!HHHHHH", identifier, 0x8180, 1, 1, 0, 0)
            + query[12:]
            + b"\xc0\x0c"
            + struct.pack("!HHIH", 1, 1, 5, 4)
            + ipaddress.ip_address("198.18.0.7").packed
        )
        self.assertEqual(_answer_address(answer, identifier), "198.18.0.7")
        outside = answer[:-4] + ipaddress.ip_address("198.19.0.1").packed
        with self.assertRaises(ValueError):
            _answer_address(outside, identifier)

    def test_dns_sentinel_is_routed_but_never_allocated(self):
        route = ipaddress.ip_network(VIRTUAL_DNS_ROUTE)
        pool = ipaddress.ip_network(VIRTUAL_DNS_POOL)
        sentinel = ipaddress.ip_address(DNS_SENTINEL)
        self.assertIn(sentinel, route)
        self.assertNotIn(sentinel, pool)
        helper = (
            Path(__file__).resolve().parents[1] / "helper" / "teather-helper.c"
        ).read_text(encoding="utf-8")
        self.assertIn('"--virtual-dns-pool", "198.18.0.0/16"', helper)

    def test_networkmanager_dns_is_temporary_and_restorable(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resolver = root / "resolv.conf"
            resolver.write_text("nameserver 1.1.1.1\n")
            interface = root / "teather0"
            interface.mkdir()
            transport = FakeNetworkManagerTransport(resolver)
            controller = NetworkManagerDns(
                resolver_path=resolver,
                interface_path=interface,
                transport=transport,
                timeout=0.1,
            )
            controller.preflight()
            controller.apply()
            self.assertTrue(controller.resolver_is_active())
            settings, version = transport.reapplied[0]
            self.assertEqual(version, 41)
            self.assertEqual(settings["ipv4"]["dns-data"].unpack(), ["198.19.0.1"])
            self.assertEqual(settings["ipv4"]["dns-priority"].unpack(), -32768)
            controller.restore_while_active()
            controller.ensure_no_residue()
            self.assertEqual(resolver.read_text(), "nameserver 1.1.1.1\n")

    def test_networkmanager_refuses_versions_without_preserve_external_ip(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resolver = root / "resolv.conf"
            resolver.write_text("nameserver 1.1.1.1\n")
            controller = NetworkManagerDns(
                resolver_path=resolver,
                interface_path=root / "teather0",
                transport=OldNetworkManagerTransport(resolver),
                timeout=0.1,
            )
            with self.assertRaises(TeatherError) as caught:
                controller.preflight()
            self.assertEqual(caught.exception.category, "networkmanager-version")

    def test_networkmanager_restore_waits_and_reports_residue(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resolver = root / "resolv.conf"
            resolver.write_text("nameserver 1.1.1.1\n")
            interface = root / "teather0"
            interface.mkdir()
            controller = NetworkManagerDns(
                resolver_path=resolver,
                interface_path=interface,
                transport=StuckNetworkManagerTransport(resolver),
                timeout=0.01,
            )
            controller.apply()
            with self.assertRaises(TeatherError) as caught:
                controller.restore_while_active()
            self.assertEqual(caught.exception.category, "dns-residue")

    def test_networkmanager_recovery_regenerates_only_stale_dns(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resolver = root / "resolv.conf"
            resolver.write_text("nameserver 198.19.0.1\n")
            transport = FakeNetworkManagerTransport(resolver)
            controller = NetworkManagerDns(
                resolver_path=resolver,
                interface_path=root / "missing-teather0",
                transport=transport,
                timeout=0.1,
            )
            controller.recover()
            self.assertEqual(transport.reloads, 1)
            self.assertEqual(resolver.read_text(), "nameserver 1.1.1.1\n")


class ManagerTests(unittest.TestCase):
    def make_manager(self, directory, adb):
        config = ConfigStore(Path(directory) / "config" / "config.json")
        journal = OwnershipJournal(Path(directory) / "runtime" / "journal.json")
        resolver = Path(directory) / "resolv.conf"
        resolver.write_text("nameserver 1.1.1.1\n")
        manager = Manager(
            config=config, journal=journal, adb=adb, resolver_path=resolver,
            process_factory=FakeProcess,
            dns_controller=FakeDnsController(resolver),
            dns_probe=lambda: {"udp": "198.18.0.1", "tcp": "198.18.0.1"},
            interface_snapshot=lambda: "stable-interface-state",
        )
        manager.preflight = lambda: None
        return manager

    def test_multiple_approved_devices_require_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb(multiple=True)
            manager = self.make_manager(directory, adb)
            devices = manager.discover()
            for device in devices:
                manager.approve_device(device["device_id"])
            with self.assertRaises(TeatherError) as caught:
                manager.connect()
            self.assertEqual(caught.exception.category, "selection-required")

    def test_attach_to_manual_relay_does_not_stop_android(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            device_id = manager.discover()[0]["device_id"]
            manager.approve_device(device_id)
            self.assertEqual(manager.connect(device_id)["state"], "connected")
            self.assertTrue(manager.get_status()["dns_ready"])
            self.assertEqual(manager.get_status()["api_version"], 2)
            manager.disconnect()
            self.assertFalse(manager.get_status()["dns_ready"])
            self.assertEqual(adb.started, [])
            self.assertEqual(adb.stopped, [])
            self.assertEqual(adb.removed, [(SERIAL_ONE, 45678)])

    def test_incompatible_manual_relay_is_refused_without_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb({SERIAL_ONE: compatible_status(configured_upstream="wifi")})
            manager = self.make_manager(directory, adb)
            device_id = manager.discover()[0]["device_id"]
            manager.approve_device(device_id)
            with self.assertRaises(TeatherError) as caught:
                manager.connect(device_id)
            self.assertEqual(caught.exception.category, "android-incompatible")
            self.assertEqual(adb.started, [])
            self.assertEqual(adb.forwards, [])

    def test_linux_started_relay_is_stopped_on_disconnect(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb({SERIAL_ONE: AndroidStatus()})
            manager = self.make_manager(directory, adb)
            device_id = manager.discover()[0]["device_id"]
            manager.approve_device(device_id)
            manager.connect(device_id)
            manager.disconnect()
            self.assertEqual(adb.started, [SERIAL_ONE])
            self.assertEqual(adb.stopped, [SERIAL_ONE])

    def test_auto_connect_never_starts_stopped_relay(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb({SERIAL_ONE: AndroidStatus()})
            manager = self.make_manager(directory, adb)
            device_id = manager.discover()[0]["device_id"]
            manager.approve_device(device_id)
            manager.set_auto_connect(device_id, True)
            manager.maybe_auto_connect()
            self.assertEqual(manager.get_status()["state"], "disconnected")
            self.assertEqual(adb.started, [])

    def test_auto_connect_does_not_repeat_after_an_error(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            device_id = manager.discover()[0]["device_id"]
            manager.approve_device(device_id)
            manager.set_auto_connect(device_id, True)
            manager._state = "error"
            manager.maybe_auto_connect()
            self.assertEqual(adb.forwards, [])

    def test_failed_disconnect_retains_ownership_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb(fail_remove=True)
            manager = self.make_manager(directory, adb)
            device_id = manager.discover()[0]["device_id"]
            manager.approve_device(device_id)
            manager.connect(device_id)
            result = manager.disconnect()
            self.assertEqual(result["error_category"], "recovery-pending")
            self.assertIsNotNone(manager.journal.load())

    def test_failed_connect_cleanup_retains_ownership_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb(fail_remove=True)
            manager = self.make_manager(directory, adb)
            manager.process_factory = FailedProcess
            device_id = manager.discover()[0]["device_id"]
            manager.approve_device(device_id)
            with self.assertRaises(TeatherError) as caught:
                manager.connect(device_id)
            self.assertEqual(caught.exception.category, "recovery-pending")
            self.assertIsNotNone(manager.journal.load())

    def test_uncertain_android_start_is_journaled_without_a_forward(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb(
                {SERIAL_ONE: AndroidStatus()}, fail_start=True, fail_stop=True,
            )
            manager = self.make_manager(directory, adb)
            device_id = manager.discover()[0]["device_id"]
            manager.approve_device(device_id)
            with self.assertRaises(TeatherError) as caught:
                manager.connect(device_id)
            self.assertEqual(caught.exception.category, "recovery-pending")
            self.assertEqual(manager.journal.load(), Ownership(device_id, None, True))

    def test_existing_journal_blocks_a_new_connection(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            device_id = manager.discover()[0]["device_id"]
            manager.approve_device(device_id)
            manager.journal.save(Ownership(device_id, 45678, False))
            with self.assertRaises(TeatherError) as caught:
                manager.connect(device_id)
            self.assertEqual(caught.exception.category, "recovery-pending")
            self.assertEqual(adb.forwards, [])

    def test_tunnel_exit_error_survives_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            device_id = manager.discover()[0]["device_id"]
            manager.approve_device(device_id)
            manager.connect(device_id)
            manager._tunnel.running = False
            manager.health_check()
            self.assertEqual(manager.get_status()["error_category"], "tunnel-exited")

    def test_recovery_retains_journal_until_phone_returns(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            device_id = manager.config.device_id(SERIAL_ONE)
            manager.journal.save(Ownership(device_id, 45678, True))
            adb.devices = lambda: []
            self.assertTrue(manager.recover()["recovery_pending"])
            self.assertIsNotNone(manager.journal.load())


class InterfaceParityTests(unittest.TestCase):
    def test_dbus_methods_match_cli_surface(self):
        for method in (
            "GetStatus", "ListDevices", "Connect", "Disconnect", "ApproveDevice",
            "RenameDevice", "ForgetDevice", "SetAutoConnect", "Diagnose",
        ):
            self.assertIn(f'name="{method}"', INTROSPECTION_XML)
        parser = build_parser()
        for command in ("status", "devices", "connect", "disconnect", "autoconnect", "diagnose", "recover"):
            with self.subTest(command=command):
                arguments = [command]
                if command == "autoconnect":
                    arguments += ["on", "a" * 64]
                parser.parse_args(arguments)


if __name__ == "__main__":
    unittest.main()
