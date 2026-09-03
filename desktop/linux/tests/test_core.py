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
from teather.constants import (
    DNS_PRIORITY,
    DNS_SENTINEL,
    UDPGW_SENTINEL,
    VIRTUAL_DNS_POOL,
    VIRTUAL_DNS_ROUTE,
)
from teather.dbus_service import INTROSPECTION_XML
from teather.dns_probe import _answer_address, _query
from teather.errors import TeatherError
from teather.journal import Ownership, OwnershipJournal
from teather.logging_setup import configure_logging, log_path
from teather.manager import _AUTOCONNECT_MAX_TRIES, _RELAY_PROBE_EVERY, Manager
from teather.networkmanager import NetworkManagerConnection
from teather.preflight import evaluate_routes, parse_nameservers


SERIAL_ONE = "SERIAL-ONE-PRIVATE"
SERIAL_TWO = "SERIAL-TWO-PRIVATE"
PHYSICAL_RESOLVER = "nameserver 10.0.2.3\n"


def compatible_status(**changes):
    values = {
        "schema": 2,
        "lifecycle": "running",
        "bound_port": 1080,
        "configured_port": 1080,
        "configured_upstream": "cellular",
        "secret": "0123456789abcdef0123456789abcdef",
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
        self.reconfigured = []
        self.removed = []
        self.forwards = []
        self.upstreams = []
        self.present = True          # False simulates the phone being unplugged
        self.forward_ports = []       # local ports currently "forwarded"
        self.app_version = (4, "0.1.0-p1.2")  # None simulates the app not installed
        self.installs = []            # (serial, apk_path) for each install_apk call
        self.fail_install = False

    def devices(self):
        if not self.present:
            return []
        result = [AdbDevice(SERIAL_ONE, "Phone one")]
        if self.multiple:
            result.append(AdbDevice(SERIAL_TWO, "Phone two"))
            self.states.setdefault(SERIAL_TWO, compatible_status())
        return result

    def list_forwards(self, _serial):
        return list(self.forward_ports)

    def status(self, serial):
        return self.states[serial]

    def package_installed(self, _serial):
        return self.app_version is not None

    def installed_version(self, _serial):
        return self.app_version

    def install_apk(self, serial, apk_path):
        self.installs.append((serial, apk_path))
        if self.fail_install:
            raise TeatherError("android-install-signature", "simulated key mismatch")
        self.app_version = (99, "0.1.0-test")

    def start_relay(self, serial, upstream="cellular"):
        self.started.append(serial)
        self.upstreams.append(upstream)
        if self.fail_start:
            raise TeatherError("adb-failed", "simulated start uncertainty")
        self.states[serial] = compatible_status(configured_upstream=upstream)
        return self.states[serial]

    def stop_relay(self, serial):
        self.stopped.append(serial)
        if self.fail_stop:
            raise TeatherError("adb-failed", "simulated stop failure")

    def reconfigure_relay(self, serial, upstream):
        self.reconfigured.append((serial, upstream))
        self.upstreams.append(upstream)
        self.states[serial] = compatible_status(configured_upstream=upstream)
        return self.states[serial]

    def add_forward(self, serial):
        self.forwards.append(serial)
        self.forward_ports = [45678]
        return 45678

    def remove_forward(self, serial, port):
        self.removed.append((serial, port))
        if self.fail_remove:
            raise TeatherError("adb-failed", "simulated forward cleanup failure")
        self.forward_ports = [p for p in self.forward_ports if p != port]


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
        self.connectivity_rechecks = 0

    def preflight(self):
        return None

    def recheck_connectivity(self):
        self.connectivity_rechecks += 1

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

    def check_connectivity(self):
        self.connectivity_checks = getattr(self, "connectivity_checks", 0) + 1
        return 4  # NM_CONNECTIVITY_FULL

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

    def reload_dns(self):
        self.dns_reloads = getattr(self, "dns_reloads", 0) + 1
        if not self.resolver.exists():
            return
        kept = [
            line for line in self.resolver.read_text().splitlines()
            if line.strip() != f"nameserver {DNS_SENTINEL}"
        ]
        self.resolver.write_text("".join(f"{line}\n" for line in kept))


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

    def test_configure_logging_is_idempotent_and_writes_a_private_log(self):
        import logging as _logging
        import teather.logging_setup as ls
        root = _logging.getLogger("teather")
        saved = (list(root.handlers), root.level, root.propagate, ls._configured)

        def restore():
            root.handlers[:] = saved[0]
            root.setLevel(saved[1])
            root.propagate = saved[2]
            ls._configured = saved[3]

        self.addCleanup(restore)
        with tempfile.TemporaryDirectory() as directory:
            with patch.dict(os.environ, {"XDG_STATE_HOME": directory, "STATE_DIRECTORY": ""}, clear=False):
                root.handlers[:] = []
                ls._configured = False
                first = configure_logging()
                second = configure_logging()  # no duplicate handlers, returns None
                self.assertEqual(first, log_path())
                self.assertIsNone(second)
                self.assertTrue(first.exists())
                self.assertEqual(stat.S_IMODE(first.stat().st_mode), 0o600)
                self.assertEqual(len(root.handlers), 2)

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

    def test_remove_forward_tolerates_an_already_gone_listener(self):
        result = subprocess.CompletedProcess(
            ["adb"], 1, stdout="", stderr="error: listener 'tcp:41234' not found",
        )
        with patch("teather.adb.subprocess.run", return_value=result):
            AdbClient(executable="adb").remove_forward(SERIAL_ONE, 41234)

    def test_remove_forward_still_raises_on_a_real_failure(self):
        result = subprocess.CompletedProcess(
            ["adb"], 1, stdout="", stderr="error: adb server is out of date",
        )
        with patch("teather.adb.subprocess.run", return_value=result):
            with self.assertRaises(TeatherError):
                AdbClient(executable="adb").remove_forward(SERIAL_ONE, 41234)

    def test_list_forwards_parses_only_this_devices_tcp_forwards(self):
        listing = (
            f"{SERIAL_ONE} tcp:39251 tcp:1080\n"
            f"OTHER-DEVICE tcp:40000 tcp:1080\n"
            f"{SERIAL_ONE} localabstract:x localabstract:y\n"
        )
        result = subprocess.CompletedProcess(["adb"], 0, stdout=listing, stderr="")
        with patch("teather.adb.subprocess.run", return_value=result):
            ports = AdbClient(executable="adb").list_forwards(SERIAL_ONE)
        self.assertEqual(ports, [39251])

    def test_stop_relay_confirms_a_relay_that_is_already_stopped(self):
        stop = subprocess.CompletedProcess(["adb"], 1, stdout="", stderr="Error: not running")
        dumpsys = subprocess.CompletedProcess(
            ["adb"], 0,
            stdout="teather.status.version=1\nlifecycle=idle\nbound_port=0\n"
            "configured_port=1080\nconfigured_upstream=cellular\n",
            stderr="",
        )
        with patch("teather.adb.subprocess.run", side_effect=[stop, dumpsys]):
            AdbClient(executable="adb").stop_relay(SERIAL_ONE)

    def test_status_parser_ignores_surrounding_dumpsys_text(self):
        status = parse_android_status(
            "header\nteather.status.version=2\n"
            "teather.status.secret=00112233445566778899aabbccddeeff\n"
            "lifecycle=running\nbound_port=1080\n"
            "configured_port=1080\nconfigured_upstream=cellular\nbytes_internet_to_client=42\n"
        )
        self.assertTrue(status.compatible)
        self.assertEqual(status.bytes_internet_to_client, 42)
        self.assertEqual(status.secret, "00112233445566778899aabbccddeeff")

    def test_status_parser_rejects_a_non_hex_relay_secret(self):
        status = parse_android_status(
            "teather.status.version=2\nteather.status.secret=not-a-real-secret\n"
            "lifecycle=running\nbound_port=1080\nconfigured_port=1080\n"
            "configured_upstream=cellular\n"
        )
        self.assertEqual(status.secret, "")

    def test_status_compatibility_includes_requested_upstream(self):
        self.assertFalse(compatible_status(configured_upstream="default").compatible)
        self.assertFalse(compatible_status(configured_port=2080).compatible)

    def test_missing_schema_is_stopped_and_incompatible(self):
        self.assertFalse(parse_android_status("Service not found").compatible)

    def test_route_preflight_accepts_preferred_physical_default(self):
        routes = json.dumps([{"dst": "default", "dev": "wlan0", "metric": 600}])
        self.assertTrue(evaluate_routes(routes).safe)

    def test_route_preflight_allows_a_host_with_no_default_route(self):
        # No other internet: Teather becomes the primary path instead of a backup.
        result = evaluate_routes("[]")
        self.assertTrue(result.safe)
        self.assertEqual(result.category, "standalone")
        # An ambiguous default is still refused even with nothing else present.
        self.assertEqual(
            evaluate_routes(json.dumps([{"dst": "default", "dev": "tun0", "metric": 50}])).category,
            "vpn-active",
        )

    def test_manager_preflight_standalone_requires_armed_failover(self):
        with tempfile.TemporaryDirectory() as directory:
            resolver = Path(directory) / "resolv.conf"  # never created: no other internet
            manager = Manager(
                config=ConfigStore(Path(directory) / "config.json"),
                resolver_path=resolver,
                nm=FakeNmConnection(resolver),
            )
            with patch.object(manager, "_run_json", return_value="[]"):
                with self.assertRaises(TeatherError) as caught:
                    manager.preflight(armed=False)
                self.assertEqual(caught.exception.category, "failover-disabled")
                manager.preflight(armed=True)  # armed: no resolver needed, succeeds

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
            _tunnel_command(45678, "00112233445566778899aabbccddeeff")
        self.assertIn("--virtual-dns-pool", command)
        self.assertIn(VIRTUAL_DNS_POOL, command)
        self.assertIn("teather0", command)
        # The relay secret authenticates the SOCKS connection (D-028).
        self.assertIn(
            "socks5://teather:00112233445566778899aabbccddeeff@127.0.0.1:45678", command
        )
        # UDP gateway sentinel is a CONNECT target, so it must not fall inside
        # the range tun2proxy routes into the tun.
        self.assertIn("--udpgw-server", command)
        sentinel_ip = ipaddress.ip_address(UDPGW_SENTINEL.split(":")[0])
        self.assertNotIn(sentinel_ip, route)
        self.assertNotIn(sentinel_ip, pool)

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

    def test_standalone_activation_accepts_a_sentinel_only_resolver(self):
        # No physical link at preflight (empty resolv.conf) -> no baseline
        # nameserver -> the sole-resolver check is correctly skipped, so arming
        # Teather as the only path succeeds instead of failing dns-exclusive.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resolver = root / "resolv.conf"
            resolver.write_text("")
            nm = make_nm(resolver, root / "teather0", exclusive=True)
            nm.preflight()
            nm.activate(armed=True)
            self.assertEqual(parse_nameservers(resolver.read_text()), [DNS_SENTINEL])
            self.assertTrue(nm.connection_is_active())

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

    def test_recover_clears_an_orphaned_dns_sentinel_via_networkmanager_reload(self):
        # An unclean shutdown can leave the sentinel in resolv.conf with no
        # teather0 connection behind it (a stale file NM has not regenerated).
        # recover() must ask NM to rewrite resolv.conf, not fail forever.
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resolver = root / "resolv.conf"
            resolver.write_text(PHYSICAL_RESOLVER + f"nameserver {DNS_SENTINEL}\n")
            nm = make_nm(resolver, root / "teather0")
            nm.recover()
            self.assertNotIn(DNS_SENTINEL, resolver.read_text())
            self.assertEqual(nm.transport.dns_reloads, 1)

    def test_recheck_connectivity_calls_networkmanager_and_never_raises(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            resolver = root / "resolv.conf"
            resolver.write_text("")
            nm = make_nm(resolver, root / "teather0")
            nm.recheck_connectivity()
            self.assertEqual(nm.transport.connectivity_checks, 1)

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
        manager.preflight = lambda *_args, **_kwargs: None
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

    def _with_bundled_apk(self, directory, version_code=99, version_name="0.1.0-test"):
        apk = Path(directory) / "Teather.apk"
        apk.write_bytes(b"PK\x03\x04 fake apk")
        ver = Path(directory) / "Teather.apk.version"
        ver.write_text(f"{version_code}\n{version_name}\n")
        return patch.multiple(
            "teather.manager", BUNDLED_APK=str(apk), BUNDLED_APK_VERSION=str(ver)
        )

    def test_android_app_state_reports_outdated_then_install_upgrades(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            adb.app_version = (4, "0.1.0-p1.2")  # older than the bundled 99
            manager = self.make_manager(directory, adb)
            with self._with_bundled_apk(directory):
                state = manager.android_app_state("")
                self.assertEqual(state["status"], "outdated")
                self.assertEqual(state["installed_version_code"], 4)
                self.assertEqual(state["bundled_version_code"], 99)

                result = manager.install_android("")
                self.assertEqual(adb.installs, [(SERIAL_ONE, str(Path(directory) / "Teather.apk"))])
                self.assertEqual(result["action"], "reinstalled")
                self.assertEqual(manager.android_app_state("")["status"], "current")

    def test_install_android_installs_when_missing(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            adb.app_version = None
            manager = self.make_manager(directory, adb)
            with self._with_bundled_apk(directory):
                self.assertEqual(manager.android_app_state("")["status"], "missing")
                result = manager.install_android("")
                self.assertEqual(result["action"], "installed")
                self.assertEqual(len(adb.installs), 1)

    def test_install_android_needs_a_connected_device(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            adb.present = False
            manager = self.make_manager(directory, adb)
            with self._with_bundled_apk(directory):
                with self.assertRaises(TeatherError) as caught:
                    manager.install_android("")
            self.assertEqual(caught.exception.category, "device-unavailable")

    def test_install_android_without_a_bundled_apk_is_a_clear_error(self):
        with tempfile.TemporaryDirectory() as directory:
            manager = self.make_manager(directory, FakeAdb())
            with patch.multiple(
                "teather.manager", BUNDLED_APK=str(Path(directory) / "absent.apk"),
                BUNDLED_APK_VERSION=str(Path(directory) / "absent.version"),
            ):
                with self.assertRaises(TeatherError) as caught:
                    manager.install_android("")
            self.assertEqual(caught.exception.category, "no-bundled-apk")

    def test_a_signature_mismatch_on_install_surfaces_its_own_category(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            adb.app_version = None
            adb.fail_install = True
            manager = self.make_manager(directory, adb)
            with self._with_bundled_apk(directory):
                with self.assertRaises(TeatherError) as caught:
                    manager.install_android("")
            self.assertEqual(caught.exception.category, "android-install-signature")

    def test_connect_refuses_a_relay_that_provides_no_session_secret(self):
        with tempfile.TemporaryDirectory() as directory:
            # schema/port fine but no usable secret (e.g. a malformed one the
            # parser dropped, or an app too old to publish it).
            adb = FakeAdb({SERIAL_ONE: compatible_status(secret="")})
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            with self.assertRaises(TeatherError) as caught:
                manager.connect(device_id)
            self.assertEqual(caught.exception.category, "android-incompatible")
            # nothing left dangling
            self.assertEqual(manager.get_status()["state"], "error")
            self.assertIsNone(manager._tunnel)

    def test_tunnel_command_rejects_a_non_hex_secret(self):
        manager = Manager(config=_scratch_config())
        with self.assertRaises(TeatherError):
            manager._tunnel_command(45678, "; rm -rf /")

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

    def test_standalone_connect_comes_up_as_the_only_path(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            resolver = Path(directory) / "resolv.conf"  # no other internet: never created
            manager = Manager(
                config=ConfigStore(Path(directory) / "config" / "config.json"),
                journal=OwnershipJournal(Path(directory) / "runtime" / "journal.json"),
                adb=adb, resolver_path=resolver, process_factory=FakeProcess,
                nm=FakeNmConnection(resolver),
                dns_probe=lambda: {"udp": "198.18.0.1", "tcp": "198.18.0.1"},
                interface_snapshot=lambda armed: "stable-interface-state",
                snapshot_timeout=0.2,
            )
            device_id = self._approve_one(manager)
            with patch.object(manager, "_run_json", return_value="[]"):
                status = manager.connect(device_id)
            self.assertEqual(status["state"], "connected")
            self.assertTrue(status["failover_armed"])
            self.assertIn("only internet path", status["message"])

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

    def test_upstream_default_is_cellular_and_toggle_rebinds_only_the_relay(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb({SERIAL_ONE: AndroidStatus()})  # relay stopped -> Teather starts it
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            manager.connect(device_id)
            self.assertEqual(adb.upstreams, ["cellular"])
            self.assertEqual(manager.get_status()["active_upstream"], "cellular")
            tunnel_before = manager._tunnel
            result = manager.set_upstream("wifi")
            self.assertEqual(result["active_upstream"], "wifi")
            # zero-gap: the relay is rebound live, never stopped/restarted
            self.assertEqual(adb.stopped, [])
            self.assertEqual(adb.reconfigured, [(SERIAL_ONE, "wifi")])
            self.assertEqual(adb.upstreams, ["cellular", "wifi"])
            self.assertIs(manager._tunnel, tunnel_before)  # tunnel/teather0 untouched
            self.assertEqual(manager.config.upstream(), "wifi")

    def test_set_upstream_refuses_a_manual_relay(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()  # relay already running -> Teather attaches, did not start it
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            manager.connect(device_id)
            self.assertEqual(adb.started, [])
            with self.assertRaises(TeatherError) as caught:
                manager.set_upstream("wifi")
            self.assertEqual(caught.exception.category, "manual-relay")

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

    def test_disconnect_survives_a_flaky_phone_side_cleanup(self):
        # A forward that won't remove is loopback-only and not host state: the
        # disconnect still lands in a clean, reconnectable state, with the
        # phone-side uncertainty surfaced as a hint rather than a wedge.
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb(fail_remove=True)
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            manager.connect(device_id)
            result = manager.disconnect()
            self.assertEqual(result["state"], "disconnected")
            self.assertEqual(result["error_category"], "none")
            self.assertIsNone(manager.journal.load())
            self.assertTrue(result["recovery_hint"])
            self.assertEqual(manager.resolver_path.read_text(), PHYSICAL_RESOLVER)
            self.assertEqual(manager.connect(device_id)["state"], "connected")

    def test_failed_connect_host_cleanup_is_reported_but_phone_side_is_not(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb(fail_remove=True)
            manager = self.make_manager(directory, adb)
            manager.process_factory = FailedProcess
            device_id = self._approve_one(manager)
            with self.assertRaises(TeatherError) as caught:
                manager.connect(device_id)
            # The tunnel failure surfaces as itself; the un-removable forward
            # does not upgrade it to a wedged recovery-pending, and the journal
            # is cleared so the next connect is free.
            self.assertEqual(caught.exception.category, "tunnel-start")
            self.assertIsNone(manager.journal.load())
            self.assertEqual(manager.resolver_path.read_text(), PHYSICAL_RESOLVER)

    def test_uncertain_android_start_does_not_wedge_the_next_connect(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb({SERIAL_ONE: AndroidStatus()}, fail_start=True, fail_stop=True)
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            with self.assertRaises(TeatherError) as caught:
                manager.connect(device_id)
            self.assertEqual(caught.exception.category, "adb-failed")
            # The relay may or may not have started on the phone, but that is
            # phone state: the journal is cleared and a retry is unblocked. The
            # relay is left alone (a failed connect is a self-heal path — a
            # running relay gets adopted on the retry, not stopped).
            self.assertIsNone(manager.journal.load())
            self.assertEqual(adb.stopped, [])

    def test_a_leftover_journal_is_reconciled_then_the_connect_proceeds(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            manager.journal.save(Ownership(device_id, 45678, False))
            status = manager.connect(device_id)
            self.assertEqual(status["state"], "connected")
            # the stale forward was released before the fresh one was added
            self.assertEqual(adb.removed, [(SERIAL_ONE, 45678)])
            self.assertEqual(adb.forwards, [SERIAL_ONE])

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

    def test_abnormal_tunnel_exit_self_heals_to_a_reconnectable_state(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            manager.connect(device_id)
            manager._tunnel.running = False
            manager.health_check()
            status = manager.get_status()
            # No error state that blocks auto-connect; the drop reason is
            # recorded, the host is restored, and the journal is clear.
            self.assertEqual(status["state"], "disconnected")
            self.assertEqual(status["last_drop"], "tunnel-exited")
            self.assertIsNone(manager.journal.load())
            self.assertEqual(manager.resolver_path.read_text(), PHYSICAL_RESOLVER)

    def test_self_heal_leaves_a_teather_started_relay_up_for_auto_reconnect(self):
        # Regression: a drop's teardown must NOT stop a relay Teather started —
        # auto-connect will not restart a stopped relay, so doing so leaves the
        # self-heal cleaned up but permanently disconnected (seen live on
        # 0.1.0-11 before the fix).
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb({SERIAL_ONE: AndroidStatus()})  # relay stopped -> Teather starts it
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            manager.set_auto_connect(device_id, True)
            manager.connect(device_id)
            self.assertEqual(adb.started, [SERIAL_ONE])

            manager._tunnel.running = False
            manager.health_check()
            self.assertEqual(manager.get_status()["state"], "disconnected")
            self.assertEqual(adb.stopped, [])  # relay left running

            manager.maybe_auto_connect()
            self.assertEqual(manager.get_status()["state"], "connected")
            self.assertEqual(adb.started, [SERIAL_ONE])  # adopted, not restarted

    def test_connection_loss_disconnects_restores_and_stays_reconnectable(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            manager.connect(device_id)
            manager.nm.active = False
            manager.health_check()
            status = manager.get_status()
            self.assertEqual(status["state"], "disconnected")
            self.assertEqual(status["last_drop"], "connection-lost")
            self.assertEqual(manager.resolver_path.read_text(), PHYSICAL_RESOLVER)

    def test_connection_loss_surfaces_but_does_not_wedge_on_flaky_adb(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            manager.connect(device_id)
            manager.nm.active = False
            adb.fail_remove = True
            manager.health_check()
            status = manager.get_status()
            # host state restored, journal cleared, phone-side uncertainty noted
            self.assertEqual(status["state"], "disconnected")
            self.assertEqual(manager.resolver_path.read_text(), PHYSICAL_RESOLVER)
            self.assertIsNone(manager.journal.load())
            self.assertTrue(status["recovery_hint"])

    def test_recovery_clears_the_journal_once_the_tunnel_is_torn_down(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            manager.journal.save(Ownership(device_id, 45678, True))
            result = manager.recover()
            self.assertFalse(result["recovery_pending"])
            self.assertIsNone(manager.journal.load())
            self.assertEqual(manager.nm.recovered, 1)
            self.assertEqual(adb.removed, [(SERIAL_ONE, 45678)])
            # recover() is a self-heal path: it releases the host side and the
            # forward but leaves the relay running for the next connect to adopt.
            self.assertEqual(adb.stopped, [])

    def test_recovery_clears_the_journal_even_when_the_phone_is_absent(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            device_id = manager.config.device_id(SERIAL_ONE)
            manager.journal.save(Ownership(device_id, 45678, True))
            adb.devices = lambda: []
            result = manager.recover()
            self.assertFalse(result["recovery_pending"])
            self.assertIsNone(manager.journal.load())
            self.assertEqual(manager.nm.recovered, 1)

    def test_recovery_keeps_the_journal_when_the_tunnel_teardown_is_unverified(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            manager.journal.save(Ownership(device_id, 45678, True))

            def unsafe_recover():
                raise TeatherError("ambiguous-interface", "teather0 is not ours")

            manager.nm.recover = unsafe_recover
            with self.assertRaises(TeatherError) as caught:
                manager.recover()
            self.assertEqual(caught.exception.category, "ambiguous-interface")
            self.assertIsNotNone(manager.journal.load())

    def test_restart_during_a_live_connection_does_not_wedge_connect(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb(fail_remove=True, fail_stop=True)
            manager = self.make_manager(directory, adb)
            device_id = self._approve_one(manager)
            manager.journal.save(Ownership(device_id, 45678, True))
            manager.recover()
            self.assertIsNone(manager.journal.load())
            self.assertEqual(manager.connect(device_id)["state"], "connected")


class SelfHealTests(unittest.TestCase):
    def make_manager(self, directory, adb):
        return ManagerTests.make_manager(self, directory, adb)

    def _connect_one(self, manager):
        device_id = manager.discover()[0]["device_id"]
        manager.approve_device(device_id)
        manager.set_auto_connect(device_id, True)
        manager.connect(device_id)
        return device_id

    def test_unplugging_the_phone_self_heals_and_auto_reconnects(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            self._connect_one(manager)

            adb.present = False  # the phone is unplugged
            manager.health_check()
            status = manager.get_status()
            self.assertEqual(status["state"], "disconnected")
            self.assertEqual(status["last_drop"], "phone-disconnected")
            self.assertEqual(status["error_category"], "none")
            self.assertIsNone(manager.journal.load())
            self.assertEqual(manager.resolver_path.read_text(), PHYSICAL_RESOLVER)

            adb.present = True  # plugged back in
            manager.maybe_auto_connect()
            self.assertEqual(manager.get_status()["state"], "connected")

    def test_a_dropped_adb_forward_is_detected_as_a_lost_connection(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            self._connect_one(manager)
            adb.forward_ports = []  # the forward died with an adb-server blip
            manager.health_check()
            status = manager.get_status()
            self.assertEqual(status["state"], "disconnected")
            self.assertEqual(status["last_drop"], "relay-unreachable")

    def test_reconcile_clears_a_stale_journal_on_the_poll_loop(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            device_id = manager.discover()[0]["device_id"]
            manager.approve_device(device_id)
            manager.journal.save(Ownership(device_id, 45678, False))
            manager._state = "error"
            manager._error_category = "recovery-pending"

            manager.reconcile()

            self.assertEqual(manager.get_status()["state"], "disconnected")
            self.assertIsNone(manager.journal.load())
            self.assertEqual(manager.nm.recovered, 1)

    def test_reconcile_self_heals_an_error_latched_by_a_failed_connect(self):
        # A failed (auto-)connect records the raw category it hit — e.g.
        # "dns-residue" from preflight — not "recovery-pending". The poll-loop
        # self-heal must still clear it once the residue is gone, otherwise the
        # daemon stays wedged in "error" forever: reconcile and auto-connect are
        # both gated off that state.
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            device_id = manager.discover()[0]["device_id"]
            manager.approve_device(device_id)
            manager.set_auto_connect(device_id, True)

            manager._state = "error"
            manager._error_category = "dns-residue"
            manager._message = "The Teather DNS sentinel is already present; run teather recover"

            manager.reconcile()

            self.assertEqual(manager.get_status()["state"], "disconnected")
            self.assertEqual(manager.get_status()["error_category"], "none")

            manager.maybe_auto_connect()
            self.assertEqual(manager.get_status()["state"], "connected")

    def test_auto_connect_backs_off_after_repeated_failures_then_a_replug_resumes(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            device_id = manager.discover()[0]["device_id"]
            manager.approve_device(device_id)
            manager.set_auto_connect(device_id, True)

            def boom(_id=""):
                raise TeatherError("networkmanager-activation", "simulated wedged NM")

            with patch.object(manager, "connect", side_effect=boom):
                for _ in range(_AUTOCONNECT_MAX_TRIES + 3):
                    manager.maybe_auto_connect()
            # capped, not looping forever
            self.assertEqual(manager._autoconnect_tries, 0)
            self.assertGreater(manager._autoconnect_paused_until, 0.0)
            self.assertIn("Paused", manager.get_status()["message"])

            # a replug (eligible set goes empty then non-empty) lifts the pause
            adb.present = False
            manager.maybe_auto_connect()
            adb.present = True
            manager.maybe_auto_connect()
            self.assertEqual(manager._autoconnect_paused_until, 0.0)
            self.assertEqual(manager.get_status()["state"], "connected")

    def test_shutdown_releases_the_host_but_leaves_the_relay_for_next_start(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb({SERIAL_ONE: AndroidStatus()})  # Teather starts the relay
            manager = self.make_manager(directory, adb)
            device_id = self._connect_one(manager)
            self.assertEqual(adb.started, [SERIAL_ONE])

            manager.shutdown()
            self.assertEqual(adb.stopped, [])  # relay left running
            self.assertEqual(manager.resolver_path.read_text(), PHYSICAL_RESOLVER)
            self.assertIsNone(manager.journal.load())
            self.assertIsNone(manager._tunnel)

            # next start adopts the still-running relay
            manager.connect(device_id)
            self.assertEqual(adb.started, [SERIAL_ONE])  # not started again
            self.assertEqual(manager.get_status()["state"], "connected")

    def test_explicit_disconnect_still_stops_a_relay_teather_started(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb({SERIAL_ONE: AndroidStatus()})
            manager = self.make_manager(directory, adb)
            self._connect_one(manager)
            manager.disconnect()
            self.assertEqual(adb.stopped, [SERIAL_ONE])

    def test_relay_probe_is_skipped_while_a_recent_status_is_known(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            self._connect_one(manager)
            adb.states[adb.devices()[0].serial] = AndroidStatus()  # relay now stopped
            manager._health_tick = _RELAY_PROBE_EVERY - 1
            manager._relay_ok_at = manager._relay_ok_at or 1.0
            import teather.manager as m
            with patch.object(m.time, "monotonic", return_value=manager._relay_ok_at + 10):
                manager.health_check()  # within the "recently confirmed" window -> no probe
            self.assertEqual(manager.get_status()["state"], "connected")

    def test_relay_probe_detects_a_stopped_relay_as_a_backstop(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            self._connect_one(manager)
            adb.states[adb.devices()[0].serial] = AndroidStatus()  # relay stopped
            manager._health_tick = _RELAY_PROBE_EVERY - 1
            import teather.manager as m
            with patch.object(m.time, "monotonic", return_value=manager._relay_ok_at + 10_000):
                manager.health_check()
            status = manager.get_status()
            self.assertEqual(status["state"], "disconnected")
            self.assertEqual(status["last_drop"], "relay-stopped")

    def test_sole_path_transition_is_tracked_and_announced(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            manager = self.make_manager(directory, adb)
            self._connect_one(manager)
            self.assertFalse(manager.get_status()["standalone"])

            with_wifi = json.dumps([{"dst": "default", "dev": "wlan0", "metric": 600}])
            no_wifi = json.dumps([{"dst": "default", "dev": "teather0", "metric": 32000}])

            with patch.object(manager, "_run_json", return_value=with_wifi):
                manager.health_check()
            self.assertFalse(manager.get_status()["standalone"])  # no change

            with patch.object(manager, "_run_json", return_value=no_wifi):
                manager.health_check()
            status = manager.get_status()
            self.assertTrue(status["standalone"])
            self.assertIn("carrying all traffic", status["message"])
            self.assertEqual(status["state"], "connected")

            with patch.object(manager, "_run_json", return_value=with_wifi):
                manager.health_check()
            self.assertFalse(manager.get_status()["standalone"])

    def test_standalone_connect_nudges_the_connectivity_check(self):
        with tempfile.TemporaryDirectory() as directory:
            adb = FakeAdb()
            resolver = Path(directory) / "resolv.conf"  # no other internet
            manager = Manager(
                config=ConfigStore(Path(directory) / "config" / "config.json"),
                journal=OwnershipJournal(Path(directory) / "runtime" / "journal.json"),
                adb=adb, resolver_path=resolver, process_factory=FakeProcess,
                nm=FakeNmConnection(resolver),
                dns_probe=lambda: {"udp": "198.18.0.1", "tcp": "198.18.0.1"},
                interface_snapshot=lambda armed: "stable-interface-state",
                snapshot_timeout=0.2,
            )
            device_id = manager.discover()[0]["device_id"]
            manager.approve_device(device_id)
            with patch.object(manager, "_run_json", return_value="[]"):
                manager.connect(device_id)
            self.assertEqual(manager.nm.connectivity_rechecks, 1)


class InterfaceParityTests(unittest.TestCase):
    def test_dbus_methods_match_cli_surface(self):
        for method in (
            "GetStatus", "ListDevices", "Connect", "Disconnect", "ApproveDevice",
            "RenameDevice", "ForgetDevice", "SetAutoConnect", "SetAutoFailover",
            "SetUpstream", "Diagnose",
        ):
            self.assertIn(f'name="{method}"', INTROSPECTION_XML)
        parser = build_parser()
        for command in ("status", "devices", "connect", "disconnect", "autoconnect", "failover", "upstream", "diagnose", "recover"):
            with self.subTest(command=command):
                arguments = [command]
                if command == "autoconnect":
                    arguments += ["on", "a" * 64]
                elif command == "failover":
                    arguments += ["on"]
                elif command == "upstream":
                    arguments += ["wifi"]
                parser.parse_args(arguments)


if __name__ == "__main__":
    unittest.main()
