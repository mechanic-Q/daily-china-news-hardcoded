# ---
# author: lmr
# created_at: 2026-07-03 20:11:30
# ---
#!/usr/bin/env python3
"""
daily_logging.py — centralized logging entry point for Daily project.
"""

from __future__ import annotations

import logging
import os
import sys
from pathlib import Path

__all__ = ["setup_logging"]

_log = logging.getLogger("daily")
_setup_done = False


def setup_logging(
    log_file: str | None = None,
    level: int | str | None = None,
) -> logging.Logger:
    global _setup_done

    if _setup_done:
        return _log

    _setup_done = True

    log_level: int
    if level is not None:
        if isinstance(level, str):
            log_level = getattr(logging, level.upper(), logging.INFO)
        else:
            log_level = level
    else:
        from_env = os.environ.get("DAILY_LOG_LEVEL", "INFO")
        log_level = getattr(logging, from_env.upper(), logging.INFO)

    _log.setLevel(log_level)

    fmt = logging.Formatter(
        "%(asctime)s [%(levelname)-5s] %(name)s: %(message)s",
        datefmt="%Y-%m-%d %H:%M:%S",
    )

    h = logging.StreamHandler(sys.stdout)
    h.setLevel(log_level)
    h.setFormatter(fmt)
    _log.addHandler(h)

    if log_file is None:
        log_file = str(
            Path(os.environ.get("DAILY_OUTPUT_DIR", "/mnt/e/每日新中国"))
            / "logs"
            / "daily.log"
        )

    try:
        path = Path(log_file)
        path.parent.mkdir(parents=True, exist_ok=True)
        fh = logging.FileHandler(log_file, encoding="utf-8")
        fh.setLevel(log_level)
        fh.setFormatter(fmt)
        _log.addHandler(fh)
    except OSError:
        pass

    return _log
