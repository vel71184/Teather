from __future__ import annotations

import re
import shutil
import subprocess
import time
from dataclasses import dataclass

from .android_status import AndroidStatus, parse_android_status
from .constants import (
    ACTION_RECONFIGURE,
    ACTION_START,
    ACTION_STOP,
    APP_ID,
    RELAY_PORT,
    SERVICE_COMPONENT,
)
from .errors import TeatherError


@dataclass(frozen=True)
class AdbDevice:
    serial: str
    model: str


class AdbClient:
    def __init__(self, executable: str = "adb", timeout: float = 10.0):
        self.executable = shutil.which(executable) or executable
        self.timeout = timeout

    def _run(self, arguments: list[str], serial: str | None = None, check: bool = True) -> str:
        command = [self.executable]
        if serial:
            command.extend(["-s", serial])
        command.extend(arguments)
        try:
            result = subprocess.run(
                command,
                check=False,
                capture_output=True,
                text=True,
                timeout=self.timeout,
                env={"PATH": "/usr/bin:/bin"},
            )
        except (OSError, subprocess.TimeoutExpired) as error:
            raise TeatherError("adb-unavailable", f"ADB command failed: {type(error).__name__}") from error
        if check and result.returncode:
            detail = (result.stderr or result.stdout or "ADB command failed").strip()
            if serial:
                detail = detail.replace(serial, "<device>")
            detail = re.sub(r"[A-Za-z0-9._:-]{16,}", "<redacted>", detail)
            raise TeatherError("adb-failed", detail[:240])
        return result.stdout

    def devices(self) -> list[AdbDevice]:
        output = self._run(["devices", "-l"])
        devices: list[AdbDevice] = []
        for line in output.splitlines()[1:]:
            fields = line.split()
            if len(fields) < 2 or fields[1] != "device":
                continue
            details = dict(part.split(":", 1) for part in fields[2:] if ":" in part)
            model = details.get("model", "Android phone").replace("_", " ")[:80]
            devices.append(AdbDevice(fields[0], model))
        return devices

    def package_installed(self, serial: str) -> bool:
        output = self._run(["shell", "pm", "path", APP_ID], serial=serial, check=False)
        return output.startswith("package:")

    def status(self, serial: str) -> AndroidStatus:
        output = self._run(
            ["shell", "dumpsys", "activity", "service", SERVICE_COMPONENT],
            serial=serial,
        )
        return parse_android_status(output)

    def start_relay(self, serial: str, upstream: str = "cellular") -> AndroidStatus:
        self._run(
            [
                "shell", "am", "start-foreground-service", "-n", SERVICE_COMPONENT,
                "-a", ACTION_START, "--ei", "relay_port", str(RELAY_PORT),
                "--es", "relay_upstream", upstream,
            ],
            serial=serial,
        )
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            status = self.status(serial)
            if status.running or status.lifecycle == "failed":
                return status
            time.sleep(0.2)
        raise TeatherError("android-timeout", "Android relay did not become ready")

    def reconfigure_relay(self, serial: str, upstream: str) -> AndroidStatus:
        """Rebind the running relay's upstream with no listener teardown.

        Established sessions keep their transport; new ones use ``upstream``.
        """
        self._run(
            [
                "shell", "am", "start-foreground-service", "-n", SERVICE_COMPONENT,
                "-a", ACTION_RECONFIGURE, "--ei", "relay_port", str(RELAY_PORT),
                "--es", "relay_upstream", upstream,
            ],
            serial=serial,
        )
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            status = self.status(serial)
            if status.configured_upstream == upstream or status.lifecycle == "failed":
                return status
            time.sleep(0.2)
        raise TeatherError("android-timeout", "Android relay did not apply the new upstream")

    def stop_relay(self, serial: str) -> None:
        self._run(
            ["shell", "am", "start-foreground-service", "-n", SERVICE_COMPONENT, "-a", ACTION_STOP],
            serial=serial,
        )
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            if not self.status(serial).running:
                return
            time.sleep(0.2)
        raise TeatherError("android-timeout", "Android relay did not stop")

    def add_forward(self, serial: str) -> int:
        output = self._run(["forward", "tcp:0", f"tcp:{RELAY_PORT}"], serial=serial).strip()
        try:
            port = int(output)
        except ValueError as error:
            raise TeatherError("adb-forward", "ADB did not return a local port") from error
        if port not in range(1024, 65536):
            raise TeatherError("adb-forward", "ADB returned an unsafe local port")
        return port

    def remove_forward(self, serial: str, port: int) -> None:
        self._run(["forward", "--remove", f"tcp:{port}"], serial=serial)
