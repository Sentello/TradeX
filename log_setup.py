"""Centralized logging setup.

Every process gets exactly one log file, named after the service it runs.
Previously each module attached its own RotatingFileHandler, which meant
several processes rotated the same file independently and lost lines on
rollover (bot_logic and signal_handler both wrote to trading.log).

Entry points call configure("<service>") before importing anything that
logs; library modules just call get_logger(__name__).
"""

import logging
import os
from logging.handlers import RotatingFileHandler

ROOT_LOGGER_NAME = "tradex"

_FORMAT = "%(asctime)s - %(levelname)s - %(filename)s:%(lineno)d - %(message)s"

# Payload keys whose values must never reach a log file.
_SECRET_KEYS = {"pin", "password", "passwd", "secret", "apikey", "api_key", "token"}

_configured = False


def log_directory():
    """Log destination, which differs inside the container."""
    override = os.getenv("TRADEX_LOG_DIR", "").strip()
    if override:
        return override
    return "/app/logs" if os.getenv("DOCKER_ENV") else "logs"


def configure(service):
    """Attach handlers to the shared parent logger. Idempotent."""
    global _configured

    logger = logging.getLogger(ROOT_LOGGER_NAME)
    if _configured:
        return logger

    directory = log_directory()
    os.makedirs(directory, exist_ok=True)

    formatter = logging.Formatter(_FORMAT)
    file_handler = RotatingFileHandler(
        os.path.join(directory, f"{service}.log"), maxBytes=2_000_000, backupCount=5
    )
    file_handler.setFormatter(formatter)
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(formatter)

    logger.setLevel(logging.INFO)
    # The logger object outlives a module reload, so drop anything stale
    # rather than accumulating duplicate handlers.
    for stale in list(logger.handlers):
        logger.removeHandler(stale)
        stale.close()
    logger.addHandler(file_handler)
    logger.addHandler(console_handler)
    # Handlers live here, not on the root logger, so nothing is emitted twice.
    logger.propagate = False

    _configured = True
    return logger


def get_logger(name):
    """Return a child logger. Falls back to a generic file if no entry point ran."""
    if not _configured:
        configure(os.getenv("TRADEX_SERVICE", ROOT_LOGGER_NAME))
    return logging.getLogger(f"{ROOT_LOGGER_NAME}.{name}")


def redact(payload):
    """Copy of a signal payload with secrets masked, safe to log."""
    if not isinstance(payload, dict):
        return payload
    return {
        key: ("***" if str(key).lower().replace("-", "_") in _SECRET_KEYS else value)
        for key, value in payload.items()
    }
