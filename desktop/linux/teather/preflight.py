from __future__ import annotations

import ipaddress
import json
import re
from dataclasses import dataclass

from .constants import INTERFACE_NAME, ROUTE_METRIC, VIRTUAL_DNS_POOL


@dataclass(frozen=True)
class PreflightResult:
    safe: bool
    category: str
    message: str


def evaluate_routes(
    route_json: str,
    link_json: str = "[]",
    address_json: str = "[]",
    rule_json: str = "[]",
) -> PreflightResult:
    try:
        routes = json.loads(route_json)
        links = json.loads(link_json)
        addresses = json.loads(address_json)
        rules = json.loads(rule_json)
    except (ValueError, TypeError):
        return PreflightResult(False, "route-inspection", "Cannot parse Linux route state")
    collections = (routes, links, addresses, rules)
    if any(not isinstance(collection, list) for collection in collections) or any(
        not isinstance(entry, dict) for collection in collections for entry in collection
    ):
        return PreflightResult(False, "route-inspection", "Linux route state has an unexpected shape")
    standard_rules = {(0, "local"), (32766, "main"), (32767, "default")}
    for rule in rules:
        table = str(rule.get("table", ""))
        table = {"255": "local", "254": "main", "253": "default"}.get(table, table)
        try:
            identity = (int(rule.get("priority", -1)), table)
        except (TypeError, ValueError):
            return PreflightResult(False, "route-inspection", "Cannot parse an IPv4 policy rule")
        unusual = set(rule) - {"priority", "src", "dst", "table", "protocol"}
        if identity not in standard_rules or rule.get("src", "all") != "all" or unusual:
            return PreflightResult(False, "policy-routing", "Nonstandard IPv4 policy routing is active")
    if any(link.get("ifname") == INTERFACE_NAME for link in links):
        return PreflightResult(False, "interface-collision", f"{INTERFACE_NAME} already exists")
    for entry in addresses:
        for info in entry.get("addr_info", []):
            if info.get("family") == "inet" and info.get("local") == "192.0.2.1":
                return PreflightResult(False, "address-collision", "192.0.2.1 is already assigned")
    defaults = []
    virtual_pool = ipaddress.ip_network(VIRTUAL_DNS_POOL)
    for route in routes:
        destination = route.get("dst", "default")
        device = str(route.get("dev", ""))
        if device == INTERFACE_NAME:
            return PreflightResult(False, "route-collision", "A Teather route already exists")
        if destination in {"0.0.0.0/1", "128.0.0.0/1"}:
            return PreflightResult(False, "split-default", "Split-default routing is active")
        if destination != "default":
            try:
                network = ipaddress.ip_network(destination, strict=False)
            except ValueError:
                return PreflightResult(False, "route-inspection", "Cannot parse an IPv4 route destination")
            if network.version == 4 and network.overlaps(virtual_pool):
                return PreflightResult(False, "route-collision", "An existing route overlaps the virtual-DNS pool")
        if destination == "default":
            defaults.append(route)
            if re.search(r"(^|[-_.])(tun|tap|wg|vpn|tailscale|proton)", device, re.I):
                return PreflightResult(False, "vpn-active", "A VPN-like default route is active")
            try:
                metric = int(route.get("metric", 0))
            except (TypeError, ValueError):
                return PreflightResult(False, "route-inspection", "Cannot parse an IPv4 route metric")
            if metric >= ROUTE_METRIC:
                return PreflightResult(False, "route-preference", "An existing default would not remain preferred")
    if not defaults:
        return PreflightResult(False, "no-default", "No existing IPv4 default route is present")
    return PreflightResult(True, "ready", "Existing defaults remain preferred")


def parse_nameservers(resolver_text: str) -> list[str]:
    result: list[str] = []
    for line in resolver_text.splitlines():
        line = line.split("#", 1)[0].strip()
        fields = line.split()
        if len(fields) != 2 or fields[0] != "nameserver":
            continue
        try:
            address = ipaddress.ip_address(fields[1].split("%", 1)[0])
        except ValueError:
            continue
        if address.version == 4 and not address.is_loopback and not address.is_unspecified:
            result.append(str(address))
    return result
