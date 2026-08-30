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
    autoconnect = commands.add_parser("autoconnect", help="enable or disable safe auto-connect")
    autoconnect.add_argument("setting", choices=("on", "off"))
    autoconnect.add_argument("device_id")
    failover = commands.add_parser(
        "failover",
        help="arm (on) or hold dormant (off) automatic failover to Teather when Wi-Fi is lost",
    )
    failover.add_argument("setting", choices=("on", "off"))
    _json_flag(commands.add_parser("diagnose", help="run read-only diagnostics"))
    _json_flag(commands.add_parser("recover", help="clean journaled resources and diagnose"))
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
        elif arguments.device_command == "approve":
            if not arguments.yes:
                answer = input("Approve this locally connected phone for Teather? [y/N] ")
                if answer.strip().lower() not in {"y", "yes"}:
                    print("Approval cancelled", file=sys.stderr)
                    return 2
            result = client.call("ApproveDevice", "(s)", (arguments.device_id,))
        elif arguments.device_command == "rename":
            result = client.call("RenameDevice", "(ss)", (arguments.device_id, arguments.name))
        else:
            result = client.call("ForgetDevice", "(s)", (arguments.device_id,))
        _print(result, getattr(arguments, "json", False))
        return 0
    except Exception as error:
        print(f"teather: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
