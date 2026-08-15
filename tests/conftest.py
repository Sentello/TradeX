"""Test fixtures.

Every test runs against an environment built here, never against the real
.env, and never touches a live exchange.
"""

import importlib
import os
import sys

import bcrypt
import dotenv
import pytest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

TEST_PASSWORD = "correct-horse-battery-staple"
TEST_PIN = "test-pin-abcdef123456"

# rounds=4 keeps the suite fast; production hashes use the bcrypt default.
TEST_PASSWORD_HASH = bcrypt.hashpw(
    TEST_PASSWORD.encode(), bcrypt.gensalt(rounds=4)
).decode()

BASE_ENV = {
    "FLASK_SECRET_KEY": "test-secret-key",
    "DASHBOARD_PASSWORD": TEST_PASSWORD_HASH,
    "WEBHOOK_PIN": TEST_PIN,
    "MODE": "webhook",
    "EXCHANGES": "bybit,binance",
    "BYBIT_API_KEY": "bybit-key",
    "BYBIT_API_SECRET": "bybit-secret",
    "BINANCE_API_KEY": "binance-key",
    "BINANCE_API_SECRET": "binance-secret",
    "LOGIN_MAX_ATTEMPTS": "3",
    "LOGIN_LOCKOUT_SECONDS": "300",
}

# Modules that hold module-level state derived from config, in import order.
RELOAD_ORDER = [
    "config",
    "serve",
    "exchanges",
    "signal_handler",
    "bot_logic",
    "email_reader",
    "webhook_receiver",
    "dashboard_app",
]

# Reloaded for every test regardless of what the test asked for: it caches
# whether logging was configured, and that must not leak between tests.
ALWAYS_RELOAD = ["log_setup"]


def reload_app(env, monkeypatch, tmp_path, modules=RELOAD_ORDER):
    """Rebuild the app's modules against a specific environment."""
    # The real .env must never leak into a test.
    monkeypatch.setattr(dotenv, "load_dotenv", lambda *a, **k: False)
    monkeypatch.setattr("dotenv.main.load_dotenv", lambda *a, **k: False, raising=False)

    for key in list(os.environ):
        if key.startswith(("FLASK_", "DASHBOARD_", "WEBHOOK_", "BYBIT_", "BINANCE_",
                           "IMAP_", "SESSION_", "LOGIN_", "MODE", "EXCHANGES")):
            monkeypatch.delenv(key, raising=False)

    for key, value in env.items():
        monkeypatch.setenv(key, value)
    monkeypatch.setenv("TRADEX_LOG_DIR", str(tmp_path / "logs"))

    for name in ALWAYS_RELOAD + RELOAD_ORDER:
        sys.modules.pop(name, None)

    loaded = {}
    for name in ALWAYS_RELOAD:
        importlib.import_module(name)
    for name in modules:
        loaded[name] = importlib.import_module(name)
    return loaded


@pytest.fixture
def app_env(monkeypatch, tmp_path):
    """Callable that boots the app with BASE_ENV plus any overrides."""
    def _boot(modules=RELOAD_ORDER, **overrides):
        env = dict(BASE_ENV)
        env.update({k: v for k, v in overrides.items() if v is not None})
        for k, v in overrides.items():
            if v is None:
                env.pop(k, None)
        return reload_app(env, monkeypatch, tmp_path, modules)
    return _boot


class FakeExchange:
    """Records ccxt calls instead of reaching an exchange."""

    def __init__(self, positions=None, raises=None):
        self.calls = []
        self._positions = positions or []
        self._raises = raises
        self.fetch_positions_count = 0

    def create_order(self, symbol, order_type, side, amount, price=None, params=None):
        self.calls.append(
            {
                "method": "create_order",
                "symbol": symbol,
                "type": order_type,
                "side": side,
                "amount": amount,
                "price": price,
                "params": params or {},
            }
        )
        if self._raises:
            raise self._raises
        return {"id": "order-1", "symbol": symbol, "status": "closed"}

    def fetch_positions(self):
        self.fetch_positions_count += 1
        return self._positions

    def fetch_open_orders(self):
        return []

    def fetch_balance(self):
        return {"total": {"USDT": 1000.0}}

    def cancel_order(self, order_id, symbol):
        self.calls.append({"method": "cancel_order", "id": order_id, "symbol": symbol})
        return {"id": order_id, "status": "canceled"}


@pytest.fixture
def fake_exchange():
    return FakeExchange
