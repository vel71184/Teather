from __future__ import annotations

import os
from dataclasses import asdict, dataclass
from pathlib import Path

from .config import SecureJsonFile
from .errors import TeatherError


@dataclass(frozen=True)
class Ownership:
    device_id: str
    local_port: int | None
    android_started: bool


class OwnershipJournal:
    SCHEMA = 1

    def __init__(self, path: Path | None = None):
        root = Path(os.environ.get("XDG_RUNTIME_DIR", f"/run/user/{os.getuid()}"))
        self.file = SecureJsonFile(path or root / "teather" / "ownership.json")

    def load(self) -> Ownership | None:
        value = self.file.read()
        if value is None:
            return None
        if value.get("schema") != self.SCHEMA:
            raise TeatherError("invalid-journal", "Unsupported ownership journal schema")
        try:
            if type(value["android_started"]) is not bool:
                raise TypeError("android_started must be boolean")
            ownership = Ownership(
                device_id=str(value["device_id"]),
                local_port=None if value["local_port"] is None else int(value["local_port"]),
                android_started=bool(value["android_started"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise TeatherError("invalid-journal", "Malformed ownership journal") from error
        if (
            len(ownership.device_id) != 64
            or any(character not in "0123456789abcdef" for character in ownership.device_id)
            or (
                ownership.local_port is not None
                and ownership.local_port not in range(1024, 65536)
            )
            or (ownership.local_port is None and not ownership.android_started)
        ):
            raise TeatherError("invalid-journal", "Unsafe ownership journal values")
        return ownership

    def save(self, ownership: Ownership) -> None:
        self.file.write({"schema": self.SCHEMA, **asdict(ownership)})

    def clear(self) -> None:
        self.file.remove()
