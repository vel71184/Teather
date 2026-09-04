"""A tiny append-only history of finished Teather connection sessions.

One JSON object per line in ``<state dir>/sessions.jsonl`` (mode 0600, next to
``teatherd.log``), capped at the most recent :data:`MAX_ENTRIES`. It exists so a
long soak can be shown after the fact — how long each session lasted and how
much it moved — without reading raw byte counters off a live status.

Every function here is best-effort: a session record must never be able to break
a teardown, so all filesystem errors are swallowed.
"""

from __future__ import annotations

import json
from pathlib import Path

from .logging_setup import state_dir

MAX_ENTRIES = 100


def sessions_path() -> Path:
    return state_dir() / "sessions.jsonl"


def _read_lines(path: Path) -> list[str]:
    try:
        return [line for line in path.read_text(encoding="utf-8").splitlines() if line.strip()]
    except OSError:
        return []


def append(entry: dict) -> None:
    path = sessions_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        lines = _read_lines(path)
        lines.append(json.dumps(entry, sort_keys=True))
        lines = lines[-MAX_ENTRIES:]
        path.write_text("\n".join(lines) + "\n", encoding="utf-8")
        try:
            path.chmod(0o600)
        except OSError:
            pass
    except OSError:
        pass


def read(limit: int = MAX_ENTRIES) -> list[dict]:
    lines = _read_lines(sessions_path())
    out: list[dict] = []
    for line in lines[-limit:]:
        try:
            parsed = json.loads(line)
        except ValueError:
            continue
        if isinstance(parsed, dict):
            out.append(parsed)
    return out
