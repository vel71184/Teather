from __future__ import annotations

from dataclasses import dataclass

from .constants import RELAY_PORT, STATUS_SCHEMA

# Android upstream transports Teather can bind the relay to. The Android app
# (UpstreamPreference) already supports all four; "auto" lets Android pick.
KNOWN_UPSTREAMS = ("auto", "cellular", "wifi", "ethernet")
DEFAULT_UPSTREAM = "cellular"


@dataclass(frozen=True)
class AndroidStatus:
    schema: int = 0
    lifecycle: str = "stopped"
    bound_port: int = 0
    configured_port: int = 0
    configured_upstream: str = "none"
    selected_upstream: str = "none"
    cellular_available: bool = False
    cellular_validated: bool = False
    accepted_clients: int = 0
    established_sessions: int = 0
    rejected_clients: int = 0
    active_sessions: int = 0
    bytes_client_to_internet: int = 0
    bytes_internet_to_client: int = 0
    failure_category: str = "none"
    last_error_category: str = "none"
    control_error: str = "none"

    @property
    def running(self) -> bool:
        return self.lifecycle == "running"

    @property
    def compatible(self) -> bool:
        return (
            self.schema == STATUS_SCHEMA
            and self.running
            and self.bound_port == RELAY_PORT
            and self.configured_port == RELAY_PORT
            and self.configured_upstream in KNOWN_UPSTREAMS
        )

    def matches_upstream(self, upstream: str) -> bool:
        return self.configured_upstream == upstream


def parse_android_status(output: str) -> AndroidStatus:
    values: dict[str, str] = {}
    for line in output.splitlines():
        if "=" not in line:
            continue
        key, value = line.strip().split("=", 1)
        if key == "teather.status.version" or key in AndroidStatus.__dataclass_fields__:
            values[key] = value
    if "teather.status.version" not in values:
        return AndroidStatus()

    def integer(name: str) -> int:
        try:
            value = int(values.get(name, "0"))
        except ValueError:
            return 0
        return max(0, value)

    def boolean(name: str) -> bool:
        return values.get(name) == "true"

    return AndroidStatus(
        schema=integer("teather.status.version"),
        lifecycle=values.get("lifecycle", "unknown"),
        bound_port=integer("bound_port"),
        configured_port=integer("configured_port"),
        configured_upstream=values.get("configured_upstream", "none"),
        selected_upstream=values.get("selected_upstream", "none"),
        cellular_available=boolean("cellular_available"),
        cellular_validated=boolean("cellular_validated"),
        accepted_clients=integer("accepted_clients"),
        established_sessions=integer("established_sessions"),
        rejected_clients=integer("rejected_clients"),
        active_sessions=integer("active_sessions"),
        bytes_client_to_internet=integer("bytes_client_to_internet"),
        bytes_internet_to_client=integer("bytes_internet_to_client"),
        failure_category=values.get("failure_category", "none"),
        last_error_category=values.get("last_error_category", "none"),
        control_error=values.get("control_error", "none"),
    )
