from __future__ import annotations

import argparse
import json
import sys

from .dbus_client import DbusClient


def _json_flag(parser):
    parser.add_argument("--json", action="store_true", help="print machine-readable JSON")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="teather", description="Teather Linux USB desktop client")
    commands = parser.add_subparsers(dest="command", required=True)
    _json_flag(commands.add_parser("status", help="show connection status"))
    _json_flag(commands.add_parser("devices", help="list detected and remembered phones"))
    connect = commands.add_parser("connect", help="connect an approved phone")
    connect.add_argument("device_id", nargs="?", default="")
    commands.add_parser("disconnect", help="disconnect and clean owned resources")
    device = commands.add_parser("device", help="manage remembered phones").add_subparsers(dest="device_command", required=True)
    approve = device.add_parser("approve", help="approve a connected phone locally")
    approve.add_argument("device_id")
    approve.add_argument("--yes", action="store_true")
    rename = device.add_parser("rename", help="rename a remembered phone")
    rename.add_argument("device_id")
    rename.add_argument("name")
    forget = device.add_parser("forget", help="forget a phone")
    forget.add_argument("device_id")
    install = device.add_parser(
        "install",
        help="install or upgrade the Teather app on the phone from the APK this package bundles",
    )
    install.add_argument("device_id", nargs="?", default="")
    install.add_argument("--yes", action="store_true")
    autoconnect = commands.add_parser("autoconnect", help="enable or disable safe auto-connect")
    autoconnect.add_argument("setting", choices=("on", "off"))
    autoconnect.add_argument("device_id")
    failover = commands.add_parser(
        "failover",
        help="arm (on) or hold dormant (off) automatic failover to Teather when Wi-Fi is lost",
    )
    failover.add_argument("setting", choices=("on", "off"))
    upstream = commands.add_parser(
        "upstream",
        help="pick which of the phone's transports the relay uses (restarts only the phone's relay binding)",
    )
    upstream.add_argument("transport", choices=("auto", "cellular", "wifi", "ethernet"))
    _json_flag(commands.add_parser("diagnose", help="run read-only diagnostics"))
    _json_flag(commands.add_parser("recover", help="clean journaled resources and diagnose"))
    _json_flag(commands.add_parser("sessions", help="show the recent connection-session history"))
    return parser


def _print(value, machine: bool = False) -> None:
    if machine:
        print(json.dumps(value, sort_keys=True, separators=(",", ":")))
        return
    if isinstance(value, list):
        for item in value:
            print(f"{item['device_id']}  {item['name']}  connected={item['connected']} approved={item['approved']} relay={item['relay_state']}")
        if not value:
            print("No phones detected or remembered")
        return
    for key, item in value.items():
        print(f"{key}: {item}")


def main(argv: list[str] | None = None) -> int:
    arguments = build_parser().parse_args(argv)
    try:
        client = DbusClient()
        if arguments.command == "status":
            result = client.call("GetStatus")
        elif arguments.command == "devices":
            result = client.call("ListDevices")
        elif arguments.command == "connect":
            device_id = arguments.device_id
            if not device_id:
                candidates = [
                    device for device in client.call("ListDevices")
                    if device["connected"] and device["approved"]
                ]
                if len(candidates) > 1:
                    if not sys.stdin.isatty():
                        raise RuntimeError("multiple approved phones are available; provide DEVICE_ID")
                    for index, device in enumerate(candidates, 1):
                        print(f"{index}. {device['name']} ({device['device_id']})")
                    choice = input("Connect which phone? ").strip()
                    if not choice.isdigit() or int(choice) not in range(1, len(candidates) + 1):
                        raise RuntimeError("invalid phone selection")
                    device_id = candidates[int(choice) - 1]["device_id"]
            result = client.call("Connect", "(s)", (device_id,))
        elif arguments.command == "disconnect":
            result = client.call("Disconnect")
        elif arguments.command == "diagnose":
            result = client.call("Diagnose")
        elif arguments.command == "sessions":
            sessions = client.call("SessionHistory")
            if getattr(arguments, "json", False):
                print(json.dumps(sessions, sort_keys=True, separators=(",", ":")))
                return 0
            if not sessions:
                print("No sessions recorded yet")
                return 0
            def _bytes(n: int) -> str:
                value = float(max(0, int(n)))
                for unit in ("B", "KiB", "MiB", "GiB"):
                    if value < 1024 or unit == "GiB":
                        return f"{int(value)} {unit}" if unit == "B" else f"{value:.1f} {unit}"
                    value /= 1024
                return f"{value:.1f} GiB"
            for s in sorted(sessions, key=lambda x: str(x.get("started", "")), reverse=True):
                mins = int(s.get("duration_s", 0)) // 60
                print(
                    f"{s.get('started', '?')}  {mins:>4}m  "
                    f"up {_bytes(s.get('to_internet', 0)):>10}  down {_bytes(s.get('to_client', 0)):>10}  "
                    f"{s.get('upstream', '?')}  ({s.get('end_reason', '?')})"
                )
            return 0
        elif arguments.command == "recover":
            status = client.call("Disconnect")
            result = client.call("Diagnose")
            result["recovery_pending"] = status.get("error_category") == "recovery-pending"
        elif arguments.command == "autoconnect":
            result = client.call(
                "SetAutoConnect", "(sb)", (arguments.device_id, arguments.setting == "on"),
            )
        elif arguments.command == "failover":
            result = client.call("SetAutoFailover", "(b)", (arguments.setting == "on",))
        elif arguments.command == "upstream":
            result = client.call("SetUpstream", "(s)", (arguments.transport,))
        elif arguments.device_command == "approve":
            if not arguments.yes:
                answer = input("Approve this locally connected phone for Teather? [y/N] ")
                if answer.strip().lower() not in {"y", "yes"}:
                    print("Approval cancelled", file=sys.stderr)
                    return 2
            result = client.call("ApproveDevice", "(s)", (arguments.device_id,))
        elif arguments.device_command == "rename":
            result = client.call("RenameDevice", "(ss)", (arguments.device_id, arguments.name))
        elif arguments.device_command == "install":
            state = client.call("AndroidAppState", "(s)", (arguments.device_id,))
            status = state.get("status")
            if status == "current":
                print(
                    f"The phone already has the matching Teather app "
                    f"(versionCode {state.get('installed_version_code')})."
                )
                return 0
            if status == "no-bundle":
                raise RuntimeError("this package does not bundle a Teather APK")
            if status == "no-device":
                raise RuntimeError("connect exactly one phone, or pass its id")
            if status == "ahead":
                print(
                    "The phone has a newer Teather app "
                    f"(versionCode {state.get('installed_version_code')}) than this package bundles "
                    f"({state.get('bundled_version_code')}); leaving it alone."
                )
                return 0
            verb = "Install" if status == "missing" else "Upgrade"
            if not arguments.yes:
                answer = input(
                    f"{verb} the Teather app on this phone to versionCode "
                    f"{state.get('bundled_version_code')}? [y/N] "
                )
                if answer.strip().lower() not in {"y", "yes"}:
                    print("Cancelled", file=sys.stderr)
                    return 2
            result = client.call("InstallAndroid", "(s)", (arguments.device_id,))
        else:
            result = client.call("ForgetDevice", "(s)", (arguments.device_id,))
        _print(result, getattr(arguments, "json", False))
        return 0
    except Exception as error:
        print(f"teather: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
