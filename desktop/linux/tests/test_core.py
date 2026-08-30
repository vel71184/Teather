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
from teather.constants import DNS_PRIORITY, DNS_SENTINEL, VIRTUAL_DNS_POOL, VIRTUAL_DNS_ROUTE
from teather.dbus_service import INTROSPECTION_XML
from teather.dns_probe import _answer_address, _query
from teather.errors import TeatherError
from teather.journal import Ownership, OwnershipJournal
from teather.manager import Manager
from teather.networkmanager import NetworkManagerConnection
from teather.preflight import evaluate_routes, parse_nameservers


SERIAL_ONE = "SERIAL-ONE-PRIVATE"
SERIAL_TWO = "SERIAL-TWO-PRIVATE"
PHYSICAL_RESOLVER = "nameserver 10.0.2.3\n"


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
            raise subprocess.TimeoutExpired("tun2proxy", timeout)
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
        self.stderr = io.StringIO("simulated packet-engine failure")

    def wait(self, timeout=None):
        return 1

    def poll(self):
        return 1


class FakeNmConnection:
    """Stand-in for NetworkManagerConnection used by Manager tests."""

    def __init__(self, resolver):
        self.resolver = resolver
        self.armed = None
        self.active = False
        self.recovered = 0

    def preflight(self):
        return None

    def check_supported(self):
        return "1.42.4"

    def activate(self, armed):
        self.armed = armed
        self.active = True
        if armed:
            self.resolver.write_text(PHYSICAL_RESOLVER + f"nameserver {DNS_SENTINEL}\n")

    def connection_is_active(self):
        return self.active

    def deactivate(self):
        if self.armed:
            self.resolver.write_text(PHYSICAL_RESOLVER)
        self.armed = None
        self.active = False

    def recover(self):
        self.recovered += 1
        self.deactivate()


class ActivateFailingNm(FakeNmConnection):
    def activate(self, armed):
        super().activate(armed)
        raise TeatherError("dns-not-ready", "simulated NetworkManager activation timeout")


class FakeNmTransport:
    """Implements NetworkManagerTransport for direct NetworkManagerConnection tests."""

    def __init__(self, resolver, interface_path, *, version="1.42.4", exclusive=False, sticky=False):
        self.resolver = resolver
        self.interface_path = interface_path
        self._version = version
        self.exclusive = exclusive
        self.sticky = sticky
        self.added = []
        self.deactivated = []
        self.deleted = []
        self._armed_pending = False
        self._connections = {}
        self._active = {}

    def version(self):
        return self._version

    def add_connection(self, connection):
        self.added.append(connection)
        settings_path = "/org/freedesktop/NetworkManager/Settings/9"
        self._armed_pending = "dns-data" in connection["ipv4"]
        self._connections[settings_path] = {
            "connection": {"id": "teather0", "type": "tun"},
            "tun": {"owner": str(os.getuid())},
        }
        return settings_path

    def activate_connection(self, settings_path):
        active_path = "/org/freedesktop/NetworkManager/ActiveConnection/9"
        self.interface_path.mkdir(exist_ok=True)
        if self._armed_pending:
            if self.exclusive:
                self.resolver.write_text(f"nameserver {DNS_SENTINEL}\n")
            else:
                self.resolver.write_text(PHYSICAL_RESOLVER + f"nameserver {DNS_SENTINEL}\n")
        self._active[active_path] = settings_path
        return active_path

    def active_state(self, _active_path):
        return 2

    def device_path(self, _interface):
        if self.interface_path.exists():
            return "/org/freedesktop/NetworkManager/Devices/7"
        raise TeatherError("networkmanager-unavailable", "no teather0 device")

    def device_active_connection(self, _device_path):
        return next(iter(self._active), "/")

    def active_connection_settings(self, active_path):
        return self._active.get(active_path, "/")

    def list_connections(self):
        return list(self._connections)

    def connection_settings(self, settings_path):
        return self._connections.get(settings_path, {"connection": {}})

    def deactivate(self, active_path):
        self.deactivated.append(active_path)
        if not self.sticky:
            self.resolver.write_text(PHYSICAL_RESOLVER)
            if self.interface_path.exists():
                self.interface_path.rmdir()
        self._active.pop(active_path, None)

    def delete_connection(self, settings_path):
        self.deleted.append(settings_path)
        self._connections.pop(settings_path, None)


def make_nm(resolver, interface_path, **transport_kwargs):
    return NetworkManagerConnection(
        resolver_path=resolver,
        interface_path=interface_path,
        transport=FakeNmTransport(resolver, interface_path, **transport_kwargs),
        timeout=0.2,
    )


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

    def test_auto_failover_defaults_on_and_persists(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config" / "config.json"
            store = ConfigStore(path)
            self.assertTrue(store.auto_failover())
            self.assertFalse(store.set_auto_failover(False))
            self.assertFalse(ConfigStore(path).auto_failover())

    def test_config_without_failover_key_still_loads(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "config.json"
            path.write_text('{"schema":1,"salt":"AAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAAA=","devices":{}}')
            path.chmod(0o600)
            self.assertTrue(ConfigStore(path).auto_failover())

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
    def test_user_service_drops_privilege_and_keeps_sandbox(self):
        service = (
            Path(__file__).resolve().parents[3] / "packaging" / "systemd" / "teather.service"
        ).read_text(encoding="utf-8")
        directives = {
            line.strip() for line in service.splitlines()
            if line.strip() and not line.lstrip().startswith("#")
        }
        self.assertIn("NoNewPrivileges=yes", directives)
        self.assertNotIn("NoNewPrivileges=no", directives)
        self.assertIn("ProtectSystem=strict", directives)
        self.assertIn("ProtectHome=read-only", directives)

    def test_no_privileged_helper_or_polkit_action_is_shipped(self):
        repo = Path(__file__).resolve().parents[3]
        self.assertFalse((repo / "desktop/linux/helper").exists())
        self.assertFalse((repo / "packaging/polkit").exists())
        build = (repo / "packaging/scripts/build-deb.sh").read_text(encoding="utf-8")
        self.assertNotIn("teather-helper", build)
        self.assertNotIn("pkexec", build)

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
        sentinel_half = json.dumps([{"dst": "198.19.0.0/16", "dev": "eth0"}, {"dst": "default", "dev": "eth0"}])
        self.assertEqual(evaluate_routes(sentinel_half).category, "route-collision")
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
        command = Manager(config=_scratch_config()).\
            _tunnel_command(45678)
        self.assertIn("--virtual-dns-pool", command)
        self.assertIn(VIRTUAL_DNS_POOL, command)
        self.assertIn("teather0", command)

    def test_dns_priority_is_additive_not_exclusive(self):
        # A positive priority is non-exclusive: NetworkManager keeps every other
        # resolver ahead of Teather's while they are present.
        self.assertGreater(DNS_PRIORITY, 0)


class NetworkManagerConnectionTests(unittest.TestCase):
    def test_armed_activation_is_additive_and_reversible(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resolver = root / "resolv.conf"
            resolver.write_text(PHYSICAL_RESOLVER)
            nm = make_nm(resolver, root / "teather0")
            nm.preflight()
            nm.activate(armed=True)
            servers = parse_nameservers(resolver.read_text())
            self.assertEqual(servers[0], "10.0.2.3")
            self.assertIn(DNS_SENTINEL, resolver.read_text())
            self.assertTrue(nm.connection_is_active())
            connection = nm.transport.added[0]
            self.assertEqual(connection["ipv4"]["dns-data"].unpack(), [DNS_SENTINEL])
            self.assertEqual(connection["ipv4"]["dns-priority"].unpack(), DNS_PRIORITY)
            self.assertEqual(connection["tun"]["pi"].unpack(), False)
            self.assertEqual(connection["tun"]["owner"].unpack(), str(os.getuid()))
            nm.deactivate()
            self.assertNotIn(DNS_SENTINEL, resolver.read_text())

    def test_dormant_activation_adds_no_route_or_dns(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resolver = root / "resolv.conf"
            resolver.write_text(PHYSICAL_RESOLVER)
            nm = make_nm(resolver, root / "teather0")
            nm.preflight()
            nm.activate(armed=False)
            self.assertNotIn(DNS_SENTINEL, resolver.read_text())
            connection = nm.transport.added[0]
            self.assertNotIn("dns-data", connection["ipv4"])
            self.assertEqual(connection["ipv4"]["never-default"].unpack(), True)

    def test_exclusive_dns_result_fails_closed(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resolver = root / "resolv.conf"
            resolver.write_text(PHYSICAL_RESOLVER)
            nm = make_nm(resolver, root / "teather0", exclusive=True)
            nm.preflight()
            with self.assertRaises(TeatherError) as caught:
                nm.activate(armed=True)
            self.assertEqual(caught.exception.category, "dns-exclusive")

    def test_old_networkmanager_is_refused(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resolver = root / "resolv.conf"
            resolver.write_text(PHYSICAL_RESOLVER)
            nm = make_nm(resolver, root / "teather0", version="1.40.2")
            with self.assertRaises(TeatherError) as caught:
                nm.preflight()
            self.assertEqual(caught.exception.category, "networkmanager-version")

    def test_teardown_reports_dns_residue(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resolver = root / "resolv.conf"
            resolver.write_text(PHYSICAL_RESOLVER)
            nm = make_nm(resolver, root / "teather0", sticky=True)
            nm.preflight()
            nm.activate(armed=True)
            with self.assertRaises(TeatherError) as caught:
                nm.deactivate()
            self.assertIn(caught.exception.category, {"dns-residue", "interface-residue"})

    def test_preflight_refuses_a_preexisting_interface(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resolver = root / "resolv.conf"
            resolver.write_text(PHYSICAL_RESOLVER)
            interface = root / "teather0"
            interface.mkdir()
            nm = make_nm(resolver, interface)
            with self.assertRaises(TeatherError) as caught:
                nm.preflight()
            self.assertEqual(caught.exception.category, "interface-collision")

    def test_recover_removes_a_teather_owned_stale_connection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resolver = root / "resolv.conf"
            resolver.write_text(PHYSICAL_RESOLVER)
            interface = root / "teather0"
            nm = make_nm(resolver, interface)
            nm.preflight()
            nm.activate(armed=True)
            nm._active_path = ""  # simulate a daemon crash that lost its handles
            nm._settings_path = ""
            nm.recover()
            self.assertNotIn(DNS_SENTINEL, resolver.read_text())
            self.assertTrue(nm.transport.deleted)

    def test_recover_refuses_a_foreign_teather0(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resolver = root / "resolv.conf"
            resolver.write_text(PHYSICAL_RESOLVER)
            interface = root / "teather0"
            interface.mkdir()
            transport = FakeNmTransport(resolver, interface)
            transport._connections["/foreign"] = {
                "connection": {"id": "teather0", "type": "tun"},
                "tun": {"owner": "0"},
            }
            transport._active["/foreign-active"] = "/foreign"
            nm = NetworkManagerConnection(
                resolver_path=resolver, interface_path=interface, transport=transport, timeout=0.1,
            )
            with self.assertRaises(TeatherError) as caught:
                nm.recover()
            self.assertEqual(caught.exception.category, "ambiguous-interface")


def _scratch_config():
    directory = tempfile.mkdtemp()
    return ConfigStore(Path(directory) / "config" / "config.json")


class InterfaceSnapshotTests(unittest.TestCase):
    def test_snapshot_matches_armed_and_dormant_route_sets(self):
        address = json.dumps([{
            "ifname": "teather0",
            "addr_info": [{"family": "inet", "local": "192.0.2.1", "prefixlen": 32}],
        }])
        armed_routes = json.dumps([
            {"dst": "198.18.0.0/15", "dev": "teather0"},
            {"dst": "default", "dev": "teather0", "metric": 32000},
        ])
        dormant_routes = json.dumps([{"dst": "198.18.0.0/15", "dev": "teather0"}])
        manager = Manager(config=_scratch_config())
        with patch.object(manager, "_run_json", side_effect=[address, armed_routes]):
            self.assertTrue(manager._system_interface_snapshot(armed=True))
        with patch.object(manager, "_run_json", side_effect=[address, dormant_routes]):
            self.assertTrue(manager._system_interface_snapshot(armed=False))
        with patch.object(manager, "_run_json", side_effect=[address, dormant_routes]):
            with self.assertRaises(TeatherError) as caught:
                manager._system_interface_snapshot(armed=True)
        self.assertEqual(caught.exception.category, "tunnel-start")


class ManagerTests(unittest.TestCase):
    def make_manager(self, directory, adb, nm_factory=FakeNmConnection):
        config = ConfigStore(Path(directory) / "config" / "config.json")
        journal = OwnershipJournal(Path(directory) / "runtime" / "journal.json")
        resolver = Path(directory) / "resolv.conf"
        resolver.write_text(PHYSICAL_RESOLVER)
        manager = Manager(
            config=config, journal=journal, adb=adb, resolver_path=resolver,
            process_factory=FakeProcess,
            nm=nm_factory(resolver),
            dns_probe=lambda: {"udp": "198.18.0.1", "tcp": "198.18.0.1"},
            interface_snapshot=lambda armed: "stable-interface-state",
            snapshot_timeout=0.2,
        )
        manager.preflight = lambda: None
        return manager

    def _approve_one(self, manager):
        device_id = manager.discover()[0]["device_id"]
        manager.approve_device(device_id)
        return device_id

    def test_multiple_approved_devices_require_selection(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb(multiple=True)
            manager = self.make_manager(directory, adb)
            for device in manager.discover():
                manager.approve_device(device["device_id"])
            with self.assertRaises(TeatherError) as caught:
                manager.connect()
            self.assertEqual(caught.exception.category, "selection-required")

    def test_attach_to_manual_relay_does_not_stop_android(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            self.assertEqual(manager.connect(device_id)["state"], "connected")
            status = manager.get_status()
            self.assertTrue(status["dns_ready"])
            self.assertTrue(status["failover_armed"])
            self.assertEqual(status["api_version"], 2)
            manager.disconnect()
            self.assertFalse(manager.get_status()["dns_ready"])
            self.assertEqual(adb.started, [])
            self.assertEqual(adb.stopped, [])
            self.assertEqual(adb.removed, [(SERIAL_ONE, 45678)])

    def test_dormant_connect_when_failover_disabled(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            manager.config.set_auto_failover(False)
            device_id = self._approve_one(manager)
            manager.connect(device_id)
            status = manager.get_status()
            self.assertEqual(status["state"], "connected")
            self.assertFalse(status["failover_armed"])
            self.assertFalse(status["dns_ready"])
            self.assertNotIn(DNS_SENTINEL, manager.resolver_path.read_text())

    def test_toggling_failover_while_connected_reestablishes_armed(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            manager.config.set_auto_failover(False)
            device_id = self._approve_one(manager)
            manager.connect(device_id)
            self.assertFalse(manager.get_status()["failover_armed"])
            manager.set_auto_failover(True)
            self.assertTrue(manager.get_status()["failover_armed"])
            self.assertIn(DNS_SENTINEL, manager.resolver_path.read_text())

    def test_incompatible_manual_relay_is_refused_without_restart(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb({SERIAL_ONE: compatible_status(configured_upstream="wifi")})
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            with self.assertRaises(TeatherError) as caught:
                manager.connect(device_id)
            self.assertEqual(caught.exception.category, "android-incompatible")
            self.assertEqual(adb.started, [])
            self.assertEqual(adb.forwards, [])

    def test_linux_started_relay_is_stopped_on_disconnect(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb({SERIAL_ONE: AndroidStatus()})
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            manager.connect(device_id)
            manager.disconnect()
            self.assertEqual(adb.started, [SERIAL_ONE])
            self.assertEqual(adb.stopped, [SERIAL_ONE])

    def test_auto_connect_never_starts_stopped_relay(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb({SERIAL_ONE: AndroidStatus()})
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            manager.set_auto_connect(device_id, True)
            manager.maybe_auto_connect()
            self.assertEqual(manager.get_status()["state"], "disconnected")
            self.assertEqual(adb.started, [])

    def test_failed_disconnect_retains_ownership_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb(fail_remove=True)
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            manager.connect(device_id)
            result = manager.disconnect()
            self.assertEqual(result["error_category"], "recovery-pending")
            self.assertIsNotNone(manager.journal.load())

    def test_failed_connect_cleanup_retains_ownership_journal(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb(fail_remove=True)
            manager = self.make_manager(directory, adb)
            manager.process_factory = FailedProcess
            device_id = self._approve_one(manager)
            with self.assertRaises(TeatherError) as caught:
                manager.connect(device_id)
            self.assertEqual(caught.exception.category, "recovery-pending")
            self.assertIsNotNone(manager.journal.load())

    def test_uncertain_android_start_is_journaled_without_a_forward(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb({SERIAL_ONE: AndroidStatus()}, fail_start=True, fail_stop=True)
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            with self.assertRaises(TeatherError) as caught:
                manager.connect(device_id)
            self.assertEqual(caught.exception.category, "recovery-pending")
            self.assertEqual(manager.journal.load(), Ownership(device_id, None, True))

    def test_existing_journal_blocks_a_new_connection(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            manager.journal.save(Ownership(device_id, 45678, False))
            with self.assertRaises(TeatherError) as caught:
                manager.connect(device_id)
            self.assertEqual(caught.exception.category, "recovery-pending")
            self.assertEqual(adb.forwards, [])

    def test_nm_activation_failure_restores_every_owned_resource(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb, nm_factory=ActivateFailingNm)
            device_id = self._approve_one(manager)
            with self.assertRaises(TeatherError) as caught:
                manager.connect(device_id)
            self.assertEqual(caught.exception.category, "dns-not-ready")
            self.assertEqual(manager.resolver_path.read_text(), PHYSICAL_RESOLVER)
            self.assertEqual(adb.removed, [(SERIAL_ONE, 45678)])
            self.assertIsNone(manager.journal.load())
            self.assertIsNone(manager._tunnel)

    def test_interface_parity_failure_restores_every_owned_resource(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)

            def bad_snapshot(_armed):
                raise TeatherError("tunnel-start", "unexpected teather0 routes")

            manager.interface_snapshot = bad_snapshot
            device_id = self._approve_one(manager)
            with self.assertRaises(TeatherError) as caught:
                manager.connect(device_id)
            self.assertEqual(caught.exception.category, "tunnel-start")
            self.assertEqual(manager.resolver_path.read_text(), PHYSICAL_RESOLVER)
            self.assertEqual(adb.removed, [(SERIAL_ONE, 45678)])
            self.assertIsNone(manager.journal.load())

    def test_dns_probe_failure_restores_every_owned_resource(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)

            def fail_probe():
                raise TeatherError("dns-readiness", "simulated UDP/TCP readiness failure")

            manager.dns_probe = fail_probe
            device_id = self._approve_one(manager)
            with self.assertRaises(TeatherError) as caught:
                manager.connect(device_id)
            self.assertEqual(caught.exception.category, "dns-readiness")
            self.assertEqual(manager.resolver_path.read_text(), PHYSICAL_RESOLVER)
            self.assertEqual(adb.removed, [(SERIAL_ONE, 45678)])
            self.assertIsNone(manager.journal.load())

    def test_tunnel_exit_error_survives_cleanup(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            manager.connect(device_id)
            manager._tunnel.running = False
            manager.health_check()
            self.assertEqual(manager.get_status()["error_category"], "tunnel-exited")

    def test_connection_loss_disconnects_and_restores(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            manager.connect(device_id)
            manager.nm.active = False
            manager.health_check()
            self.assertEqual(manager.get_status()["error_category"], "connection-lost")
            self.assertEqual(manager.resolver_path.read_text(), PHYSICAL_RESOLVER)

    def test_connection_loss_does_not_hide_cleanup_failure(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            manager.connect(device_id)
            manager.nm.active = False
            adb.fail_remove = True
            manager.health_check()
            self.assertEqual(manager.get_status()["error_category"], "recovery-pending")
            self.assertIsNotNone(manager.journal.load())

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
            "RenameDevice", "ForgetDevice", "SetAutoConnect", "SetAutoFailover", "Diagnose",
        ):
            self.assertIn(f'name="{method}"', INTROSPECTION_XML)
        parser = build_parser()
        for command in ("status", "devices", "connect", "disconnect", "autoconnect", "failover", "diagnose", "recover"):
            with self.subTest(command=command):
                arguments = [command]
                if command == "autoconnect":
                    arguments += ["on", "a" * 64]
                elif command == "failover":
                    arguments += ["on"]
                parser.parse_args(arguments)


if __name__ == "__main__":
    unittest.main()
