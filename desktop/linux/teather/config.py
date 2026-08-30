from __future__ import annotations

import base64
import hashlib
import hmac
import json
import os
import secrets
import stat
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from .errors import TeatherError


@dataclass(frozen=True)
class RememberedDevice:
    device_id: str
    name: str
    approved: bool = True
    auto_connect: bool = False


class SecureJsonFile:
    def __init__(self, path: Path):
        self.path = path

    def _ensure_parent(self) -> None:
        self.path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(self.path.parent, 0o700)

    def read(self) -> dict[str, Any] | None:
        try:
            info = self.path.lstat()
        except FileNotFoundError:
            return None
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid() or info.st_mode & 0o077:
            raise TeatherError("unsafe-storage", f"Unsafe owner or mode on {self.path}")
        flags = os.O_RDONLY | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(self.path, flags)
        try:
            with os.fdopen(fd, "r", encoding="utf-8") as stream:
                value = json.load(stream)
        except (OSError, ValueError, TypeError) as error:
            raise TeatherError("invalid-storage", f"Cannot read {self.path.name}: {error}") from error
        if not isinstance(value, dict):
            raise TeatherError("invalid-storage", f"{self.path.name} must contain an object")
        return value

    def write(self, value: dict[str, Any]) -> None:
        self._ensure_parent()
        temporary = self.path.with_name(f".{self.path.name}.{secrets.token_hex(8)}")
        flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_NOFOLLOW", 0)
        fd = os.open(temporary, flags, 0o600)
        try:
            with os.fdopen(fd, "w", encoding="utf-8") as stream:
                json.dump(value, stream, sort_keys=True, separators=(",", ":"))
                stream.write("\n")
                stream.flush()
                os.fsync(stream.fileno())
            os.replace(temporary, self.path)
            os.chmod(self.path, 0o600)
        finally:
            try:
                temporary.unlink()
            except FileNotFoundError:
                pass

    def remove(self) -> None:
        try:
            info = self.path.lstat()
        except FileNotFoundError:
            return
        if not stat.S_ISREG(info.st_mode) or info.st_uid != os.getuid():
            raise TeatherError("unsafe-storage", f"Refusing to remove ambiguous {self.path}")
        self.path.unlink()


class ConfigStore:
    SCHEMA = 1

    def __init__(self, path: Path | None = None):
        root = Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config"))
        self.file = SecureJsonFile(path or root / "teather" / "config.json")
        self._data = self.file.read() or self._new_data()
        self._validate()
        if not self.file.path.exists():
            self.save()

    @staticmethod
    def _new_data() -> dict[str, Any]:
        return {
            "schema": ConfigStore.SCHEMA,
            "salt": base64.b64encode(secrets.token_bytes(32)).decode("ascii"),
            "devices": {},
            "auto_failover": True,
        }

    def _validate(self) -> None:
        if self._data.get("schema") != self.SCHEMA or not isinstance(self._data.get("devices"), dict):
            raise TeatherError("invalid-config", "Unsupported Teather configuration schema")
        try:
            salt = base64.b64decode(self._data["salt"], validate=True)
        except (KeyError, ValueError, TypeError) as error:
            raise TeatherError("invalid-config", "Invalid device-hash salt") from error
        if len(salt) != 32:
            raise TeatherError("invalid-config", "Invalid device-hash salt length")

    @property
    def salt(self) -> bytes:
        return base64.b64decode(self._data["salt"])

    def device_id(self, serial: str) -> str:
        return hmac.new(self.salt, serial.encode("utf-8"), hashlib.sha256).hexdigest()

    def devices(self) -> dict[str, RememberedDevice]:
        result: dict[str, RememberedDevice] = {}
        for device_id, value in self._data["devices"].items():
            if not isinstance(value, dict):
                continue
            result[device_id] = RememberedDevice(
                device_id=device_id,
                name=str(value.get("name") or "Android phone")[:80],
                approved=bool(value.get("approved", True)),
                auto_connect=bool(value.get("auto_connect", False)),
            )
        return result

    def approve(self, device_id: str, name: str) -> RememberedDevice:
        clean_name = " ".join(name.split())[:80] or "Android phone"
        self._data["devices"][device_id] = {
            "name": clean_name,
            "approved": True,
            "auto_connect": False,
        }
        self.save()
        return self.devices()[device_id]

    def rename(self, device_id: str, name: str) -> RememberedDevice:
        if device_id not in self._data["devices"]:
            raise TeatherError("unknown-device", "The device is not remembered")
        clean_name = " ".join(name.split())[:80]
        if not clean_name:
            raise TeatherError("invalid-name", "Device name cannot be empty")
        self._data["devices"][device_id]["name"] = clean_name
        self.save()
        return self.devices()[device_id]

    def forget(self, device_id: str) -> None:
        if device_id not in self._data["devices"]:
            raise TeatherError("unknown-device", "The device is not remembered")
        del self._data["devices"][device_id]
        self.save()

    def set_auto_connect(self, device_id: str, enabled: bool) -> RememberedDevice:
        if device_id not in self._data["devices"]:
            raise TeatherError("unknown-device", "The device is not remembered")
        self._data["devices"][device_id]["auto_connect"] = enabled
        self.save()
        return self.devices()[device_id]

    def auto_failover(self) -> bool:
        """Whether Teather arms itself as an automatic backup path (D-022).

        Default on: once connected, Teather installs its worse-metric default
        route and additive DNS so traffic fails over automatically the moment
        the physical link's route and resolver disappear, mirroring
        Ethernet/Wi-Fi failover. The physical link itself is never touched.

        Off: Teather still connects (interface and tunnel up) but stays dormant
        with no default route and no DNS entry until the owner explicitly arms
        it, because the phone's upstream may be metered cellular data.
        """

        return bool(self._data.get("auto_failover", True))

    def set_auto_failover(self, enabled: bool) -> bool:
        self._data["auto_failover"] = bool(enabled)
        self.save()
        return self.auto_failover()

    def save(self) -> None:
        self.file.write(self._data)
