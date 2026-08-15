import logging
import os
from datetime import timedelta

from dotenv import load_dotenv

load_dotenv()

# Handlers may not be attached yet; warnings still reach stderr.
_startup_log = logging.getLogger("tradex.config")

MIN_PIN_LENGTH = 16


class ConfigError(RuntimeError):
    """Raised at import time when the app is not safe to start."""


def _unescape(value):
    """Turn Compose's `$$` escape into a literal `$`.

    Docker Compose interpolates `.env` and treats `$NAME` as a variable.
    A bcrypt hash is `$2b$12$...`, so the third `$` plus the next
    characters get eaten unless every `$` is written as `$$`. python-dotenv
    does not do that rewrite, so the same file would otherwise disagree
    locally vs in Docker.
    """
    return value.replace("$$", "$")


def _required(name, hint):
    """Secrets have no safe default: refuse to start rather than guess one."""
    value = _unescape(os.getenv(name, "").strip())
    if not value:
        raise ConfigError(f"{name} is not set in .env. {hint}")
    return value


def _optional(name, default):
    value = _unescape(os.getenv(name, "").strip())
    return value or default


def _int(name, default):
    value = _unescape(os.getenv(name, "").strip())
    if not value:
        return default
    try:
        return int(value)
    except ValueError:
        raise ConfigError(f"{name} must be a whole number, got {value!r}.")


def _bool(name, default):
    value = _unescape(os.getenv(name, "").strip()).lower()
    if not value:
        return default
    return value in ("true", "1", "yes", "on")


# Dashboard
DASHBOARD_HOST = _optional("DASHBOARD_HOST", "0.0.0.0")
DASHBOARD_PORT = _int("DASHBOARD_PORT", 5000)
DASHBOARD_PASSWORD = _required(
    "DASHBOARD_PASSWORD", "Generate a bcrypt hash with: python generate_credentials.py"
)
if not DASHBOARD_PASSWORD.startswith(("$2a$", "$2b$", "$2y$")):
    raise ConfigError(
        "DASHBOARD_PASSWORD must be a bcrypt hash, not a plaintext password. "
        "Generate one with: python generate_credentials.py"
    )

# Flask session
FLASK_SECRET_KEY = _required(
    "FLASK_SECRET_KEY", "Generate one with: python generate_credentials.py"
)
SESSION_LIFETIME_HOURS = float(_optional("SESSION_LIFETIME_HOURS", "12"))
SESSION_PERMANENT_LIFETIME = timedelta(hours=SESSION_LIFETIME_HOURS)
# Leave false only when the dashboard is reached over plain HTTP on localhost.
SESSION_COOKIE_SECURE = _bool("SESSION_COOKIE_SECURE", False)

# Failed dashboard logins before that client is locked out.
LOGIN_MAX_ATTEMPTS = _int("LOGIN_MAX_ATTEMPTS", 5)
LOGIN_LOCKOUT_SECONDS = _int("LOGIN_LOCKOUT_SECONDS", 300)

# Webhook
WEBHOOK_HOST = _optional("WEBHOOK_HOST", "0.0.0.0")
WEBHOOK_PORT = _int("WEBHOOK_PORT", 5005)
# Without this the webhook is an open trading endpoint for anyone who finds it.
WEBHOOK_PIN = _required(
    "WEBHOOK_PIN", "Generate one with: python generate_credentials.py"
)
if len(WEBHOOK_PIN) < MIN_PIN_LENGTH:
    _startup_log.warning(
        f"⚠ WEBHOOK_PIN is only {len(WEBHOOK_PIN)} characters. It is the sole "
        f"credential on the trading endpoint; use at least {MIN_PIN_LENGTH} "
        f"random characters."
    )
if WEBHOOK_PIN.isdigit():
    _startup_log.warning(
        f"⚠ WEBHOOK_PIN is digits only, a keyspace of just 10^{len(WEBHOOK_PIN)}. "
        f"Regenerate it with: python generate_credentials.py"
    )

# Source addresses permitted to reach /webhook. Empty means "any address".
# TradingView publishes a small set of webhook source IPs; restricting to
# them removes brute force as a concern entirely.
WEBHOOK_ALLOWED_IPS = _optional("WEBHOOK_ALLOWED_IPS", "")

# Per-IP lockout after repeated bad PINs. Not endpoint-wide: a global lock
# would let anyone disable trading by sending a handful of bad requests.
WEBHOOK_MAX_FAILURES = _int("WEBHOOK_MAX_FAILURES", 5)
WEBHOOK_LOCKOUT_SECONDS = _int("WEBHOOK_LOCKOUT_SECONDS", 300)

# Window in which an identical signal is treated as a retry and ignored,
# so a lost response cannot turn into a doubled position. Set to 0 to
# disable. Send a unique ID field in the alert to make this exact.
WEBHOOK_DEDUP_SECONDS = _int("WEBHOOK_DEDUP_SECONDS", 60)

# Only enable behind a reverse proxy that overwrites X-Forwarded-For.
# Trusting it when directly exposed lets a client forge its own address and
# walk straight past the allowlist and the lockout.
TRUST_PROXY_HEADERS = _bool("TRUST_PROXY_HEADERS", False)

# Bybit / Binance credentials
BYBIT_API_KEY = _optional("BYBIT_API_KEY", "")
BYBIT_API_SECRET = _optional("BYBIT_API_SECRET", "")
BINANCE_API_KEY = _optional("BINANCE_API_KEY", "")
BINANCE_API_SECRET = _optional("BINANCE_API_SECRET", "")

# Which exchanges to enable (comma-separated list, e.g. "bybit,binance")
EXCHANGES = _optional("EXCHANGES", "bybit,binance").lower()
ENABLED_EXCHANGES = frozenset(part.strip() for part in EXCHANGES.split(",") if part.strip())

# Signal ingestion: "webhook", "email", or "both"
MODE = _optional("MODE", "webhook").lower()
if MODE not in ("webhook", "email", "both"):
    raise ConfigError(f"MODE must be 'webhook', 'email' or 'both', got {MODE!r}.")
WEBHOOK_ENABLED = MODE in ("webhook", "both")
EMAIL_ENABLED = MODE in ("email", "both")

# Email (IMAP)
IMAP_SERVER = _optional("IMAP_SERVER", "")
IMAP_PORT = _int("IMAP_PORT", 993)
IMAP_EMAIL = _optional("IMAP_EMAIL", "")
IMAP_PASSWORD = _optional("IMAP_PASSWORD", "")
IMAP_USE_SSL = _bool("IMAP_USE_SSL", True)
IMAP_CHECK_INTERVAL = _int("IMAP_CHECK_INTERVAL", 15)  # seconds

if EMAIL_ENABLED and not (IMAP_SERVER and IMAP_EMAIL and IMAP_PASSWORD):
    raise ConfigError(
        f"MODE={MODE} requires IMAP_SERVER, IMAP_EMAIL and IMAP_PASSWORD to be set."
    )
