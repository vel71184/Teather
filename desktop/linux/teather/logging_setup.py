"""Persistent daemon logging.

`teatherd` had no logging at all before this: `daemon.py` swallowed every
poll-loop exception and `Manager` narrated nothing, so a failure that happened
while nobody was watching left no record to look back at. This module gives the
daemon a rotating on-disk log plus stderr (which systemd captures into the
journal).

What is logged: the failing *layer* and the control-plane actions Teather takes
— D-Bus calls, `adb` control commands, NetworkManager activation, connect /
disconnect / reconcile / health-check steps and their outcomes. What is not
logged: resolver contents, DNS probe names, and per-flow destinations
(`AGENTS.md`: "Logs identify the failing layer without recording browsing
destinations by default"). `adb` serials are redacted to ``<device>`` by the
ADB layer before they reach a log record.

Set ``TEATHER_DEBUG=1`` for DEBUG-level detail (every `adb` argv, every poll
tick); the default level is INFO.
"""

from __future__ import annotations

import logging
import logging.handlers
import os
from pathlib import Path

LOGGER_NAME = "teather"
_MAX_BYTES = 2_000_000
_BACKUP_COUNT = 5
_FORMAT = "%(asctime)s %(levelname)-7s %(name)s: %(message)s"

_configured = False


def _state_dir() -> Path:
    """Where to keep the log. systemd's ``StateDirectory=teather`` wins; the
    XDG state dir is the fallback for a daemon started outside the unit."""

    from_systemd = os.environ.get("STATE_DIRECTORY", "").split(":")[0].strip()
    if from_systemd:
        return Path(from_systemd)
    base = os.environ.get("XDG_STATE_HOME", "").strip() or str(Path.home() / ".local" / "state")
    return Path(base) / "teather"


def log_path() -> Path:
    return _state_dir() / "teatherd.log"


def configure_logging() -> Path | None:
    """Attach the rotating-file and stderr handlers to the ``teather`` logger.

    Idempotent. Never raises: if the state directory cannot be created the
    daemon still runs and still logs to stderr/journal, just without the
    look-back file. Returns the log path when the file handler was attached.
    """

    global _configured
    if _configured:
        return None
    _configured = True

    level = logging.DEBUG if os.environ.get("TEATHER_DEBUG", "").strip() not in ("", "0", "false", "no") else logging.INFO
    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(level)
    logger.propagate = False
    formatter = logging.Formatter(_FORMAT)

    stderr_handler = logging.StreamHandler()
    stderr_handler.setFormatter(formatter)
    logger.addHandler(stderr_handler)

    path = log_path()
    try:
        path.parent.mkdir(mode=0o700, parents=True, exist_ok=True)
        os.chmod(path.parent, 0o700)
        file_handler = logging.handlers.RotatingFileHandler(
            path, maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8", delay=True,
        )
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
        # The handler opens the file lazily (delay=True); pre-create it with a
        # private mode so the first record does not land in a 0644 file.
        if not path.exists():
            path.touch(mode=0o600)
        else:
            os.chmod(path, 0o600)
    except OSError as error:
        logger.warning("on-disk logging unavailable (%s: %s); logging to stderr only", type(error).__name__, error)
        return None

    logger.info("logging to %s (level %s)", path, logging.getLevelName(level))
    return path
