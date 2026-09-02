from __future__ import annotations

import logging
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

log = logging.getLogger(__name__)


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
        # Log the control command with the serial redacted (AGENTS.md: logs
        # identify the failing layer, never the device or its traffic).
        printable = " ".join("<device>" if part == serial else part for part in command[1:])
        log.debug("adb %s", printable)
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
            log.warning("adb %s -> %s", printable, type(error).__name__)
            raise TeatherError("adb-unavailable", f"ADB command failed: {type(error).__name__}") from error
        if check and result.returncode:
            detail = (result.stderr or result.stdout or "ADB command failed").strip()
            if serial:
                detail = detail.replace(serial, "<device>")
            detail = re.sub(r"[A-Za-z0-9._:-]{16,}", "<redacted>", detail)
            log.warning("adb %s -> exit %s: %s", printable, result.returncode, detail[:160])
            raise TeatherError("adb-failed", detail[:240])
        return result.stdout

    def list_forwards(self, serial: str) -> list[int]:
        """Local TCP ports currently forwarded for ``serial`` (``adb forward
        --list``). Used by the health check to notice a forward that died with
        an ADB-server restart or a USB blip."""

        ports: list[int] = []
        for line in self._run(["forward", "--list"]).splitlines():
            fields = line.split()
            if len(fields) >= 2 and fields[0] == serial and fields[1].startswith("tcp:"):
                try:
                    ports.append(int(fields[1].split(":", 1)[1]))
                except ValueError:
                    continue
        return ports

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

    def installed_version(self, serial: str) -> tuple[int, str] | None:
        """``(versionCode, versionName)`` for the Teather app on ``serial``, or
        ``None`` if it is not installed. Used to keep the phone app in lockstep
        with this desktop package (D-029)."""

        output = self._run(["shell", "dumpsys", "package", APP_ID], serial=serial, check=False)
        code = re.search(r"versionCode=(\d+)", output)
        name = re.search(r"versionName=(\S+)", output)
        if not code:
            return None
        return int(code.group(1)), (name.group(1) if name else "")

    def install_apk(self, serial: str, apk_path: str) -> None:
        """``adb install -r`` the bundled APK. Reinstall in place needs the same
        signing key already on the device; a key mismatch surfaces as
        ``android-install-signature`` so the caller can tell the user to remove
        the old app first."""

        output = self._run(["install", "-r", apk_path], serial=serial, check=False)
        if "Success" in output:
            return
        lowered = output.lower()
        if "signatures do not match" in lowered or "update_incompatible" in lowered:
            raise TeatherError(
                "android-install-signature",
                "The phone has a Teather build signed with a different key; uninstall it first "
                "(adb uninstall " + APP_ID + "), then install again.",
            )
        if "version_downgrade" in lowered or "older" in lowered:
            raise TeatherError(
                "android-install-downgrade",
                "The phone already has a newer Teather app than this package bundles.",
            )
        detail = re.sub(r"[A-Za-z0-9._:/-]{16,}", "<redacted>", output.strip())
        raise TeatherError("android-install", detail[:240] or "adb install failed")

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
        try:
            self._run(
                ["shell", "am", "start-foreground-service", "-n", SERVICE_COMPONENT, "-a", ACTION_STOP],
                serial=serial,
            )
        except TeatherError:
            # Delivering STOP can fail when the service is already gone (nothing
            # is listening for the intent). That is the desired end state, so
            # fall through and let the status poll below confirm it.
            pass
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
        try:
            self._run(["forward", "--remove", f"tcp:{port}"], serial=serial)
        except TeatherError as error:
            # An already-absent forward (or a device that has since vanished) is
            # the outcome we want: adb forwards are loopback-only and die with
            # the adb server or the device, so this is not host-network state to
            # keep chasing.
            if "not found" in str(error).lower():
                return
            raise
