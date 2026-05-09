from __future__ import annotations
import logging
import os
from typing import Optional


_configured = False


def configure_logging(level: Optional[str] = None) -> None:
    global _configured
    if _configured:
        return
    lvl_str = level or os.getenv("LOG_LEVEL", "INFO")
    lvl = getattr(logging, lvl_str.upper(), logging.INFO)
    handler = logging.StreamHandler()
    fmt = logging.Formatter("%(asctime)s %(levelname)s: %(message)s")
    handler.setFormatter(fmt)
    root = logging.getLogger()
    # If another test harness or the environment already configured
    # handlers on the root logger, avoid adding a second handler to
    # prevent duplicate messages. Just set the level and mark configured.
    root.setLevel(lvl)
    if not root.handlers:
        root.addHandler(handler)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    configure_logging()
    return logging.getLogger(name)


__all__ = ["get_logger", "configure_logging"]
