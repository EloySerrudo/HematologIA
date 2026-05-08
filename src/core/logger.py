"""Centralized logger configuration with rotating file handler.

Usage:
    from src.core.logger import get_logger
    logger = get_logger(__name__)
    logger.info("Message")

The first call to ``setup_logger`` configures the app-wide logger. Subsequent
calls are no-ops (idempotent).
"""
from __future__ import annotations

import logging
from logging.handlers import RotatingFileHandler

from src.config import (
    APP_NAME,
    LOG_BACKUP_COUNT,
    LOG_DATE_FORMAT,
    LOG_FORMAT,
    LOG_MAX_BYTES,
    LOG_PATH,
    LOGS_DIR,
)

_initialized: bool = False


def setup_logger() -> logging.Logger:
    """Configure the root app logger. Safe to call multiple times."""
    global _initialized
    logger = logging.getLogger(APP_NAME)

    if _initialized:
        return logger

    LOGS_DIR.mkdir(parents=True, exist_ok=True)

    logger.setLevel(logging.INFO)
    formatter = logging.Formatter(LOG_FORMAT, datefmt=LOG_DATE_FORMAT)

    file_handler = RotatingFileHandler(
        LOG_PATH,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setFormatter(formatter)
    logger.addHandler(file_handler)

    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)

    # Avoid double-emitting via the root logger.
    logger.propagate = False
    _initialized = True

    logger.info("Logger initialized — log file: %s", LOG_PATH)
    return logger


def get_logger(name: str | None = None) -> logging.Logger:
    """Return a child logger of the app logger.

    Args:
        name: Logger name (typically ``__name__``). If None, returns the root
            app logger.
    """
    if not _initialized:
        setup_logger()

    if name is None or name == APP_NAME:
        return logging.getLogger(APP_NAME)

    # Strip the package prefix so log lines say e.g. "core.auth" instead of
    # "src.core.auth.HematologIA" once the parent prefix is added.
    short = name.removeprefix("src.")
    return logging.getLogger(f"{APP_NAME}.{short}")
